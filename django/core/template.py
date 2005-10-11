"""
This is the Django template system.

How it works:

The tokenize() function converts a template string (i.e., a string containing
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
from django.conf.settings import DEFAULT_CHARSET

__all__ = ('Template','Context','compile_string')

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

# match a variable or block tag and capture the entire tag, including start/end delimiters
tag_re = re.compile('(%s.*?%s|%s.*?%s)' % (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
                                          re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END)))

# global dict used by register_tag; maps custom tags to callback functions
registered_tags = {}

# global dict used by register_filter; maps custom filters to callback functions
registered_filters = {}

class TemplateSyntaxError(Exception):
    pass

class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass

class TemplateDoesNotExist(Exception):
    pass

class VariableDoesNotExist(Exception):
    pass

class SilentVariableFailure(Exception):
    "Any function raising this exception will be ignored by resolve_variable"
    pass

class Template:
    def __init__(self, template_string):
        "Compilation stage"
        self.nodelist = compile_string(template_string)

    def __iter__(self):
        for node in self.nodelist:
            for subnode in node:
                yield subnode

    def render(self, context):
        "Display stage -- can be called many times"
        return self.nodelist.render(context)

def compile_string(template_string):
    "Compiles template_string into NodeList ready for rendering"
    tokens = tokenize(template_string)
    parser = Parser(tokens)
    return parser.parse()

class Context:
    "A stack container for variable context"
    def __init__(self, dict=None):
        dict = dict or {}
        self.dicts = [dict]

    def __repr__(self):
        return repr(self.dicts)

    def __iter__(self):
        for d in self.dicts:
            yield d

    def push(self):
        self.dicts = [{}] + self.dicts

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        del self.dicts[0]

    def __setitem__(self, key, value):
        "Set a variable in the current context"
        self.dicts[0][key] = value

    def __getitem__(self, key):
        "Get a variable's value, starting at the current context and going upward"
        for dict in self.dicts:
            if dict.has_key(key):
                return dict[key]
        return ''

    def __delitem__(self, key):
        "Delete a variable from the current context"
        del self.dicts[0][key]

    def has_key(self, key):
        for dict in self.dicts:
            if dict.has_key(key):
                return True
        return False

    def update(self, other_dict):
        "Like dict.update(). Pushes an entire dictionary's keys and values onto the context."
        self.dicts = [other_dict] + self.dicts

class Token:
    def __init__(self, token_type, contents):
        "The token_type must be TOKEN_TEXT, TOKEN_VAR or TOKEN_BLOCK"
        self.token_type, self.contents = token_type, contents

    def __str__(self):
        return '<%s token: "%s...">' % (
            {TOKEN_TEXT:'Text', TOKEN_VAR:'Var', TOKEN_BLOCK:'Block'}[self.token_type],
            self.contents[:20].replace('\n', '')
            )

def tokenize(template_string):
    "Return a list of tokens from a given template_string"
    # remove all empty strings, because the regex has a tendency to add them
    bits = filter(None, tag_re.split(template_string))
    return map(create_token, bits)

def create_token(token_string):
    "Convert the given token string into a new Token object and return it"
    if token_string.startswith(VARIABLE_TAG_START):
        return Token(TOKEN_VAR, token_string[len(VARIABLE_TAG_START):-len(VARIABLE_TAG_END)].strip())
    elif token_string.startswith(BLOCK_TAG_START):
        return Token(TOKEN_BLOCK, token_string[len(BLOCK_TAG_START):-len(BLOCK_TAG_END)].strip())
    else:
        return Token(TOKEN_TEXT, token_string)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens

    def parse(self, parse_until=[]):
        nodelist = NodeList()
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_TEXT:
                nodelist.append(TextNode(token.contents))
            elif token.token_type == TOKEN_VAR:
                if not token.contents:
                    raise TemplateSyntaxError, "Empty variable tag"
                nodelist.append(VariableNode(token.contents))
            elif token.token_type == TOKEN_BLOCK:
                if token.contents in parse_until:
                    # put token back on token list so calling code knows why it terminated
                    self.prepend_token(token)
                    return nodelist
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    raise TemplateSyntaxError, "Empty block tag"
                try:
                    # execute callback function for this tag and append resulting node
                    nodelist.append(registered_tags[command](self, token))
                except KeyError:
                    raise TemplateSyntaxError, "Invalid block tag: '%s'" % command
        if parse_until:
            raise TemplateSyntaxError, "Unclosed tag(s): '%s'" % ', '.join(parse_until)
        return nodelist

    def next_token(self):
        return self.tokens.pop(0)

    def prepend_token(self, token):
        self.tokens.insert(0, token)

    def delete_first_token(self):
        del self.tokens[0]

class FilterParser:
    """Parse a variable token and its optional filters (all as a single string),
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
    def __init__(self, s):
        self.s = s
        self.i = -1
        self.current = ''
        self.filters = []
        self.current_filter_name = None
        self.current_filter_arg = None
        # First read the variable part - decide on wether we need
        # to parse a string or a variable by peeking into the stream
        if self.peek_char() in ('_', '"', "'"):
            self.var = self.read_constant_string_token()
        else:
            self.var = self.read_alphanumeric_token()
        if not self.var:
            raise TemplateSyntaxError, "Could not read variable name: '%s'" % self.s
        if self.var.find(VARIABLE_ATTRIBUTE_SEPARATOR + '_') > -1 or (self.var[0] == '_' and not self.var.startswith('_(')):
            raise TemplateSyntaxError, "Variables and attributes may not begin with underscores: '%s'" % self.var
        # Have we reached the end?
        if self.current is None:
            return
        if self.current != FILTER_SEPARATOR:
            raise TemplateSyntaxError, "Bad character (expecting '%s') '%s'" % (FILTER_SEPARATOR, self.current)
        # We have a filter separator; start reading the filters
        self.read_filters()

    def peek_char(self):
        try:
            return self.s[self.i+1]
        except IndexError:
            return None

    def next_char(self):
        self.i = self.i + 1
        try:
            self.current = self.s[self.i]
        except IndexError:
            self.current = None

    def read_constant_string_token(self):
        """Read a constant string that must be delimited by either "
        or ' characters. The string is returned with it's delimiters
        and a possible i18n tag."""
        val = ''
        i18n = False
        qchar = None
        self.next_char()
        if self.current == '_':
            self.next_char()
            if self.current != '(':
                raise TemplateSyntaxError, "Bad character (expecting '(') '%s'" % self.current
            i18n = True
            val = '_('
            self.next_char()
        if not self.current in ('"', "'"):
            raise TemplateSyntaxError, "Bad character (expecting '\"' or ''') '%s'" % self.current
        qchar = self.current
        val += qchar
        while 1:
           self.next_char()
           if self.current == qchar:
               break
           val += self.current
        val += self.current
        if i18n:
           self.next_char()
           if self.current != ')':
                raise TemplateSyntaxError, "Bad character (expecting ')') '%s'" % self.current
           val += self.current
        self.next_char()
        return val

    def read_alphanumeric_token(self):
        """Read a variable name or filter name, which are continuous strings of
        alphanumeric characters + the underscore"""
        var = ''
        while 1:
            self.next_char()
            if self.current is None:
                break
            if self.current not in ALLOWED_VARIABLE_CHARS:
                break
            var += self.current
        return var

    def read_filters(self):
        while 1:
            filter_name, arg = self.read_filter()
            if not registered_filters.has_key(filter_name):
                raise TemplateSyntaxError, "Invalid filter: '%s'" % filter_name
            if registered_filters[filter_name][1] == True and arg is None:
                raise TemplateSyntaxError, "Filter '%s' requires an argument" % filter_name
            if registered_filters[filter_name][1] == False and arg is not None:
                raise TemplateSyntaxError, "Filter '%s' should not have an argument (argument is %r)" % (filter_name, arg)
            self.filters.append((filter_name, arg))
            if self.current is None:
                break

    def read_filter(self):
        self.current_filter_name = self.read_alphanumeric_token()
        self.current_filter_arg = None
        # Have we reached the end?
        if self.current is None:
            return (self.current_filter_name, None)
        # Does the filter have an argument?
        if self.current == FILTER_ARGUMENT_SEPARATOR:
            self.current_filter_arg = self.read_arg()
            return (self.current_filter_name, self.current_filter_arg)
        # Next thing MUST be a pipe
        if self.current != FILTER_SEPARATOR:
            raise TemplateSyntaxError, "Bad character (expecting '%s') '%s'" % (FILTER_SEPARATOR, self.current)
        return (self.current_filter_name, self.current_filter_arg)

    def read_arg(self):
        # First read a " or a _("
        self.next_char()
        translated = False
        if self.current == '_':
            self.next_char()
            if self.current != '(':
                raise TemplateSyntaxError, "Bad character (expecting '(') '%s'" % self.current
            translated = True
            self.next_char()
        if self.current != '"':
            raise TemplateSyntaxError, "Bad character (expecting '\"') '%s'" % self.current
        self.escaped = False
        arg = ''
        while 1:
            self.next_char()
            if self.current == '"' and not self.escaped:
                break
            if self.current == '\\' and not self.escaped:
                self.escaped = True
                continue
            if self.current == '\\' and self.escaped:
                arg += '\\'
                self.escaped = False
                continue
            if self.current == '"' and self.escaped:
                arg += '"'
                self.escaped = False
                continue
            if self.escaped and self.current not in '\\"':
                raise TemplateSyntaxError, "Unescaped backslash in '%s'" % self.s
            if self.current is None:
                raise TemplateSyntaxError, "Unexpected end of argument in '%s'" % self.s
            arg += self.current
        # self.current must now be '"'
        self.next_char()
        if translated:
            if self.current != ')':
                raise TemplateSyntaxError, "Bad character (expecting ')') '%s'" % self.current
            self.next_char()
            arg = _(arg)
        return arg

def get_filters_from_token(token):
    "Convenient wrapper for FilterParser"
    p = FilterParser(token)
    return (p.var, p.filters)

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
    if path[0]  in ('"', "'") and path[0] == path[-1]:
        current = path[1:-1]
    elif path.startswith('_(') and path.endswith(')') and path[2] in ("'", '"') and path[-2] == path[2]:
        current = _(path[3:-2]) % context
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
                            current = ''
                        else:
                            try: # method call (assuming no args required)
                                current = current()
                            except SilentVariableFailure:
                                current = ''
                            except TypeError: # arguments *were* required
                                current = '' # invalid method call
                except (TypeError, AttributeError):
                    try: # list-index lookup
                        current = current[int(bits[0])]
                    except (IndexError, ValueError, KeyError):
                        raise VariableDoesNotExist, "Failed lookup for key [%s] in %r" % (bits[0], current) # missing attribute
            del bits[0]
    return current

def resolve_variable_with_filters(var_string, context):
    """
    var_string is a full variable expression with optional filters, like:
        a.b.c|lower|date:"y/m/d"
    This function resolves the variable in the context, applies all filters and
    returns the object.
    """
    var, filters = get_filters_from_token(var_string)
    try:
        obj = resolve_variable(var, context)
    except VariableDoesNotExist:
        obj = ''
    for name, arg in filters:
        obj = registered_filters[name][0](obj, arg)
    return obj

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
                bits.append(node.render(context))
            else:
                bits.append(node)
        return ''.join(bits)

    def get_nodes_by_type(self, nodetype):
        "Return a list of all nodes of the given type"
        nodes = []
        for node in self:
            nodes.extend(node.get_nodes_by_type(nodetype))
        return nodes

class TextNode(Node):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "<Text Node: '%s'>" % self.s[:25]

    def render(self, context):
        return self.s

class VariableNode(Node):
    def __init__(self, var_string):
        self.var_string = var_string

    def __repr__(self):
        return "<Variable Node: %s>" % self.var_string

    def render(self, context):
        output = resolve_variable_with_filters(self.var_string, context)
        # Check type so that we don't run str() on a Unicode object
        if not isinstance(output, basestring):
            output = str(output)
        elif isinstance(output, unicode):
            output = output.encode(DEFAULT_CHARSET)
        return output

def register_tag(token_command, callback_function):
    registered_tags[token_command] = callback_function

def unregister_tag(token_command):
    del registered_tags[token_command]

def register_filter(filter_name, callback_function, has_arg):
    registered_filters[filter_name] = (callback_function, has_arg)

def unregister_filter(filter_name):
    del registered_filters[filter_name]

import defaulttags
import defaultfilters
