import imp
import re
from inspect import getargspec

from django.conf import settings
from django.template.context import Context, RequestContext, ContextPopException
from django.utils.importlib import import_module
from django.utils.itercompat import is_iterable
from django.utils.functional import curry, Promise
from django.utils.text import smart_split, unescape_string_literal, get_text_list
from django.utils.encoding import smart_unicode, force_unicode, smart_str
from django.utils.translation import ugettext as _
from django.utils.safestring import SafeData, EscapeData, mark_safe, mark_for_escaping
from django.utils.formats import localize
from django.utils.html import escape
from django.utils.module_loading import module_has_submodule


TOKEN_TEXT = 0
TOKEN_VAR = 1
TOKEN_BLOCK = 2
TOKEN_COMMENT = 3

# template syntax constants
FILTER_SEPARATOR = '|'
FILTER_ARGUMENT_SEPARATOR = ':'
VARIABLE_ATTRIBUTE_SEPARATOR = '.'
BLOCK_TAG_START = '{%'
BLOCK_TAG_END = '%}'
VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'
COMMENT_TAG_START = '{#'
COMMENT_TAG_END = '#}'
TRANSLATOR_COMMENT_MARK = 'Translators'
SINGLE_BRACE_START = '{'
SINGLE_BRACE_END = '}'

ALLOWED_VARIABLE_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'

# what to report as the origin for templates that come from non-loader sources
# (e.g. strings)
UNKNOWN_SOURCE = '<unknown source>'

# match a variable or block tag and capture the entire tag, including start/end delimiters
tag_re = re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' % (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
                                          re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END),
                                          re.escape(COMMENT_TAG_START), re.escape(COMMENT_TAG_END)))

# global dictionary of libraries that have been loaded using get_library
libraries = {}
# global list of libraries to load by default for a new parser
builtins = []

# True if TEMPLATE_STRING_IF_INVALID contains a format string (%s). None means
# uninitialised.
invalid_var_format_string = None

class TemplateSyntaxError(Exception):
    pass

class TemplateDoesNotExist(Exception):
    pass

class TemplateEncodingError(Exception):
    pass

class VariableDoesNotExist(Exception):

    def __init__(self, msg, params=()):
        self.msg = msg
        self.params = params

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.msg % tuple([force_unicode(p, errors='replace') for p in self.params])

class InvalidTemplateLibrary(Exception):
    pass

class Origin(object):
    def __init__(self, name):
        self.name = name

    def reload(self):
        raise NotImplementedError

    def __str__(self):
        return self.name

class StringOrigin(Origin):
    def __init__(self, source):
        super(StringOrigin, self).__init__(UNKNOWN_SOURCE)
        self.source = source

    def reload(self):
        return self.source

class Template(object):
    def __init__(self, template_string, origin=None, name='<Unknown Template>'):
        try:
            template_string = smart_unicode(template_string)
        except UnicodeDecodeError:
            raise TemplateEncodingError("Templates can only be constructed from unicode or UTF-8 strings.")
        if settings.TEMPLATE_DEBUG and origin is None:
            origin = StringOrigin(template_string)
        self.nodelist = compile_string(template_string, origin)
        self.name = name

    def __iter__(self):
        for node in self.nodelist:
            for subnode in node:
                yield subnode

    def _render(self, context):
        return self.nodelist.render(context)

    def render(self, context):
        "Display stage -- can be called many times"
        context.render_context.push()
        try:
            return self._render(context)
        finally:
            context.render_context.pop()

def compile_string(template_string, origin):
    "Compiles template_string into NodeList ready for rendering"
    if settings.TEMPLATE_DEBUG:
        from debug import DebugLexer, DebugParser
        lexer_class, parser_class = DebugLexer, DebugParser
    else:
        lexer_class, parser_class = Lexer, Parser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    return parser.parse()

class Token(object):
    def __init__(self, token_type, contents):
        # token_type must be TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK or TOKEN_COMMENT.
        self.token_type, self.contents = token_type, contents
        self.lineno = None

    def __str__(self):
        return '<%s token: "%s...">' % \
            ({TOKEN_TEXT: 'Text', TOKEN_VAR: 'Var', TOKEN_BLOCK: 'Block', TOKEN_COMMENT: 'Comment'}[self.token_type],
            self.contents[:20].replace('\n', ''))

    def split_contents(self):
        split = []
        bits = iter(smart_split(self.contents))
        for bit in bits:
            # Handle translation-marked template pieces
            if bit.startswith('_("') or bit.startswith("_('"):
                sentinal = bit[2] + ')'
                trans_bit = [bit]
                while not bit.endswith(sentinal):
                    bit = bits.next()
                    trans_bit.append(bit)
                bit = ' '.join(trans_bit)
            split.append(bit)
        return split

class Lexer(object):
    def __init__(self, template_string, origin):
        self.template_string = template_string
        self.origin = origin
        self.lineno = 1

    def tokenize(self):
        "Return a list of tokens from a given template_string."
        in_tag = False
        result = []
        for bit in tag_re.split(self.template_string):
            if bit:
                result.append(self.create_token(bit, in_tag))
            in_tag = not in_tag
        return result

    def create_token(self, token_string, in_tag):
        """
        Convert the given token string into a new Token object and return it.
        If in_tag is True, we are processing something that matched a tag,
        otherwise it should be treated as a literal string.
        """
        if in_tag:
            if token_string.startswith(VARIABLE_TAG_START):
                token = Token(TOKEN_VAR, token_string[len(VARIABLE_TAG_START):-len(VARIABLE_TAG_END)].strip())
            elif token_string.startswith(BLOCK_TAG_START):
                token = Token(TOKEN_BLOCK, token_string[len(BLOCK_TAG_START):-len(BLOCK_TAG_END)].strip())
            elif token_string.startswith(COMMENT_TAG_START):
                content = ''
                if token_string.find(TRANSLATOR_COMMENT_MARK):
                    content = token_string[len(COMMENT_TAG_START):-len(COMMENT_TAG_END)].strip()
                token = Token(TOKEN_COMMENT, content)
        else:
            token = Token(TOKEN_TEXT, token_string)
        token.lineno = self.lineno
        self.lineno += token_string.count('\n')
        return token

class Parser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.tags = {}
        self.filters = {}
        for lib in builtins:
            self.add_library(lib)

    def parse(self, parse_until=None):
        if parse_until is None: parse_until = []
        nodelist = self.create_nodelist()
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_TEXT:
                self.extend_nodelist(nodelist, TextNode(token.contents), token)
            elif token.token_type == TOKEN_VAR:
                if not token.contents:
                    self.empty_variable(token)
                filter_expression = self.compile_filter(token.contents)
                var_node = self.create_variable_node(filter_expression)
                self.extend_nodelist(nodelist, var_node,token)
            elif token.token_type == TOKEN_BLOCK:
                if token.contents in parse_until:
                    # put token back on token list so calling code knows why it terminated
                    self.prepend_token(token)
                    return nodelist
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    self.empty_block_tag(token)
                # execute callback function for this tag and append resulting node
                self.enter_command(command, token)
                try:
                    compile_func = self.tags[command]
                except KeyError:
                    self.invalid_block_tag(token, command, parse_until)
                try:
                    compiled_result = compile_func(self, token)
                except TemplateSyntaxError, e:
                    if not self.compile_function_error(token, e):
                        raise
                self.extend_nodelist(nodelist, compiled_result, token)
                self.exit_command()
        if parse_until:
            self.unclosed_block_tag(parse_until)
        return nodelist

    def skip_past(self, endtag):
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_BLOCK and token.contents == endtag:
                return
        self.unclosed_block_tag([endtag])

    def create_variable_node(self, filter_expression):
        return VariableNode(filter_expression)

    def create_nodelist(self):
        return NodeList()

    def extend_nodelist(self, nodelist, node, token):
        if node.must_be_first and nodelist:
            try:
                if nodelist.contains_nontext:
                    raise AttributeError
            except AttributeError:
                raise TemplateSyntaxError("%r must be the first tag in the template." % node)
        if isinstance(nodelist, NodeList) and not isinstance(node, TextNode):
            nodelist.contains_nontext = True
        nodelist.append(node)

    def enter_command(self, command, token):
        pass

    def exit_command(self):
        pass

    def error(self, token, msg):
        return TemplateSyntaxError(msg)

    def empty_variable(self, token):
        raise self.error(token, "Empty variable tag")

    def empty_block_tag(self, token):
        raise self.error(token, "Empty block tag")

    def invalid_block_tag(self, token, command, parse_until=None):
        if parse_until:
            raise self.error(token, "Invalid block tag: '%s', expected %s" % (command, get_text_list(["'%s'" % p for p in parse_until])))
        raise self.error(token, "Invalid block tag: '%s'" % command)

    def unclosed_block_tag(self, parse_until):
        raise self.error(None, "Unclosed tags: %s " %  ', '.join(parse_until))

    def compile_function_error(self, token, e):
        pass

    def next_token(self):
        return self.tokens.pop(0)

    def prepend_token(self, token):
        self.tokens.insert(0, token)

    def delete_first_token(self):
        del self.tokens[0]

    def add_library(self, lib):
        self.tags.update(lib.tags)
        self.filters.update(lib.filters)

    def compile_filter(self, token):
        "Convenient wrapper for FilterExpression"
        return FilterExpression(token, self)

    def find_filter(self, filter_name):
        if filter_name in self.filters:
            return self.filters[filter_name]
        else:
            raise TemplateSyntaxError("Invalid filter: '%s'" % filter_name)

class TokenParser(object):
    """
    Subclass this and implement the top() method to parse a template line. When
    instantiating the parser, pass in the line from the Django template parser.

    The parser's "tagname" instance-variable stores the name of the tag that
    the filter was called with.
    """
    def __init__(self, subject):
        self.subject = subject
        self.pointer = 0
        self.backout = []
        self.tagname = self.tag()

    def top(self):
        "Overload this method to do the actual parsing and return the result."
        raise NotImplementedError()

    def more(self):
        "Returns True if there is more stuff in the tag."
        return self.pointer < len(self.subject)

    def back(self):
        "Undoes the last microparser. Use this for lookahead and backtracking."
        if not len(self.backout):
            raise TemplateSyntaxError("back called without some previous parsing")
        self.pointer = self.backout.pop()

    def tag(self):
        "A microparser that just returns the next tag from the line."
        subject = self.subject
        i = self.pointer
        if i >= len(subject):
            raise TemplateSyntaxError("expected another tag, found end of string: %s" % subject)
        p = i
        while i < len(subject) and subject[i] not in (' ', '\t'):
            i += 1
        s = subject[p:i]
        while i < len(subject) and subject[i] in (' ', '\t'):
            i += 1
        self.backout.append(self.pointer)
        self.pointer = i
        return s

    def value(self):
        "A microparser that parses for a value: some string constant or variable name."
        subject = self.subject
        i = self.pointer

        def next_space_index(subject, i):
            "Increment pointer until a real space (i.e. a space not within quotes) is encountered"
            while i < len(subject) and subject[i] not in (' ', '\t'):
                if subject[i] in ('"', "'"):
                    c = subject[i]
                    i += 1
                    while i < len(subject) and subject[i] != c:
                        i += 1
                    if i >= len(subject):
                        raise TemplateSyntaxError("Searching for value. Unexpected end of string in column %d: %s" % (i, subject))
                i += 1
            return i

        if i >= len(subject):
            raise TemplateSyntaxError("Searching for value. Expected another value but found end of string: %s" % subject)
        if subject[i] in ('"', "'"):
            p = i
            i += 1
            while i < len(subject) and subject[i] != subject[p]:
                i += 1
            if i >= len(subject):
                raise TemplateSyntaxError("Searching for value. Unexpected end of string in column %d: %s" % (i, subject))
            i += 1

            # Continue parsing until next "real" space, so that filters are also included
            i = next_space_index(subject, i)

            res = subject[p:i]
            while i < len(subject) and subject[i] in (' ', '\t'):
                i += 1
            self.backout.append(self.pointer)
            self.pointer = i
            return res
        else:
            p = i
            i = next_space_index(subject, i)
            s = subject[p:i]
            while i < len(subject) and subject[i] in (' ', '\t'):
                i += 1
            self.backout.append(self.pointer)
            self.pointer = i
            return s

# This only matches constant *strings* (things in quotes or marked for
# translation). Numbers are treated as variables for implementation reasons
# (so that they retain their type when passed to filters).
constant_string = r"""
(?:%(i18n_open)s%(strdq)s%(i18n_close)s|
%(i18n_open)s%(strsq)s%(i18n_close)s|
%(strdq)s|
%(strsq)s)
""" % {
    'strdq': r'"[^"\\]*(?:\\.[^"\\]*)*"', # double-quoted string
    'strsq': r"'[^'\\]*(?:\\.[^'\\]*)*'", # single-quoted string
    'i18n_open' : re.escape("_("),
    'i18n_close' : re.escape(")"),
    }
constant_string = constant_string.replace("\n", "")

filter_raw_string = r"""
^(?P<constant>%(constant)s)|
^(?P<var>[%(var_chars)s]+|%(num)s)|
 (?:%(filter_sep)s
     (?P<filter_name>\w+)
         (?:%(arg_sep)s
             (?:
              (?P<constant_arg>%(constant)s)|
              (?P<var_arg>[%(var_chars)s]+|%(num)s)
             )
         )?
 )""" % {
    'constant': constant_string,
    'num': r'[-+\.]?\d[\d\.e]*',
    'var_chars': "\w\." ,
    'filter_sep': re.escape(FILTER_SEPARATOR),
    'arg_sep': re.escape(FILTER_ARGUMENT_SEPARATOR),
  }

filter_re = re.compile(filter_raw_string, re.UNICODE|re.VERBOSE)

class FilterExpression(object):
    r"""
    Parses a variable token and its optional filters (all as a single string),
    and return a list of tuples of the filter name and arguments.
    Sample:
        >>> token = 'variable|default:"Default value"|date:"Y-m-d"'
        >>> p = Parser('')
        >>> fe = FilterExpression(token, p)
        >>> len(fe.filters)
        2
        >>> fe.var
        <Variable: 'variable'>

    This class should never be instantiated outside of the
    get_filters_from_token helper function.
    """
    def __init__(self, token, parser):
        self.token = token
        matches = filter_re.finditer(token)
        var_obj = None
        filters = []
        upto = 0
        for match in matches:
            start = match.start()
            if upto != start:
                raise TemplateSyntaxError("Could not parse some characters: %s|%s|%s"  % \
                        (token[:upto], token[upto:start], token[start:]))
            if var_obj is None:
                var, constant = match.group("var", "constant")
                if constant:
                    try:
                        var_obj = Variable(constant).resolve({})
                    except VariableDoesNotExist:
                        var_obj = None
                elif var is None:
                    raise TemplateSyntaxError("Could not find variable at start of %s." % token)
                else:
                    var_obj = Variable(var)
            else:
                filter_name = match.group("filter_name")
                args = []
                constant_arg, var_arg = match.group("constant_arg", "var_arg")
                if constant_arg:
                    args.append((False, Variable(constant_arg).resolve({})))
                elif var_arg:
                    args.append((True, Variable(var_arg)))
                filter_func = parser.find_filter(filter_name)
                self.args_check(filter_name, filter_func, args)
                filters.append((filter_func, args))
            upto = match.end()
        if upto != len(token):
            raise TemplateSyntaxError("Could not parse the remainder: '%s' from '%s'" % (token[upto:], token))

        self.filters = filters
        self.var = var_obj

    def resolve(self, context, ignore_failures=False):
        if isinstance(self.var, Variable):
            try:
                obj = self.var.resolve(context)
            except VariableDoesNotExist:
                if ignore_failures:
                    obj = None
                else:
                    if settings.TEMPLATE_STRING_IF_INVALID:
                        global invalid_var_format_string
                        if invalid_var_format_string is None:
                            invalid_var_format_string = '%s' in settings.TEMPLATE_STRING_IF_INVALID
                        if invalid_var_format_string:
                            return settings.TEMPLATE_STRING_IF_INVALID % self.var
                        return settings.TEMPLATE_STRING_IF_INVALID
                    else:
                        obj = settings.TEMPLATE_STRING_IF_INVALID
        else:
            obj = self.var
        for func, args in self.filters:
            arg_vals = []
            for lookup, arg in args:
                if not lookup:
                    arg_vals.append(mark_safe(arg))
                else:
                    arg_vals.append(arg.resolve(context))
            if getattr(func, 'needs_autoescape', False):
                new_obj = func(obj, autoescape=context.autoescape, *arg_vals)
            else:
                new_obj = func(obj, *arg_vals)
            if getattr(func, 'is_safe', False) and isinstance(obj, SafeData):
                obj = mark_safe(new_obj)
            elif isinstance(obj, EscapeData):
                obj = mark_for_escaping(new_obj)
            else:
                obj = new_obj
        return obj

    def args_check(name, func, provided):
        provided = list(provided)
        plen = len(provided)
        # Check to see if a decorator is providing the real function.
        func = getattr(func, '_decorated_function', func)
        args, varargs, varkw, defaults = getargspec(func)
        # First argument is filter input.
        args.pop(0)
        if defaults:
            nondefs = args[:-len(defaults)]
        else:
            nondefs = args
        # Args without defaults must be provided.
        try:
            for arg in nondefs:
                provided.pop(0)
        except IndexError:
            # Not enough
            raise TemplateSyntaxError("%s requires %d arguments, %d provided" % (name, len(nondefs), plen))

        # Defaults can be overridden.
        defaults = defaults and list(defaults) or []
        try:
            for parg in provided:
                defaults.pop(0)
        except IndexError:
            # Too many.
            raise TemplateSyntaxError("%s requires %d arguments, %d provided" % (name, len(nondefs), plen))

        return True
    args_check = staticmethod(args_check)

    def __str__(self):
        return self.token

def resolve_variable(path, context):
    """
    Returns the resolved variable, which may contain attribute syntax, within
    the given context.

    Deprecated; use the Variable class instead.
    """
    return Variable(path).resolve(context)

class Variable(object):
    r"""
    A template variable, resolvable against a given context. The variable may be
    a hard-coded string (if it begins and ends with single or double quote
    marks)::

        >>> c = {'article': {'section':u'News'}}
        >>> Variable('article.section').resolve(c)
        u'News'
        >>> Variable('article').resolve(c)
        {'section': u'News'}
        >>> class AClass: pass
        >>> c = AClass()
        >>> c.article = AClass()
        >>> c.article.section = u'News'

    (The example assumes VARIABLE_ATTRIBUTE_SEPARATOR is '.')
    """

    def __init__(self, var):
        self.var = var
        self.literal = None
        self.lookups = None
        self.translate = False

        try:
            # First try to treat this variable as a number.
            #
            # Note that this could cause an OverflowError here that we're not
            # catching. Since this should only happen at compile time, that's
            # probably OK.
            self.literal = float(var)

            # So it's a float... is it an int? If the original value contained a
            # dot or an "e" then it was a float, not an int.
            if '.' not in var and 'e' not in var.lower():
                self.literal = int(self.literal)

            # "2." is invalid
            if var.endswith('.'):
                raise ValueError

        except ValueError:
            # A ValueError means that the variable isn't a number.
            if var.startswith('_(') and var.endswith(')'):
                # The result of the lookup should be translated at rendering
                # time.
                self.translate = True
                var = var[2:-1]
            # If it's wrapped with quotes (single or double), then
            # we're also dealing with a literal.
            try:
                self.literal = mark_safe(unescape_string_literal(var))
            except ValueError:
                # Otherwise we'll set self.lookups so that resolve() knows we're
                # dealing with a bonafide variable
                if var.find(VARIABLE_ATTRIBUTE_SEPARATOR + '_') > -1 or var[0] == '_':
                    raise TemplateSyntaxError("Variables and attributes may not begin with underscores: '%s'" % var)
                self.lookups = tuple(var.split(VARIABLE_ATTRIBUTE_SEPARATOR))

    def resolve(self, context):
        """Resolve this variable against a given context."""
        if self.lookups is not None:
            # We're dealing with a variable that needs to be resolved
            value = self._resolve_lookup(context)
        else:
            # We're dealing with a literal, so it's already been "resolved"
            value = self.literal
        if self.translate:
            return _(value)
        return value

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.var)

    def __str__(self):
        return self.var

    def _resolve_lookup(self, context):
        """
        Performs resolution of a real variable (i.e. not a literal) against the
        given context.

        As indicated by the method's name, this method is an implementation
        detail and shouldn't be called by external code. Use Variable.resolve()
        instead.
        """
        current = context
        try: # catch-all for silent variable failures
            for bit in self.lookups:
                try: # dictionary lookup
                    current = current[bit]
                except (TypeError, AttributeError, KeyError):
                    try: # attribute lookup
                        current = getattr(current, bit)
                    except (TypeError, AttributeError):
                        try: # list-index lookup
                            current = current[int(bit)]
                        except (IndexError, # list index out of range
                                ValueError, # invalid literal for int()
                                KeyError,   # current is a dict without `int(bit)` key
                                TypeError,  # unsubscriptable object
                                ):
                            raise VariableDoesNotExist("Failed lookup for key [%s] in %r", (bit, current)) # missing attribute
                if callable(current):
                    if getattr(current, 'alters_data', False):
                        current = settings.TEMPLATE_STRING_IF_INVALID
                    else:
                        try: # method call (assuming no args required)
                            current = current()
                        except TypeError: # arguments *were* required
                            # GOTCHA: This will also catch any TypeError
                            # raised in the function itself.
                            current = settings.TEMPLATE_STRING_IF_INVALID # invalid method call
        except Exception, e:
            if getattr(e, 'silent_variable_failure', False):
                current = settings.TEMPLATE_STRING_IF_INVALID
            else:
                raise

        return current

class Node(object):
    # Set this to True for nodes that must be first in the template (although
    # they can be preceded by text nodes.
    must_be_first = False
    child_nodelists = ('nodelist',)

    def render(self, context):
        "Return the node rendered as a string"
        pass

    def __iter__(self):
        yield self

    def get_nodes_by_type(self, nodetype):
        "Return a list of all nodes (within this node and its nodelist) of the given type"
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        for attr in self.child_nodelists:
            nodelist = getattr(self, attr, None)
            if nodelist:
                nodes.extend(nodelist.get_nodes_by_type(nodetype))
        return nodes

class NodeList(list):
    # Set to True the first time a non-TextNode is inserted by
    # extend_nodelist().
    contains_nontext = False

    def render(self, context):
        bits = []
        for node in self:
            if isinstance(node, Node):
                bits.append(self.render_node(node, context))
            else:
                bits.append(node)
        return mark_safe(''.join([force_unicode(b) for b in bits]))

    def get_nodes_by_type(self, nodetype):
        "Return a list of all nodes of the given type"
        nodes = []
        for node in self:
            nodes.extend(node.get_nodes_by_type(nodetype))
        return nodes

    def render_node(self, node, context):
        return node.render(context)

class TextNode(Node):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "<Text Node: '%s'>" % smart_str(self.s[:25], 'ascii',
                errors='replace')

    def render(self, context):
        return self.s

def _render_value_in_context(value, context):
    """
    Converts any value to a string to become part of a rendered template. This
    means escaping, if required, and conversion to a unicode object. If value
    is a string, it is expected to have already been translated.
    """
    value = localize(value, use_l10n=context.use_l10n)
    value = force_unicode(value)
    if (context.autoescape and not isinstance(value, SafeData)) or isinstance(value, EscapeData):
        return escape(value)
    else:
        return value

class VariableNode(Node):
    def __init__(self, filter_expression):
        self.filter_expression = filter_expression

    def __repr__(self):
        return "<Variable Node: %s>" % self.filter_expression

    def render(self, context):
        try:
            output = self.filter_expression.resolve(context)
        except UnicodeDecodeError:
            # Unicode conversion can fail sometimes for reasons out of our
            # control (e.g. exception rendering). In that case, we fail quietly.
            return ''
        return _render_value_in_context(output, context)

def generic_tag_compiler(params, defaults, name, node_class, parser, token):
    "Returns a template.Node subclass."
    bits = token.split_contents()[1:]
    bmax = len(params)
    def_len = defaults and len(defaults) or 0
    bmin = bmax - def_len
    if(len(bits) < bmin or len(bits) > bmax):
        if bmin == bmax:
            message = "%s takes %s arguments" % (name, bmin)
        else:
            message = "%s takes between %s and %s arguments" % (name, bmin, bmax)
        raise TemplateSyntaxError(message)
    return node_class(bits)

class Library(object):
    def __init__(self):
        self.filters = {}
        self.tags = {}

    def tag(self, name=None, compile_function=None):
        if name == None and compile_function == None:
            # @register.tag()
            return self.tag_function
        elif name != None and compile_function == None:
            if(callable(name)):
                # @register.tag
                return self.tag_function(name)
            else:
                # @register.tag('somename') or @register.tag(name='somename')
                def dec(func):
                    return self.tag(name, func)
                return dec
        elif name != None and compile_function != None:
            # register.tag('somename', somefunc)
            self.tags[name] = compile_function
            return compile_function
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to Library.tag: (%r, %r)", (name, compile_function))

    def tag_function(self,func):
        self.tags[getattr(func, "_decorated_function", func).__name__] = func
        return func

    def filter(self, name=None, filter_func=None):
        if name == None and filter_func == None:
            # @register.filter()
            return self.filter_function
        elif filter_func == None:
            if(callable(name)):
                # @register.filter
                return self.filter_function(name)
            else:
                # @register.filter('somename') or @register.filter(name='somename')
                def dec(func):
                    return self.filter(name, func)
                return dec
        elif name != None and filter_func != None:
            # register.filter('somename', somefunc)
            self.filters[name] = filter_func
            return filter_func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to Library.filter: (%r, %r)", (name, filter_func))

    def filter_function(self, func):
        self.filters[getattr(func, "_decorated_function", func).__name__] = func
        return func

    def simple_tag(self, func=None, takes_context=None):
        def dec(func):
            params, xx, xxx, defaults = getargspec(func)
            if takes_context:
                if params[0] == 'context':
                    params = params[1:]
                else:
                    raise TemplateSyntaxError("Any tag function decorated with takes_context=True must have a first argument of 'context'")

            class SimpleNode(Node):
                def __init__(self, vars_to_resolve):
                    self.vars_to_resolve = map(Variable, vars_to_resolve)

                def render(self, context):
                    resolved_vars = [var.resolve(context) for var in self.vars_to_resolve]
                    if takes_context:
                        func_args = [context] + resolved_vars
                    else:
                        func_args = resolved_vars
                    return func(*func_args)

            compile_func = curry(generic_tag_compiler, params, defaults, getattr(func, "_decorated_function", func).__name__, SimpleNode)
            compile_func.__doc__ = func.__doc__
            self.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
            return func

        if func is None:
            # @register.simple_tag(...)
            return dec
        elif callable(func):
            # @register.simple_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to simple_tag")

    def inclusion_tag(self, file_name, context_class=Context, takes_context=False):
        def dec(func):
            params, xx, xxx, defaults = getargspec(func)
            if takes_context:
                if params[0] == 'context':
                    params = params[1:]
                else:
                    raise TemplateSyntaxError("Any tag function decorated with takes_context=True must have a first argument of 'context'")

            class InclusionNode(Node):
                def __init__(self, vars_to_resolve):
                    self.vars_to_resolve = map(Variable, vars_to_resolve)

                def render(self, context):
                    resolved_vars = [var.resolve(context) for var in self.vars_to_resolve]
                    if takes_context:
                        args = [context] + resolved_vars
                    else:
                        args = resolved_vars

                    dict = func(*args)

                    if not getattr(self, 'nodelist', False):
                        from django.template.loader import get_template, select_template
                        if not isinstance(file_name, basestring) and is_iterable(file_name):
                            t = select_template(file_name)
                        else:
                            t = get_template(file_name)
                        self.nodelist = t.nodelist
                    new_context = context_class(dict, autoescape=context.autoescape)
                    # Copy across the CSRF token, if present, because inclusion
                    # tags are often used for forms, and we need instructions
                    # for using CSRF protection to be as simple as possible.
                    csrf_token = context.get('csrf_token', None)
                    if csrf_token is not None:
                        new_context['csrf_token'] = csrf_token
                    return self.nodelist.render(new_context)

            compile_func = curry(generic_tag_compiler, params, defaults, getattr(func, "_decorated_function", func).__name__, InclusionNode)
            compile_func.__doc__ = func.__doc__
            self.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
            return func
        return dec

def import_library(taglib_module):
    """Load a template tag library module.

    Verifies that the library contains a 'register' attribute, and
    returns that attribute as the representation of the library
    """
    app_path, taglib = taglib_module.rsplit('.',1)
    app_module = import_module(app_path)
    try:
        mod = import_module(taglib_module)
    except ImportError, e:
        # If the ImportError is because the taglib submodule does not exist, that's not
        # an error that should be raised. If the submodule exists and raised an ImportError
        # on the attempt to load it, that we want to raise.
        if not module_has_submodule(app_module, taglib):
            return None
        else:
            raise InvalidTemplateLibrary("ImportError raised loading %s: %s" % (taglib_module, e))
    try:
        return mod.register
    except AttributeError:
        raise InvalidTemplateLibrary("Template library %s does not have a variable named 'register'" % taglib_module)

templatetags_modules = []

def get_templatetags_modules():
    """Return the list of all available template tag modules.

    Caches the result for faster access.
    """
    global templatetags_modules
    if not templatetags_modules:
        _templatetags_modules = []
        # Populate list once per thread.
        for app_module in ['django'] + list(settings.INSTALLED_APPS):
            try:
                templatetag_module = '%s.templatetags' % app_module
                import_module(templatetag_module)
                _templatetags_modules.append(templatetag_module)
            except ImportError:
                continue
        templatetags_modules = _templatetags_modules
    return templatetags_modules

def get_library(library_name):
    """
    Load the template library module with the given name.

    If library is not already loaded loop over all templatetags modules to locate it.

    {% load somelib %} and {% load someotherlib %} loops twice.

    Subsequent loads eg. {% load somelib %} in the same process will grab the cached
    module from libraries.
    """
    lib = libraries.get(library_name, None)
    if not lib:
        templatetags_modules = get_templatetags_modules()
        tried_modules = []
        for module in templatetags_modules:
            taglib_module = '%s.%s' % (module, library_name)
            tried_modules.append(taglib_module)
            lib = import_library(taglib_module)
            if lib:
                libraries[library_name] = lib
                break
        if not lib:
            raise InvalidTemplateLibrary("Template library %s not found, tried %s" % (library_name, ','.join(tried_modules)))
    return lib

def add_to_builtins(module):
    builtins.append(import_library(module))

add_to_builtins('django.template.defaulttags')
add_to_builtins('django.template.defaultfilters')
