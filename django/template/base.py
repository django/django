from __future__ import unicode_literals

import re
from functools import partial
from importlib import import_module
from inspect import getargspec, getcallargs

from django.apps import apps
from django.conf import settings
from django.template.context import (BaseContext, Context, RequestContext,  # NOQA: imported for backwards compatibility
    ContextPopException)
from django.utils.itercompat import is_iterable
from django.utils.text import (smart_split, unescape_string_literal,
    get_text_list)
from django.utils.encoding import force_str, force_text
from django.utils.translation import ugettext_lazy, pgettext_lazy
from django.utils.safestring import (SafeData, EscapeData, mark_safe,
    mark_for_escaping)
from django.utils.formats import localize
from django.utils.html import conditional_escape
from django.utils.module_loading import module_has_submodule
from django.utils import six
from django.utils.timezone import template_localtime
from django.utils.encoding import python_2_unicode_compatible


TOKEN_TEXT = 0
TOKEN_VAR = 1
TOKEN_BLOCK = 2
TOKEN_COMMENT = 3
TOKEN_MAPPING = {
    TOKEN_TEXT: 'Text',
    TOKEN_VAR: 'Var',
    TOKEN_BLOCK: 'Block',
    TOKEN_COMMENT: 'Comment',
}

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

ALLOWED_VARIABLE_CHARS = ('abcdefghijklmnopqrstuvwxyz'
                         'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.')

# what to report as the origin for templates that come from non-loader sources
# (e.g. strings)
UNKNOWN_SOURCE = '<unknown source>'

# match a variable or block tag and capture the entire tag, including start/end
# delimiters
tag_re = (re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' %
          (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
           re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END),
           re.escape(COMMENT_TAG_START), re.escape(COMMENT_TAG_END))))

# global dictionary of libraries that have been loaded using get_library
libraries = {}
# global list of libraries to load by default for a new parser
builtins = []

# True if TEMPLATE_STRING_IF_INVALID contains a format string (%s). None means
# uninitialized.
invalid_var_format_string = None


class TemplateSyntaxError(Exception):
    pass


class TemplateDoesNotExist(Exception):
    pass


class TemplateEncodingError(Exception):
    pass


@python_2_unicode_compatible
class VariableDoesNotExist(Exception):

    def __init__(self, msg, params=()):
        self.msg = msg
        self.params = params

    def __str__(self):
        return self.msg % tuple(force_text(p, errors='replace') for p in self.params)


class InvalidTemplateLibrary(Exception):
    pass


class Origin(object):
    def __init__(self, name):
        self.name = name

    def reload(self):
        raise NotImplementedError('subclasses of Origin must provide a reload() method')

    def __str__(self):
        return self.name


class StringOrigin(Origin):
    def __init__(self, source):
        super(StringOrigin, self).__init__(UNKNOWN_SOURCE)
        self.source = source

    def reload(self):
        return self.source


class Template(object):
    def __init__(self, template_string, origin=None, name=None):
        try:
            template_string = force_text(template_string)
        except UnicodeDecodeError:
            raise TemplateEncodingError("Templates can only be constructed "
                                        "from unicode or UTF-8 strings.")
        if settings.TEMPLATE_DEBUG and origin is None:
            origin = StringOrigin(template_string)
        self.nodelist = compile_string(template_string, origin)
        self.name = name
        self.origin = origin

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
        from django.template.debug import DebugLexer, DebugParser
        lexer_class, parser_class = DebugLexer, DebugParser
    else:
        lexer_class, parser_class = Lexer, Parser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    return parser.parse()


class Token(object):
    def __init__(self, token_type, contents):
        # token_type must be TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK or
        # TOKEN_COMMENT.
        self.token_type, self.contents = token_type, contents
        self.lineno = None

    def __str__(self):
        token_name = TOKEN_MAPPING[self.token_type]
        return ('<%s token: "%s...">' %
                (token_name, self.contents[:20].replace('\n', '')))

    def split_contents(self):
        split = []
        bits = iter(smart_split(self.contents))
        for bit in bits:
            # Handle translation-marked template pieces
            if bit.startswith('_("') or bit.startswith("_('"):
                sentinal = bit[2] + ')'
                trans_bit = [bit]
                while not bit.endswith(sentinal):
                    bit = next(bits)
                    trans_bit.append(bit)
                bit = ' '.join(trans_bit)
            split.append(bit)
        return split


class Lexer(object):
    def __init__(self, template_string, origin):
        self.template_string = template_string
        self.origin = origin
        self.lineno = 1
        self.verbatim = False

    def tokenize(self):
        """
        Return a list of tokens from a given template_string.
        """
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
        if in_tag and token_string.startswith(BLOCK_TAG_START):
            # The [2:-2] ranges below strip off *_TAG_START and *_TAG_END.
            # We could do len(BLOCK_TAG_START) to be more "correct", but we've
            # hard-coded the 2s here for performance. And it's not like
            # the TAG_START values are going to change anytime, anyway.
            block_content = token_string[2:-2].strip()
            if self.verbatim and block_content == self.verbatim:
                self.verbatim = False
        if in_tag and not self.verbatim:
            if token_string.startswith(VARIABLE_TAG_START):
                token = Token(TOKEN_VAR, token_string[2:-2].strip())
            elif token_string.startswith(BLOCK_TAG_START):
                if block_content[:9] in ('verbatim', 'verbatim '):
                    self.verbatim = 'end%s' % block_content
                token = Token(TOKEN_BLOCK, block_content)
            elif token_string.startswith(COMMENT_TAG_START):
                content = ''
                if token_string.find(TRANSLATOR_COMMENT_MARK):
                    content = token_string[2:-2].strip()
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
        if parse_until is None:
            parse_until = []
        nodelist = self.create_nodelist()
        while self.tokens:
            token = self.next_token()
            # Use the raw values here for TOKEN_* for a tiny performance boost.
            if token.token_type == 0:  # TOKEN_TEXT
                self.extend_nodelist(nodelist, TextNode(token.contents), token)
            elif token.token_type == 1:  # TOKEN_VAR
                if not token.contents:
                    self.empty_variable(token)
                try:
                    filter_expression = self.compile_filter(token.contents)
                except TemplateSyntaxError as e:
                    if not self.compile_filter_error(token, e):
                        raise
                var_node = self.create_variable_node(filter_expression)
                self.extend_nodelist(nodelist, var_node, token)
            elif token.token_type == 2:  # TOKEN_BLOCK
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    self.empty_block_tag(token)
                if command in parse_until:
                    # put token back on token list so calling
                    # code knows why it terminated
                    self.prepend_token(token)
                    return nodelist
                # execute callback function for this tag and append
                # resulting node
                self.enter_command(command, token)
                try:
                    compile_func = self.tags[command]
                except KeyError:
                    self.invalid_block_tag(token, command, parse_until)
                try:
                    compiled_result = compile_func(self, token)
                except TemplateSyntaxError as e:
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
                raise TemplateSyntaxError("%r must be the first tag "
                                          "in the template." % node)
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
            raise self.error(token, "Invalid block tag: '%s', expected %s" %
                (command, get_text_list(["'%s'" % p for p in parse_until])))
        raise self.error(token, "Invalid block tag: '%s'" % command)

    def unclosed_block_tag(self, parse_until):
        raise self.error(None, "Unclosed tags: %s " % ', '.join(parse_until))

    def compile_filter_error(self, token, e):
        pass

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
        """
        Convenient wrapper for FilterExpression
        """
        return FilterExpression(token, self)

    def find_filter(self, filter_name):
        if filter_name in self.filters:
            return self.filters[filter_name]
        else:
            raise TemplateSyntaxError("Invalid filter: '%s'" % filter_name)


class TokenParser(object):
    """
    Subclass this and implement the top() method to parse a template line.
    When instantiating the parser, pass in the line from the Django template
    parser.

    The parser's "tagname" instance-variable stores the name of the tag that
    the filter was called with.
    """
    def __init__(self, subject):
        self.subject = subject
        self.pointer = 0
        self.backout = []
        self.tagname = self.tag()

    def top(self):
        """
        Overload this method to do the actual parsing and return the result.
        """
        raise NotImplementedError('subclasses of Tokenparser must provide a top() method')

    def more(self):
        """
        Returns True if there is more stuff in the tag.
        """
        return self.pointer < len(self.subject)

    def back(self):
        """
        Undoes the last microparser. Use this for lookahead and backtracking.
        """
        if not len(self.backout):
            raise TemplateSyntaxError("back called without some previous "
                                      "parsing")
        self.pointer = self.backout.pop()

    def tag(self):
        """
        A microparser that just returns the next tag from the line.
        """
        subject = self.subject
        i = self.pointer
        if i >= len(subject):
            raise TemplateSyntaxError("expected another tag, found "
                                      "end of string: %s" % subject)
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
        """
        A microparser that parses for a value: some string constant or
        variable name.
        """
        subject = self.subject
        i = self.pointer

        def next_space_index(subject, i):
            """
            Increment pointer until a real space (i.e. a space not within
            quotes) is encountered
            """
            while i < len(subject) and subject[i] not in (' ', '\t'):
                if subject[i] in ('"', "'"):
                    c = subject[i]
                    i += 1
                    while i < len(subject) and subject[i] != c:
                        i += 1
                    if i >= len(subject):
                        raise TemplateSyntaxError("Searching for value. "
                            "Unexpected end of string in column %d: %s" %
                            (i, subject))
                i += 1
            return i

        if i >= len(subject):
            raise TemplateSyntaxError("Searching for value. Expected another "
                                      "value but found end of string: %s" %
                                      subject)
        if subject[i] in ('"', "'"):
            p = i
            i += 1
            while i < len(subject) and subject[i] != subject[p]:
                i += 1
            if i >= len(subject):
                raise TemplateSyntaxError("Searching for value. Unexpected "
                                          "end of string in column %d: %s" %
                                          (i, subject))
            i += 1

            # Continue parsing until next "real" space,
            # so that filters are also included
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
    'strdq': r'"[^"\\]*(?:\\.[^"\\]*)*"',  # double-quoted string
    'strsq': r"'[^'\\]*(?:\\.[^'\\]*)*'",  # single-quoted string
    'i18n_open': re.escape("_("),
    'i18n_close': re.escape(")"),
}
constant_string = constant_string.replace("\n", "")

filter_raw_string = r"""
^(?P<constant>%(constant)s)|
^(?P<var>[%(var_chars)s]+|%(num)s)|
 (?:\s*%(filter_sep)s\s*
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
    'var_chars': "\w\.",
    'filter_sep': re.escape(FILTER_SEPARATOR),
    'arg_sep': re.escape(FILTER_ARGUMENT_SEPARATOR),
}

filter_re = re.compile(filter_raw_string, re.UNICODE | re.VERBOSE)


class FilterExpression(object):
    """
    Parses a variable token and its optional filters (all as a single string),
    and return a list of tuples of the filter name and arguments.
    Sample::

        >>> token = 'variable|default:"Default value"|date:"Y-m-d"'
        >>> p = Parser('')
        >>> fe = FilterExpression(token, p)
        >>> len(fe.filters)
        2
        >>> fe.var
        <Variable: 'variable'>
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
                raise TemplateSyntaxError("Could not parse some characters: "
                                          "%s|%s|%s" %
                                          (token[:upto], token[upto:start],
                                           token[start:]))
            if var_obj is None:
                var, constant = match.group("var", "constant")
                if constant:
                    try:
                        var_obj = Variable(constant).resolve({})
                    except VariableDoesNotExist:
                        var_obj = None
                elif var is None:
                    raise TemplateSyntaxError("Could not find variable at "
                                              "start of %s." % token)
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
            raise TemplateSyntaxError("Could not parse the remainder: '%s' "
                                      "from '%s'" % (token[upto:], token))

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
            if getattr(func, 'expects_localtime', False):
                obj = template_localtime(obj, context.use_tz)
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
        # First argument, filter input, is implied.
        plen = len(provided) + 1
        # Check to see if a decorator is providing the real function.
        func = getattr(func, '_decorated_function', func)
        args, varargs, varkw, defaults = getargspec(func)
        alen = len(args)
        dlen = len(defaults or [])
        # Not enough OR Too many
        if plen < (alen - dlen) or plen > alen:
            raise TemplateSyntaxError("%s requires %d arguments, %d provided" %
                                      (name, alen - dlen, plen))

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
    """
    A template variable, resolvable against a given context. The variable may
    be a hard-coded string (if it begins and ends with single or double quote
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
        self.message_context = None

        if not isinstance(var, six.string_types):
            raise TypeError(
                "Variable must be a string or number, got %s" % type(var))
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
                    raise TemplateSyntaxError("Variables and attributes may "
                                              "not begin with underscores: '%s'" %
                                              var)
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
            if self.message_context:
                return pgettext_lazy(self.message_context, value)
            else:
                return ugettext_lazy(value)
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
        try:  # catch-all for silent variable failures
            for bit in self.lookups:
                try:  # dictionary lookup
                    current = current[bit]
                except (TypeError, AttributeError, KeyError, ValueError):
                    try:  # attribute lookup
                        # Don't return class attributes if the class is the context:
                        if isinstance(current, BaseContext) and getattr(type(current), bit):
                            raise AttributeError
                        current = getattr(current, bit)
                    except (TypeError, AttributeError):
                        try:  # list-index lookup
                            current = current[int(bit)]
                        except (IndexError,  # list index out of range
                                ValueError,  # invalid literal for int()
                                KeyError,    # current is a dict without `int(bit)` key
                                TypeError):  # unsubscriptable object
                            raise VariableDoesNotExist("Failed lookup for key "
                                                       "[%s] in %r",
                                                       (bit, current))  # missing attribute
                if callable(current):
                    if getattr(current, 'do_not_call_in_templates', False):
                        pass
                    elif getattr(current, 'alters_data', False):
                        current = settings.TEMPLATE_STRING_IF_INVALID
                    else:
                        try:  # method call (assuming no args required)
                            current = current()
                        except TypeError:
                            try:
                                getcallargs(current)
                            except TypeError:  # arguments *were* required
                                current = settings.TEMPLATE_STRING_IF_INVALID  # invalid method call
                            else:
                                raise
        except Exception as e:
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
        """
        Return the node rendered as a string.
        """
        pass

    def __iter__(self):
        yield self

    def get_nodes_by_type(self, nodetype):
        """
        Return a list of all nodes (within this node and its nodelist)
        of the given type
        """
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
                bit = self.render_node(node, context)
            else:
                bit = node
            bits.append(force_text(bit))
        return mark_safe(''.join(bits))

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
        return force_str("<Text Node: '%s'>" % self.s[:25], 'ascii',
                errors='replace')

    def render(self, context):
        return self.s


def render_value_in_context(value, context):
    """
    Converts any value to a string to become part of a rendered template. This
    means escaping, if required, and conversion to a unicode object. If value
    is a string, it is expected to have already been translated.
    """
    value = template_localtime(value, use_tz=context.use_tz)
    value = localize(value, use_l10n=context.use_l10n)
    value = force_text(value)
    if ((context.autoescape and not isinstance(value, SafeData)) or
            isinstance(value, EscapeData)):
        return conditional_escape(value)
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
            # control (e.g. exception rendering). In that case, we fail
            # quietly.
            return ''
        return render_value_in_context(output, context)

# Regex for token keyword arguments
kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")


def token_kwargs(bits, parser, support_legacy=False):
    """
    A utility method for parsing token keyword arguments.

    :param bits: A list containing remainder of the token (split by spaces)
        that is to be checked for arguments. Valid arguments will be removed
        from this list.

    :param support_legacy: If set to true ``True``, the legacy format
        ``1 as foo`` will be accepted. Otherwise, only the standard ``foo=1``
        format is allowed.

    :returns: A dictionary of the arguments retrieved from the ``bits`` token
        list.

    There is no requirement for all remaining token ``bits`` to be keyword
    arguments, so the dictionary will be returned as soon as an invalid
    argument format is reached.
    """
    if not bits:
        return {}
    match = kwarg_re.match(bits[0])
    kwarg_format = match and match.group(1)
    if not kwarg_format:
        if not support_legacy:
            return {}
        if len(bits) < 3 or bits[1] != 'as':
            return {}

    kwargs = {}
    while bits:
        if kwarg_format:
            match = kwarg_re.match(bits[0])
            if not match or not match.group(1):
                return kwargs
            key, value = match.groups()
            del bits[:1]
        else:
            if len(bits) < 3 or bits[1] != 'as':
                return kwargs
            key, value = bits[2], bits[0]
            del bits[:3]
        kwargs[key] = parser.compile_filter(value)
        if bits and not kwarg_format:
            if bits[0] != 'and':
                return kwargs
            del bits[:1]
    return kwargs


def parse_bits(parser, bits, params, varargs, varkw, defaults,
               takes_context, name):
    """
    Parses bits for template tag helpers (simple_tag, include_tag and
    assignment_tag), in particular by detecting syntax errors and by
    extracting positional and keyword arguments.
    """
    if takes_context:
        if params[0] == 'context':
            params = params[1:]
        else:
            raise TemplateSyntaxError(
                "'%s' is decorated with takes_context=True so it must "
                "have a first argument of 'context'" % name)
    args = []
    kwargs = {}
    unhandled_params = list(params)
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        kwarg = token_kwargs([bit], parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = list(six.iteritems(kwarg))[0]
            if param not in params and varkw is None:
                # An unexpected keyword argument was supplied
                raise TemplateSyntaxError(
                    "'%s' received unexpected keyword argument '%s'" %
                    (name, param))
            elif param in kwargs:
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError(
                    "'%s' received multiple values for keyword argument '%s'" %
                    (name, param))
            else:
                # All good, record the keyword argument
                kwargs[str(param)] = value
                if param in unhandled_params:
                    # If using the keyword syntax for a positional arg, then
                    # consume it.
                    unhandled_params.remove(param)
        else:
            if kwargs:
                raise TemplateSyntaxError(
                    "'%s' received some positional argument(s) after some "
                    "keyword argument(s)" % name)
            else:
                # Record the positional argument
                args.append(parser.compile_filter(bit))
                try:
                    # Consume from the list of expected positional arguments
                    unhandled_params.pop(0)
                except IndexError:
                    if varargs is None:
                        raise TemplateSyntaxError(
                            "'%s' received too many positional arguments" %
                            name)
    if defaults is not None:
        # Consider the last n params handled, where n is the
        # number of defaults.
        unhandled_params = unhandled_params[:-len(defaults)]
    if unhandled_params:
        # Some positional arguments were not supplied
        raise TemplateSyntaxError(
            "'%s' did not receive value(s) for the argument(s): %s" %
            (name, ", ".join("'%s'" % p for p in unhandled_params)))
    return args, kwargs


def generic_tag_compiler(parser, token, params, varargs, varkw, defaults,
                         name, takes_context, node_class):
    """
    Returns a template.Node subclass.
    """
    bits = token.split_contents()[1:]
    args, kwargs = parse_bits(parser, bits, params, varargs, varkw,
                              defaults, takes_context, name)
    return node_class(takes_context, args, kwargs)


class TagHelperNode(Node):
    """
    Base class for tag helper nodes such as SimpleNode, InclusionNode and
    AssignmentNode. Manages the positional and keyword arguments to be passed
    to the decorated function.
    """

    def __init__(self, takes_context, args, kwargs):
        self.takes_context = takes_context
        self.args = args
        self.kwargs = kwargs

    def get_resolved_arguments(self, context):
        resolved_args = [var.resolve(context) for var in self.args]
        if self.takes_context:
            resolved_args = [context] + resolved_args
        resolved_kwargs = dict((k, v.resolve(context)) for k, v in self.kwargs.items())
        return resolved_args, resolved_kwargs


class Library(object):
    def __init__(self):
        self.filters = {}
        self.tags = {}

    def tag(self, name=None, compile_function=None):
        if name is None and compile_function is None:
            # @register.tag()
            return self.tag_function
        elif name is not None and compile_function is None:
            if callable(name):
                # @register.tag
                return self.tag_function(name)
            else:
                # @register.tag('somename') or @register.tag(name='somename')
                def dec(func):
                    return self.tag(name, func)
                return dec
        elif name is not None and compile_function is not None:
            # register.tag('somename', somefunc)
            self.tags[name] = compile_function
            return compile_function
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.tag: (%r, %r)", (name, compile_function))

    def tag_function(self, func):
        self.tags[getattr(func, "_decorated_function", func).__name__] = func
        return func

    def filter(self, name=None, filter_func=None, **flags):
        if name is None and filter_func is None:
            # @register.filter()
            def dec(func):
                return self.filter_function(func, **flags)
            return dec

        elif name is not None and filter_func is None:
            if callable(name):
                # @register.filter
                return self.filter_function(name, **flags)
            else:
                # @register.filter('somename') or @register.filter(name='somename')
                def dec(func):
                    return self.filter(name, func, **flags)
                return dec

        elif name is not None and filter_func is not None:
            # register.filter('somename', somefunc)
            self.filters[name] = filter_func
            for attr in ('expects_localtime', 'is_safe', 'needs_autoescape'):
                if attr in flags:
                    value = flags[attr]
                    # set the flag on the filter for FilterExpression.resolve
                    setattr(filter_func, attr, value)
                    # set the flag on the innermost decorated function
                    # for decorators that need it e.g. stringfilter
                    if hasattr(filter_func, "_decorated_function"):
                        setattr(filter_func._decorated_function, attr, value)
            filter_func._filter_name = name
            return filter_func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.filter: (%r, %r)", (name, filter_func))

    def filter_function(self, func, **flags):
        name = getattr(func, "_decorated_function", func).__name__
        return self.filter(name, func, **flags)

    def simple_tag(self, func=None, takes_context=None, name=None):
        def dec(func):
            params, varargs, varkw, defaults = getargspec(func)

            class SimpleNode(TagHelperNode):

                def render(self, context):
                    resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                    return func(*resolved_args, **resolved_kwargs)

            function_name = (name or
                getattr(func, '_decorated_function', func).__name__)
            compile_func = partial(generic_tag_compiler,
                params=params, varargs=varargs, varkw=varkw,
                defaults=defaults, name=function_name,
                takes_context=takes_context, node_class=SimpleNode)
            compile_func.__doc__ = func.__doc__
            self.tag(function_name, compile_func)
            return func

        if func is None:
            # @register.simple_tag(...)
            return dec
        elif callable(func):
            # @register.simple_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to simple_tag")

    def assignment_tag(self, func=None, takes_context=None, name=None):
        def dec(func):
            params, varargs, varkw, defaults = getargspec(func)

            class AssignmentNode(TagHelperNode):
                def __init__(self, takes_context, args, kwargs, target_var):
                    super(AssignmentNode, self).__init__(takes_context, args, kwargs)
                    self.target_var = target_var

                def render(self, context):
                    resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                    context[self.target_var] = func(*resolved_args, **resolved_kwargs)
                    return ''

            function_name = (name or
                getattr(func, '_decorated_function', func).__name__)

            def compile_func(parser, token):
                bits = token.split_contents()[1:]
                if len(bits) < 2 or bits[-2] != 'as':
                    raise TemplateSyntaxError(
                        "'%s' tag takes at least 2 arguments and the "
                        "second last argument must be 'as'" % function_name)
                target_var = bits[-1]
                bits = bits[:-2]
                args, kwargs = parse_bits(parser, bits, params,
                    varargs, varkw, defaults, takes_context, function_name)
                return AssignmentNode(takes_context, args, kwargs, target_var)

            compile_func.__doc__ = func.__doc__
            self.tag(function_name, compile_func)
            return func

        if func is None:
            # @register.assignment_tag(...)
            return dec
        elif callable(func):
            # @register.assignment_tag
            return dec(func)
        else:
            raise TemplateSyntaxError("Invalid arguments provided to assignment_tag")

    def inclusion_tag(self, file_name, context_class=Context, takes_context=False, name=None):
        def dec(func):
            params, varargs, varkw, defaults = getargspec(func)

            class InclusionNode(TagHelperNode):

                def render(self, context):
                    resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                    _dict = func(*resolved_args, **resolved_kwargs)

                    if not getattr(self, 'nodelist', False):
                        from django.template.loader import get_template, select_template
                        if isinstance(file_name, Template):
                            t = file_name
                        elif not isinstance(file_name, six.string_types) and is_iterable(file_name):
                            t = select_template(file_name)
                        else:
                            t = get_template(file_name)
                        self.nodelist = t.nodelist
                    new_context = context_class(_dict, **{
                        'autoescape': context.autoescape,
                        'current_app': context.current_app,
                        'use_l10n': context.use_l10n,
                        'use_tz': context.use_tz,
                    })
                    # Copy across the CSRF token, if present, because
                    # inclusion tags are often used for forms, and we need
                    # instructions for using CSRF protection to be as simple
                    # as possible.
                    csrf_token = context.get('csrf_token', None)
                    if csrf_token is not None:
                        new_context['csrf_token'] = csrf_token
                    return self.nodelist.render(new_context)

            function_name = (name or
                getattr(func, '_decorated_function', func).__name__)
            compile_func = partial(generic_tag_compiler,
                params=params, varargs=varargs, varkw=varkw,
                defaults=defaults, name=function_name,
                takes_context=takes_context, node_class=InclusionNode)
            compile_func.__doc__ = func.__doc__
            self.tag(function_name, compile_func)
            return func
        return dec


def is_library_missing(name):
    """Check if library that failed to load cannot be found under any
    templatetags directory or does exist but fails to import.

    Non-existing condition is checked recursively for each subpackage in cases
    like <appdir>/templatetags/subpackage/package/module.py.
    """
    # Don't bother to check if '.' is in name since any name will be prefixed
    # with some template root.
    path, module = name.rsplit('.', 1)
    try:
        package = import_module(path)
        return not module_has_submodule(package, module)
    except ImportError:
        return is_library_missing(path)


def import_library(taglib_module):
    """
    Load a template tag library module.

    Verifies that the library contains a 'register' attribute, and
    returns that attribute as the representation of the library
    """
    try:
        mod = import_module(taglib_module)
    except ImportError as e:
        # If the ImportError is because the taglib submodule does not exist,
        # that's not an error that should be raised. If the submodule exists
        # and raised an ImportError on the attempt to load it, that we want
        # to raise.
        if is_library_missing(taglib_module):
            return None
        else:
            raise InvalidTemplateLibrary("ImportError raised loading %s: %s" %
                                         (taglib_module, e))
    try:
        return mod.register
    except AttributeError:
        raise InvalidTemplateLibrary("Template library %s does not have "
                                     "a variable named 'register'" %
                                     taglib_module)

templatetags_modules = []


def get_templatetags_modules():
    """
    Return the list of all available template tag modules.

    Caches the result for faster access.
    """
    global templatetags_modules
    if not templatetags_modules:
        _templatetags_modules = []
        # Populate list once per process. Mutate the local list first, and
        # then assign it to the global name to ensure there are no cases where
        # two threads try to populate it simultaneously.

        templatetags_modules_candidates = ['django.templatetags']
        templatetags_modules_candidates += ['%s.templatetags' % app_config.name
            for app_config in apps.get_app_configs()]
        for templatetag_module in templatetags_modules_candidates:
            try:
                import_module(templatetag_module)
                _templatetags_modules.append(templatetag_module)
            except ImportError:
                continue
        templatetags_modules = _templatetags_modules
    return templatetags_modules


def get_library(library_name):
    """
    Load the template library module with the given name.

    If library is not already loaded loop over all templatetags modules
    to locate it.

    {% load somelib %} and {% load someotherlib %} loops twice.

    Subsequent loads eg. {% load somelib %} in the same process will grab
    the cached module from libraries.
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
            raise InvalidTemplateLibrary("Template library %s not found, "
                                         "tried %s" %
                                         (library_name,
                                          ','.join(tried_modules)))
    return lib


def add_to_builtins(module):
    builtins.append(import_library(module))


add_to_builtins('django.template.defaulttags')
add_to_builtins('django.template.defaultfilters')
add_to_builtins('django.template.loader_tags')
