"""
This is the Django template system.

How it works:

The Lexer.tokenize() function converts a template string (i.e., a string containing
markup with custom template tags) to tokens, which can be either plain text
(TOKEN_TEXT), variables (TOKEN_VAR) or block statements (TOKEN_BLOCK).

The Parser() class takes a list of tokens in its constructor, and its parse()
method returns a compiled template -- which is, under the hood, a list of
Node objects.

Each Node is responsible for creating some sort of output -- e.g. simple text
(TextNode), variable values in a given context (VariableNode), results of basic
logic (IfNode), results of looping (ForNode), or anything else. The core Node
types are TextNode, VariableNode, IfNode and ForNode, but plugin modules can
define their own custom node types.

Each Node has a render() method, which takes a Context and returns a string of
the rendered node. For example, the render() method of a Variable Node returns
the variable's value as a string. The render() method of an IfNode returns the
rendered output of whatever was inside the loop, recursively.

The Template class is a convenient wrapper that takes care of template
compilation and rendering.

Usage:

The only thing you should ever use directly in this file is the Template class.
Create a compiled template object with a template_string, then call render()
with a context. In the compilation stage, the TemplateSyntaxError exception
will be raised if the template doesn't have proper syntax.

Sample code:

>>> import template
>>> s = '''
... <html>
... {% if test %}
...     <h1>{{ varvalue }}</h1>
... {% endif %}
... </html>
... '''
>>> t = template.Template(s)

(t is now a compiled template, and its render() method can be called multiple
times with multiple contexts)

>>> c = template.Context({'test':True, 'varvalue': 'Hello'})
>>> t.render(c)
'\n<html>\n\n    <h1>Hello</h1>\n\n</html>\n'
>>> c = template.Context({'test':False, 'varvalue': 'Hello'})
>>> t.render(c)
'\n<html>\n\n</html>\n'
"""
import re
from inspect import getargspec
from django.utils.functional import curry
from django.conf import settings
from django.template.context import Context, RequestContext, ContextPopException

__all__ = ('Template', 'Context', 'RequestContext', 'compile_string')

TOKEN_TEXT = 0
TOKEN_VAR = 1
TOKEN_BLOCK = 2

# template syntax constants
FILTER_SEPARATOR = '|'
FILTER_ARGUMENT_SEPARATOR = ':'
VARIABLE_ATTRIBUTE_SEPARATOR = '.'
BLOCK_TAG_START = '{%'
BLOCK_TAG_END = '%}'
VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'

ALLOWED_VARIABLE_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'

# what to report as the origin for templates that come from non-loader sources
# (e.g. strings)
UNKNOWN_SOURCE="&lt;unknown source&gt;"

# match a variable or block tag and capture the entire tag, including start/end delimiters
tag_re = re.compile('(%s.*?%s|%s.*?%s)' % (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
                                          re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END)))

# global dictionary of libraries that have been loaded using get_library
libraries = {}
# global list of libraries to load by default for a new parser
builtins = []

class TemplateSyntaxError(Exception):
    pass

class TemplateDoesNotExist(Exception):
    pass

class VariableDoesNotExist(Exception):
    pass

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

class Template:
    def __init__(self, template_string, origin=None):
        "Compilation stage"
        if settings.TEMPLATE_DEBUG and origin == None:
            origin = StringOrigin(template_string)
            # Could do some crazy stack-frame stuff to record where this string
            # came from...
        self.nodelist = compile_string(template_string, origin)

    def __iter__(self):
        for node in self.nodelist:
            for subnode in node:
                yield subnode

    def render(self, context):
        "Display stage -- can be called many times"
        return self.nodelist.render(context)

def compile_string(template_string, origin):
    "Compiles template_string into NodeList ready for rendering"
    lexer = lexer_factory(template_string, origin)
    parser = parser_factory(lexer.tokenize())
    return parser.parse()

class Token:
    def __init__(self, token_type, contents):
        "The token_type must be TOKEN_TEXT, TOKEN_VAR or TOKEN_BLOCK"
        self.token_type, self.contents = token_type, contents

    def __str__(self):
        return '<%s token: "%s...">' % (
            {TOKEN_TEXT: 'Text', TOKEN_VAR: 'Var', TOKEN_BLOCK: 'Block'}[self.token_type],
            self.contents[:20].replace('\n', '')
            )

    def __repr__(self):
        return '<%s token: "%s">' % (
            {TOKEN_TEXT: 'Text', TOKEN_VAR: 'Var', TOKEN_BLOCK: 'Block'}[self.token_type],
            self.contents[:].replace('\n', '')
            )

class Lexer(object):
    def __init__(self, template_string, origin):
        self.template_string = template_string
        self.origin = origin

    def tokenize(self):
        "Return a list of tokens from a given template_string"
        # remove all empty strings, because the regex has a tendency to add them
        bits = filter(None, tag_re.split(self.template_string))
        return map(self.create_token, bits)

    def create_token(self,token_string):
        "Convert the given token string into a new Token object and return it"
        if token_string.startswith(VARIABLE_TAG_START):
            token = Token(TOKEN_VAR, token_string[len(VARIABLE_TAG_START):-len(VARIABLE_TAG_END)].strip())
        elif token_string.startswith(BLOCK_TAG_START):
            token = Token(TOKEN_BLOCK, token_string[len(BLOCK_TAG_START):-len(BLOCK_TAG_END)].strip())
        else:
            token = Token(TOKEN_TEXT, token_string)
        return token

class DebugLexer(Lexer):
    def __init__(self, template_string, origin):
        super(DebugLexer, self).__init__(template_string, origin)

    def tokenize(self):
        "Return a list of tokens from a given template_string"
        token_tups, upto = [], 0
        for match in tag_re.finditer(self.template_string):
            start, end = match.span()
            if start > upto:
                token_tups.append( (self.template_string[upto:start], (upto, start)) )
                upto = start
            token_tups.append( (self.template_string[start:end], (start,end)) )
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
           token_tups.append( (last_bit, (upto, upto + len(last_bit))) )
        return [self.create_token(tok, (self.origin, loc)) for tok, loc in token_tups]

    def create_token(self, token_string, source):
        token = super(DebugLexer, self).create_token(token_string)
        token.source = source
        return token

class Parser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.tags = {}
        self.filters = {}
        for lib in builtins:
            self.add_library(lib)

    def parse(self, parse_until=[]):
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
                    self.invalid_block_tag(token, command)
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
        nodelist.append(node)

    def enter_command(self, command, token):
        pass

    def exit_command(self):
        pass

    def error(self, token, msg ):
        return TemplateSyntaxError(msg)

    def empty_variable(self, token):
        raise self.error( token, "Empty variable tag")

    def empty_block_tag(self, token):
        raise self.error( token, "Empty block tag")

    def invalid_block_tag(self, token, command):
        raise self.error( token, "Invalid block tag: '%s'" % command)

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

    def compile_filter(self,token):
        "Convenient wrapper for FilterExpression"
        return FilterExpression(token, self)

    def find_filter(self, filter_name):
        if self.filters.has_key(filter_name):
            return self.filters[filter_name]
        else:
            raise TemplateSyntaxError, "Invalid filter: '%s'" % filter_name

class DebugParser(Parser):
    def __init__(self, lexer):
        super(DebugParser, self).__init__(lexer)
        self.command_stack = []

    def enter_command(self, command, token):
        self.command_stack.append( (command, token.source) )

    def exit_command(self):
        self.command_stack.pop()

    def error(self, token, msg):
        return self.source_error(token.source, msg)

    def source_error(self, source,msg):
        e = TemplateSyntaxError(msg)
        e.source = source
        return e

    def create_nodelist(self):
        return DebugNodeList()

    def create_variable_node(self, contents):
        return DebugVariableNode(contents)

    def extend_nodelist(self, nodelist, node, token):
        node.source = token.source
        super(DebugParser, self).extend_nodelist(nodelist, node, token)

    def unclosed_block_tag(self, parse_until):
        (command, source) = self.command_stack.pop()
        msg = "Unclosed tag '%s'. Looking for one of: %s " % (command, ', '.join(parse_until))
        raise self.source_error( source, msg)

    def compile_function_error(self, token, e):
        if not hasattr(e, 'source'):
            e.source = token.source


def lexer_factory(*args, **kwargs):
    if settings.TEMPLATE_DEBUG:
        return DebugLexer(*args, **kwargs)
    else:
        return Lexer(*args, **kwargs)

def parser_factory(*args, **kwargs):
    if settings.TEMPLATE_DEBUG:
        return DebugParser(*args, **kwargs)
    else:
        return Parser(*args, **kwargs)


class TokenParser:
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
        raise NotImplemented

    def more(self):
        "Returns True if there is more stuff in the tag."
        return self.pointer < len(self.subject)

    def back(self):
        "Undoes the last microparser. Use this for lookahead and backtracking."
        if not len(self.backout):
            raise TemplateSyntaxError, "back called without some previous parsing"
        self.pointer = self.backout.pop()

    def tag(self):
        "A microparser that just returns the next tag from the line."
        subject = self.subject
        i = self.pointer
        if i >= len(subject):
            raise TemplateSyntaxError, "expected another tag, found end of string: %s" % subject
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
        if i >= len(subject):
            raise TemplateSyntaxError, "Searching for value. Expected another value but found end of string: %s" % subject
        if subject[i] in ('"', "'"):
            p = i
            i += 1
            while i < len(subject) and subject[i] != subject[p]:
                i += 1
            if i >= len(subject):
                raise TemplateSyntaxError, "Searching for value. Unexpected end of string in column %d: %s" % subject
            i += 1
            res = subject[p:i]
            while i < len(subject) and subject[i] in (' ', '\t'):
                i += 1
            self.backout.append(self.pointer)
            self.pointer = i
            return res
        else:
            p = i
            while i < len(subject) and subject[i] not in (' ', '\t'):
                if subject[i] in ('"', "'"):
                    c = subject[i]
                    i += 1
                    while i < len(subject) and subject[i] != c:
                        i += 1
                    if i >= len(subject):
                        raise TemplateSyntaxError, "Searching for value. Unexpected end of string in column %d: %s" % subject
                i += 1
            s = subject[p:i]
            while i < len(subject) and subject[i] in (' ', '\t'):
                i += 1
            self.backout.append(self.pointer)
            self.pointer = i
            return s




filter_raw_string = r"""
^%(i18n_open)s"(?P<i18n_constant>%(str)s)"%(i18n_close)s|
^"(?P<constant>%(str)s)"|
^(?P<var>[%(var_chars)s]+)|
 (?:%(filter_sep)s
     (?P<filter_name>\w+)
         (?:%(arg_sep)s
             (?:
              %(i18n_open)s"(?P<i18n_arg>%(str)s)"%(i18n_close)s|
              "(?P<constant_arg>%(str)s)"|
              (?P<var_arg>[%(var_chars)s]+)
             )
         )?
 )""" % {
    'str': r"""[^"\\]*(?:\\.[^"\\]*)*""",
    'var_chars': "A-Za-z0-9\_\." ,
    'filter_sep': re.escape(FILTER_SEPARATOR),
    'arg_sep': re.escape(FILTER_ARGUMENT_SEPARATOR),
    'i18n_open' : re.escape("_("),
    'i18n_close' : re.escape(")"),
  }

filter_raw_string = filter_raw_string.replace("\n", "").replace(" ", "")
filter_re = re.compile(filter_raw_string)

class FilterExpression(object):
    """
    Parses a variable token and its optional filters (all as a single string),
    and return a list of tuples of the filter name and arguments.
    Sample:
        >>> token = 'variable|default:"Default value"|date:"Y-m-d"'
        >>> p = FilterParser(token)
        >>> p.filters
        [('default', 'Default value'), ('date', 'Y-m-d')]
        >>> p.var
        'variable'

    This class should never be instantiated outside of the
    get_filters_from_token helper function.
    """
    def __init__(self, token, parser):
        self.token = token
        matches = filter_re.finditer(token)
        var = None
        filters = []
        upto = 0
        for match in matches:
            start = match.start()
            if upto != start:
                raise TemplateSyntaxError, "Could not parse some characters: %s|%s|%s"  % \
                                           (token[:upto], token[upto:start], token[start:])
            if var == None:
                var, constant, i18n_constant = match.group("var", "constant", "i18n_constant")
                if i18n_constant:
                    var = '"%s"' %  _(i18n_constant)
                elif constant:
                    var = '"%s"' % constant
                upto = match.end()
                if var == None:
                    raise TemplateSyntaxError, "Could not find variable at start of %s" % token
                elif var.find(VARIABLE_ATTRIBUTE_SEPARATOR + '_') > -1 or var[0] == '_':
                    raise TemplateSyntaxError, "Variables and attributes may not begin with underscores: '%s'" % var
            else:
                filter_name = match.group("filter_name")
                args = []
                constant_arg, i18n_arg, var_arg = match.group("constant_arg", "i18n_arg", "var_arg")
                if i18n_arg:
                    args.append((False, _(i18n_arg.replace('\\', ''))))
                elif constant_arg:
                    args.append((False, constant_arg.replace('\\', '')))
                elif var_arg:
                    args.append((True, var_arg))
                filter_func = parser.find_filter(filter_name)
                self.args_check(filter_name,filter_func, args)
                filters.append( (filter_func,args))
                upto = match.end()
        if upto != len(token):
            raise TemplateSyntaxError, "Could not parse the remainder: %s" % token[upto:]
        self.var , self.filters = var, filters

    def resolve(self, context):
        try:
            obj = resolve_variable(self.var, context)
        except VariableDoesNotExist:
            obj = settings.TEMPLATE_STRING_IF_INVALID
        for func, args in self.filters:
            arg_vals = []
            for lookup, arg in args:
                if not lookup:
                    arg_vals.append(arg)
                else:
                    arg_vals.append(resolve_variable(arg, context))
            obj = func(obj, *arg_vals)
        return obj

    def args_check(name, func, provided):
        provided = list(provided)
        plen = len(provided)
        (args, varargs, varkw, defaults) = getargspec(func)
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
            raise TemplateSyntaxError, "%s requires %d arguments, %d provided" % (name, len(nondefs), plen)

        # Defaults can be overridden.
        defaults = defaults and list(defaults) or []
        try:
            for parg in provided:
                defaults.pop(0)
        except IndexError:
            # Too many.
            raise TemplateSyntaxError, "%s requires %d arguments, %d provided" % (name, len(nondefs), plen)

        return True
    args_check = staticmethod(args_check)

    def __str__(self):
        return self.token

def resolve_variable(path, context):
    """
    Returns the resolved variable, which may contain attribute syntax, within
    the given context. The variable may be a hard-coded string (if it begins
    and ends with single or double quote marks).

    >>> c = {'article': {'section':'News'}}
    >>> resolve_variable('article.section', c)
    'News'
    >>> resolve_variable('article', c)
    {'section': 'News'}
    >>> class AClass: pass
    >>> c = AClass()
    >>> c.article = AClass()
    >>> c.article.section = 'News'
    >>> resolve_variable('article.section', c)
    'News'

    (The example assumes VARIABLE_ATTRIBUTE_SEPARATOR is '.')
    """
    if path[0] in '0123456789':
        number_type = '.' in path and float or int
        try:
            current = number_type(path)
        except ValueError:
            current = settings.TEMPLATE_STRING_IF_INVALID
    elif path[0] in ('"', "'") and path[0] == path[-1]:
        current = path[1:-1]
    else:
        current = context
        bits = path.split(VARIABLE_ATTRIBUTE_SEPARATOR)
        while bits:
            try: # dictionary lookup
                current = current[bits[0]]
            except (TypeError, AttributeError, KeyError):
                try: # attribute lookup
                    current = getattr(current, bits[0])
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
                except (TypeError, AttributeError):
                    try: # list-index lookup
                        current = current[int(bits[0])]
                    except (IndexError, ValueError, KeyError):
                        raise VariableDoesNotExist, "Failed lookup for key [%s] in %r" % (bits[0], current) # missing attribute
                except Exception, e:
                    if getattr(e, 'silent_variable_failure', False):
                        current = settings.TEMPLATE_STRING_IF_INVALID
                    else:
                        raise        
            del bits[0]
    return current

class Node:
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
        if hasattr(self, 'nodelist'):
            nodes.extend(self.nodelist.get_nodes_by_type(nodetype))
        return nodes

class NodeList(list):
    def render(self, context):
        bits = []
        for node in self:
            if isinstance(node, Node):
                bits.append(self.render_node(node, context))
            else:
                bits.append(node)
        return ''.join(bits)

    def get_nodes_by_type(self, nodetype):
        "Return a list of all nodes of the given type"
        nodes = []
        for node in self:
            nodes.extend(node.get_nodes_by_type(nodetype))
        return nodes

    def render_node(self, node, context):
        return(node.render(context))

class DebugNodeList(NodeList):
    def render_node(self, node, context):
        try:
            result = node.render(context)
        except TemplateSyntaxError, e:
            if not hasattr(e, 'source'):
                e.source = node.source
            raise
        except Exception:
            from sys import exc_info
            wrapped = TemplateSyntaxError('Caught an exception while rendering.')
            wrapped.source = node.source
            wrapped.exc_info = exc_info()
            raise wrapped
        return result

class TextNode(Node):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "<Text Node: '%s'>" % self.s[:25]

    def render(self, context):
        return self.s

class VariableNode(Node):
    def __init__(self, filter_expression):
        self.filter_expression = filter_expression

    def __repr__(self):
        return "<Variable Node: %s>" % self.filter_expression

    def encode_output(self, output):
        # Check type so that we don't run str() on a Unicode object
        if not isinstance(output, basestring):
            return str(output)
        elif isinstance(output, unicode):
            return output.encode(settings.DEFAULT_CHARSET)
        else:
            return output

    def render(self, context):
        output = self.filter_expression.resolve(context)
        return self.encode_output(output)

class DebugVariableNode(VariableNode):
    def render(self, context):
        try:
             output = self.filter_expression.resolve(context)
        except TemplateSyntaxError, e:
            if not hasattr(e, 'source'):
                e.source = self.source
            raise
        return self.encode_output(output)

def generic_tag_compiler(params, defaults, name, node_class, parser, token):
    "Returns a template.Node subclass."
    bits = token.contents.split()[1:]
    bmax = len(params)
    def_len = defaults and len(defaults) or 0
    bmin = bmax - def_len
    if(len(bits) < bmin or len(bits) > bmax):
        if bmin == bmax:
            message = "%s takes %s arguments" % (name, bmin)
        else:
            message = "%s takes between %s and %s arguments" % (name, bmin, bmax)
        raise TemplateSyntaxError, message
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
            raise InvalidTemplateLibrary, "Unsupported arguments to Library.tag: (%r, %r)", (name, compile_function)

    def tag_function(self,func):
        self.tags[func.__name__] = func
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
            raise InvalidTemplateLibrary, "Unsupported arguments to Library.filter: (%r, %r, %r)", (name, compile_function, has_arg)

    def filter_function(self, func):
        self.filters[func.__name__] = func
        return func

    def simple_tag(self,func):
        (params, xx, xxx, defaults) = getargspec(func)

        class SimpleNode(Node):
            def __init__(self, vars_to_resolve):
                self.vars_to_resolve = vars_to_resolve

            def render(self, context):
                resolved_vars = [resolve_variable(var, context) for var in self.vars_to_resolve]
                return func(*resolved_vars)

        compile_func = curry(generic_tag_compiler, params, defaults, func.__name__, SimpleNode)
        compile_func.__doc__ = func.__doc__
        self.tag(func.__name__, compile_func)
        return func

    def inclusion_tag(self, file_name, context_class=Context, takes_context=False):
        def dec(func):
            (params, xx, xxx, defaults) = getargspec(func)
            if takes_context:
                if params[0] == 'context':
                    params = params[1:]
                else:
                    raise TemplateSyntaxError, "Any tag function decorated with takes_context=True must have a first argument of 'context'"

            class InclusionNode(Node):
                def __init__(self, vars_to_resolve):
                    self.vars_to_resolve = vars_to_resolve

                def render(self, context):
                    resolved_vars = [resolve_variable(var, context) for var in self.vars_to_resolve]
                    if takes_context:
                        args = [context] + resolved_vars
                    else:
                        args = resolved_vars

                    dict = func(*args)

                    if not getattr(self, 'nodelist', False):
                        from django.template.loader import get_template
                        t = get_template(file_name)
                        self.nodelist = t.nodelist
                    return self.nodelist.render(context_class(dict))

            compile_func = curry(generic_tag_compiler, params, defaults, func.__name__, InclusionNode)
            compile_func.__doc__ = func.__doc__
            self.tag(func.__name__, compile_func)
            return func
        return dec

def get_library(module_name):
    lib = libraries.get(module_name, None)
    if not lib:
        try:
            mod = __import__(module_name, '', '', [''])
        except ImportError, e:
            raise InvalidTemplateLibrary, "Could not load template library from %s, %s" % (module_name, e)
        try:
            lib = mod.register
            libraries[module_name] = lib
        except AttributeError:
            raise InvalidTemplateLibrary, "Template library %s does not have a variable named 'register'" % module_name
    return lib

def add_to_builtins(module_name):
    builtins.append(get_library(module_name))

add_to_builtins('django.template.defaulttags')
add_to_builtins('django.template.defaultfilters')
