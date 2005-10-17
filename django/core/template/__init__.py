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
from django.conf.settings import DEFAULT_CHARSET, DEBUG

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

#What to report as the origin of templates that come from non file sources (eg strings)
UNKNOWN_SOURCE="<unknown source>"

#match starts of lines
newline_re = re.compile("^", re.M);

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
    def __init__(self, template_string, filename=UNKNOWN_SOURCE):
        "Compilation stage"
        self.nodelist = compile_string(template_string, filename)
       
    def __iter__(self):
        for node in self.nodelist:
            for subnode in node:
                yield subnode

    def render(self, context):
        "Display stage -- can be called many times"
        return self.nodelist.render(context)

def compile_string(template_string, filename):
    "Compiles template_string into NodeList ready for rendering"
    if DEBUG:
        lexer_factory = DebugLexer
        parser_factory = DebugParser
    else:
        lexer_factory = Lexer
        parser_factory = Parser
        
    lexer = lexer_factory(template_string, filename)
    parser = parser_factory(lexer.tokenize())
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
            
    def __repr__(self):
        return '<%s token: "%s">' % (
            {TOKEN_TEXT:'Text', TOKEN_VAR:'Var', TOKEN_BLOCK:'Block'}[self.token_type],
            self.contents[:].replace('\n', '')
            )

class Lexer(object):
    def __init__(self, template_string, filename):
        self.template_string = template_string
        self.filename = filename
    
    def tokenize(self):
        "Return a list of tokens from a given template_string"
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
    def __init__(self, template_string, filename):
        super(DebugLexer,self).__init__(template_string, filename)

    def find_linebreaks(self, template_string):
        for match in newline_re.finditer(template_string):
            yield match.start()
        yield len(template_string) + 1

    def tokenize(self):
        "Return a list of tokens from a given template_string"
        token_tups, upto = [], 0
        lines = enumerate(self.find_linebreaks(self.template_string))
        line, next_linebreak = lines.next()
        for match in tag_re.finditer(self.template_string):
            while next_linebreak <= upto:
                line, next_linebreak = lines.next()    
            start, end = match.span()
            if start > upto:       
                token_tups.append( (self.template_string[upto:start], line) )
                upto = start
                while next_linebreak <= upto:
                    line, next_linebreak = lines.next()              
            token_tups.append( (self.template_string[start:end], line) )
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
           token_tups.append( (last_bit, line) )
        return [ self.create_token(tok, (self.filename, line)) for tok, line in token_tups]

    def create_token(self, token_string, source):
        token = super(DebugLexer, self).create_token(token_string)
        token.source = source
        return token

class Parser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        

    def parse(self, parse_until=[]):
        nodelist = NodeList()
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_TEXT:
                self.extend_nodelist(nodelist, TextNode(token.contents), token)
            elif token.token_type == TOKEN_VAR:
                if not token.contents:
                    self.empty_variable(token)
                self.extend_nodelist(nodelist, VariableNode(token.contents), token)
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
                self.enter_command(command, token);
                try:
                    compile_func = registered_tags[command]
                except KeyError:
                    self.invalid_block_tag(token, command)
                    
                self.extend_nodelist(nodelist, compile_func(self, token), token)
                self.exit_command();
                
        if parse_until:
            self.unclosed_block_tag(token, parse_until)
            
        return nodelist

    def extend_nodelist(self, nodelist, node, token):
        nodelist.append(node)

    def enter_command(self, command, token):
        pass
        
    def exit_command(self):
        pass

    def empty_variable(self, token):
        raise TemplateSyntaxError, "Empty variable tag" 
    
    def empty_block_tag(self, token):
        raise TemplateSyntaxError, "Empty block tag"
    
    def invalid_block_tag(self, token, command):
        raise TemplateSyntaxError, "Invalid block tag: %s" % (command)
    
    def unclosed_block_tag(self, token, parse_until):
        raise TemplateSyntaxError, "Unclosed tags: %s " %  ', '.join(parse_until)
        
    def next_token(self):
        return self.tokens.pop(0)

    def prepend_token(self, token):
        self.tokens.insert(0, token)

    def delete_first_token(self):
        del self.tokens[0]


class DebugParser(Parser):
    def __init__(self, lexer):
        super(DebugParser, self).__init__(lexer)
        self.command_stack = []

    def enter_command(self, command, token):
        self.command_stack.append( (command, token.source) )
        
    def exit_command(self):
        self.command_stack.pop()

    def format_source(self, source):
        return "at %s, line %d" % source

    def extend_nodelist(self, nodelist, node, token):
        node.source = token.source
        super(DebugParser, self).extend_nodelist(nodelist, node, token)

    def empty_variable(self, token):
        raise TemplateSyntaxError, "Empty variable tag %s" % self.format_source(token.source)
    
    def empty_block_tag(self, token):
        raise TemplateSyntaxError, "Empty block tag %s" % self.format_source(token.source)
    
    def invalid_block_tag(self, token, command):
        raise TemplateSyntaxError, "Invalid block tag: '%s' %s" % (command, self.format_source(token.source))
    
    def unclosed_block_tag(self, token, parse_until):
        (command, (file,line)) = self.command_stack.pop()
        msg = "Unclosed tag '%s' starting at %s, line %d. Looking for one of: %s " % \
              (command, file, line, ', '.join(parse_until) ) 
        raise TemplateSyntaxError, msg

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
        # First read the variable part
        self.var = self.read_alphanumeric_token()
        if not self.var:
            raise TemplateSyntaxError, "Could not read variable name: '%s'" % self.s
        if self.var.find(VARIABLE_ATTRIBUTE_SEPARATOR + '_') > -1 or self.var[0] == '_':
            raise TemplateSyntaxError, "Variables and attributes may not begin with underscores: '%s'" % self.var
        # Have we reached the end?
        if self.current is None:
            return
        if self.current != FILTER_SEPARATOR:
            raise TemplateSyntaxError, "Bad character (expecting '%s') '%s'" % (FILTER_SEPARATOR, self.current)
        # We have a filter separator; start reading the filters
        self.read_filters()

    def next_char(self):
        self.i = self.i + 1
        try:
            self.current = self.s[self.i]
        except IndexError:
            self.current = None

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
        # First read a "
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
    if path[0] in ('"', "'") and path[0] == path[-1]:
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
