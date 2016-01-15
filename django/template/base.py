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
the variable's value as a string. The render() method of a ForNode returns the
rendered output of whatever was inside the loop, recursively.

The Template class is a convenient wrapper that takes care of template
compilation and rendering.

Usage:

The only thing you should ever use directly in this file is the Template class.
Create a compiled template object with a template_string, then call render()
with a context. In the compilation stage, the TemplateSyntaxError exception
will be raised if the template doesn't have proper syntax.

Sample code:

>>> from django import template
>>> s = '<html>{% if test %}<h1>{{ varvalue }}</h1>{% endif %}</html>'
>>> t = template.Template(s)

(t is now a compiled template, and its render() method can be called multiple
times with multiple contexts)

>>> c = template.Context({'test':True, 'varvalue': 'Hello'})
>>> t.render(c)
'<html><h1>Hello</h1></html>'
>>> c = template.Context({'test':False, 'varvalue': 'Hello'})
>>> t.render(c)
'<html></html>'
"""

from __future__ import unicode_literals

import inspect
import logging
import re
import warnings

from django.template.context import (  # NOQA: imported for backwards compatibility
    BaseContext, Context, ContextPopException, RequestContext,
)
from django.utils import six
from django.utils.deprecation import (
    DeprecationInstanceCheck, RemovedInDjango20Warning,
    RemovedInDjango110Warning,
)
from django.utils.encoding import (
    force_str, force_text, python_2_unicode_compatible,
)
from django.utils.formats import localize
from django.utils.html import conditional_escape, escape
from django.utils.inspect import getargspec
from django.utils.safestring import (
    EscapeData, SafeData, mark_for_escaping, mark_safe,
)
from django.utils.text import (
    get_text_list, smart_split, unescape_string_literal,
)
from django.utils.timezone import template_localtime
from django.utils.translation import pgettext_lazy, ugettext_lazy

from .exceptions import TemplateSyntaxError

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

# what to report as the origin for templates that come from non-loader sources
# (e.g. strings)
UNKNOWN_SOURCE = '<unknown source>'

# match a variable or block tag and capture the entire tag, including start/end
# delimiters
tag_re = (re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' %
          (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
           re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END),
           re.escape(COMMENT_TAG_START), re.escape(COMMENT_TAG_END))))

logger = logging.getLogger('django.template')


class TemplateEncodingError(Exception):
    pass


@python_2_unicode_compatible
class VariableDoesNotExist(Exception):

    def __init__(self, msg, params=()):
        self.msg = msg
        self.params = params

    def __str__(self):
        return self.msg % tuple(force_text(p, errors='replace') for p in self.params)


class Origin(object):
    def __init__(self, name, template_name=None, loader=None):
        self.name = name
        self.template_name = template_name
        self.loader = loader

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, Origin):
            return False

        return (
            self.name == other.name and
            self.loader == other.loader
        )

    @property
    def loader_name(self):
        if self.loader:
            return '%s.%s' % (
                self.loader.__module__, self.loader.__class__.__name__,
            )


class StringOrigin(six.with_metaclass(DeprecationInstanceCheck, Origin)):
    alternative = 'django.template.Origin'
    deprecation_warning = RemovedInDjango20Warning


class Template(object):
    def __init__(self, template_string, origin=None, name=None, engine=None):
        try:
            template_string = force_text(template_string)
        except UnicodeDecodeError:
            raise TemplateEncodingError("Templates can only be constructed "
                                        "from unicode or UTF-8 strings.")
        # If Template is instantiated directly rather than from an Engine and
        # exactly one Django template engine is configured, use that engine.
        # This is required to preserve backwards-compatibility for direct use
        # e.g. Template('...').render(Context({...}))
        if engine is None:
            from .engine import Engine
            engine = Engine.get_default()
        if origin is None:
            origin = Origin(UNKNOWN_SOURCE)
        self.name = name
        self.origin = origin
        self.engine = engine
        self.source = template_string
        self.nodelist = self.compile_nodelist()

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
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    return self._render(context)
            else:
                return self._render(context)
        finally:
            context.render_context.pop()

    def compile_nodelist(self):
        """
        Parse and compile the template source into a nodelist. If debug
        is True and an exception occurs during parsing, the exception is
        is annotated with contextual line information where it occurred in the
        template source.
        """
        if self.engine.debug:
            lexer = DebugLexer(self.source)
        else:
            lexer = Lexer(self.source)

        tokens = lexer.tokenize()
        parser = Parser(
            tokens, self.engine.template_libraries, self.engine.template_builtins,
            self.origin,
        )

        try:
            return parser.parse()
        except Exception as e:
            if self.engine.debug:
                e.template_debug = self.get_exception_info(e, e.token)
            raise

    def get_exception_info(self, exception, token):
        """
        Return a dictionary containing contextual line information of where
        the exception occurred in the template. The following information is
        provided:

        message
            The message of the exception raised.

        source_lines
            The lines before, after, and including the line the exception
            occurred on.

        line
            The line number the exception occurred on.

        before, during, after
            The line the exception occurred on split into three parts:
            1. The content before the token that raised the error.
            2. The token that raised the error.
            3. The content after the token that raised the error.

        total
            The number of lines in source_lines.

        top
            The line number where source_lines starts.

        bottom
            The line number where source_lines ends.

        start
            The start position of the token in the template source.

        end
            The end position of the token in the template source.
        """
        start, end = token.position
        context_lines = 10
        line = 0
        upto = 0
        source_lines = []
        before = during = after = ""
        for num, next in enumerate(linebreak_iter(self.source)):
            if start >= upto and end <= next:
                line = num
                before = escape(self.source[upto:start])
                during = escape(self.source[start:end])
                after = escape(self.source[end:next])
            source_lines.append((num, escape(self.source[upto:next])))
            upto = next
        total = len(source_lines)

        top = max(1, line - context_lines)
        bottom = min(total, line + 1 + context_lines)

        # In some rare cases exc_value.args can be empty or an invalid
        # unicode string.
        try:
            message = force_text(exception.args[0])
        except (IndexError, UnicodeDecodeError):
            message = '(Could not get exception message)'

        return {
            'message': message,
            'source_lines': source_lines[top:bottom],
            'before': before,
            'during': during,
            'after': after,
            'top': top,
            'bottom': bottom,
            'total': total,
            'line': line,
            'name': self.origin.name,
            'start': start,
            'end': end,
        }


def linebreak_iter(template_source):
    yield 0
    p = template_source.find('\n')
    while p >= 0:
        yield p + 1
        p = template_source.find('\n', p + 1)
    yield len(template_source) + 1


class Token(object):
    def __init__(self, token_type, contents, position=None, lineno=None):
        """
        A token representing a string from the template.

        token_type
            One of TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, or TOKEN_COMMENT.

        contents
            The token source string.

        position
            An optional tuple containing the start and end index of the token
            in the template source. This is used for traceback information
            when debug is on.

        lineno
            The line number the token appears on in the template source.
            This is used for traceback information and gettext files.
        """
        self.token_type, self.contents = token_type, contents
        self.lineno = lineno
        self.position = position

    def __str__(self):
        token_name = TOKEN_MAPPING[self.token_type]
        return ('<%s token: "%s...">' %
                (token_name, self.contents[:20].replace('\n', '')))

    def split_contents(self):
        split = []
        bits = iter(smart_split(self.contents))
        for bit in bits:
            # Handle translation-marked template pieces
            if bit.startswith(('_("', "_('")):
                sentinel = bit[2] + ')'
                trans_bit = [bit]
                while not bit.endswith(sentinel):
                    bit = next(bits)
                    trans_bit.append(bit)
                bit = ' '.join(trans_bit)
            split.append(bit)
        return split


class Lexer(object):
    def __init__(self, template_string):
        self.template_string = template_string
        self.verbatim = False

    def tokenize(self):
        """
        Return a list of tokens from a given template_string.
        """
        in_tag = False
        lineno = 1
        result = []
        for bit in tag_re.split(self.template_string):
            if bit:
                result.append(self.create_token(bit, None, lineno, in_tag))
            in_tag = not in_tag
            lineno += bit.count('\n')
        return result

    def create_token(self, token_string, position, lineno, in_tag):
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
                token = Token(TOKEN_VAR, token_string[2:-2].strip(), position, lineno)
            elif token_string.startswith(BLOCK_TAG_START):
                if block_content[:9] in ('verbatim', 'verbatim '):
                    self.verbatim = 'end%s' % block_content
                token = Token(TOKEN_BLOCK, block_content, position, lineno)
            elif token_string.startswith(COMMENT_TAG_START):
                content = ''
                if token_string.find(TRANSLATOR_COMMENT_MARK):
                    content = token_string[2:-2].strip()
                token = Token(TOKEN_COMMENT, content, position, lineno)
        else:
            token = Token(TOKEN_TEXT, token_string, position, lineno)
        return token


class DebugLexer(Lexer):
    def tokenize(self):
        """
        Split a template string into tokens and annotates each token with its
        start and end position in the source. This is slower than the default
        lexer so we only use it when debug is True.
        """
        lineno = 1
        result = []
        upto = 0
        for match in tag_re.finditer(self.template_string):
            start, end = match.span()
            if start > upto:
                token_string = self.template_string[upto:start]
                result.append(self.create_token(token_string, (upto, start), lineno, in_tag=False))
                lineno += token_string.count('\n')
                upto = start
            token_string = self.template_string[start:end]
            result.append(self.create_token(token_string, (start, end), lineno, in_tag=True))
            lineno += token_string.count('\n')
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
            result.append(self.create_token(last_bit, (upto, upto + len(last_bit)), lineno, in_tag=False))
        return result


class Parser(object):
    def __init__(self, tokens, libraries=None, builtins=None, origin=None):
        self.tokens = tokens
        self.tags = {}
        self.filters = {}
        self.command_stack = []

        if libraries is None:
            libraries = {}
        if builtins is None:
            builtins = []

        self.libraries = libraries
        for builtin in builtins:
            self.add_library(builtin)
        self.origin = origin

    def parse(self, parse_until=None):
        """
        Iterate through the parser tokens and compiles each one into a node.

        If parse_until is provided, parsing will stop once one of the
        specified tokens has been reached. This is formatted as a list of
        tokens, e.g. ['elif', 'else', 'endif']. If no matching token is
        reached, raise an exception with the unclosed block tag details.
        """
        if parse_until is None:
            parse_until = []
        nodelist = NodeList()
        while self.tokens:
            token = self.next_token()
            # Use the raw values here for TOKEN_* for a tiny performance boost.
            if token.token_type == 0:  # TOKEN_TEXT
                self.extend_nodelist(nodelist, TextNode(token.contents), token)
            elif token.token_type == 1:  # TOKEN_VAR
                if not token.contents:
                    raise self.error(token, 'Empty variable tag on line %d' % token.lineno)
                try:
                    filter_expression = self.compile_filter(token.contents)
                except TemplateSyntaxError as e:
                    raise self.error(token, e)
                var_node = VariableNode(filter_expression)
                self.extend_nodelist(nodelist, var_node, token)
            elif token.token_type == 2:  # TOKEN_BLOCK
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    raise self.error(token, 'Empty block tag on line %d' % token.lineno)
                if command in parse_until:
                    # A matching token has been reached. Return control to
                    # the caller. Put the token back on the token list so the
                    # caller knows where it terminated.
                    self.prepend_token(token)
                    return nodelist
                # Add the token to the command stack. This is used for error
                # messages if further parsing fails due to an unclosed block
                # tag.
                self.command_stack.append((command, token))
                # Get the tag callback function from the ones registered with
                # the parser.
                try:
                    compile_func = self.tags[command]
                except KeyError:
                    self.invalid_block_tag(token, command, parse_until)
                # Compile the callback into a node object and add it to
                # the node list.
                try:
                    compiled_result = compile_func(self, token)
                except Exception as e:
                    raise self.error(token, e)
                self.extend_nodelist(nodelist, compiled_result, token)
                # Compile success. Remove the token from the command stack.
                self.command_stack.pop()
        if parse_until:
            self.unclosed_block_tag(parse_until)
        return nodelist

    def skip_past(self, endtag):
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_BLOCK and token.contents == endtag:
                return
        self.unclosed_block_tag([endtag])

    def extend_nodelist(self, nodelist, node, token):
        # Check that non-text nodes don't appear before an extends tag.
        if node.must_be_first and nodelist.contains_nontext:
            raise self.error(
                token, '%r must be the first tag in the template.' % node,
            )
        if isinstance(nodelist, NodeList) and not isinstance(node, TextNode):
            nodelist.contains_nontext = True
        # Set origin and token here since we can't modify the node __init__()
        # method.
        node.token = token
        node.origin = self.origin
        nodelist.append(node)

    def error(self, token, e):
        """
        Return an exception annotated with the originating token. Since the
        parser can be called recursively, check if a token is already set. This
        ensures the innermost token is highlighted if an exception occurs,
        e.g. a compile error within the body of an if statement.
        """
        if not isinstance(e, Exception):
            e = TemplateSyntaxError(e)
        if not hasattr(e, 'token'):
            e.token = token
        return e

    def invalid_block_tag(self, token, command, parse_until=None):
        if parse_until:
            raise self.error(
                token,
                "Invalid block tag on line %d: '%s', expected %s. Did you "
                "forget to register or load this tag?" % (
                    token.lineno,
                    command,
                    get_text_list(["'%s'" % p for p in parse_until]),
                ),
            )
        raise self.error(
            token,
            "Invalid block tag on line %d: '%s'. Did you forget to register "
            "or load this tag?" % (token.lineno, command)
        )

    def unclosed_block_tag(self, parse_until):
        command, token = self.command_stack.pop()
        msg = "Unclosed tag on line %d: '%s'. Looking for one of: %s." % (
            token.lineno,
            command,
            ', '.join(parse_until),
        )
        raise self.error(token, msg)

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
                    string_if_invalid = context.template.engine.string_if_invalid
                    if string_if_invalid:
                        if '%s' in string_if_invalid:
                            return string_if_invalid % self.var
                        else:
                            return string_if_invalid
                    else:
                        obj = string_if_invalid
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

        args, _, _, defaults = getargspec(func)
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
    warnings.warn("resolve_variable() is deprecated. Use django.template."
                  "Variable(path).resolve(context) instead",
                  RemovedInDjango110Warning, stacklevel=2)
    return Variable(path).resolve(context)


class Variable(object):
    """
    A template variable, resolvable against a given context. The variable may
    be a hard-coded string (if it begins and ends with single or double quote
    marks)::

        >>> c = {'article': {'section':'News'}}
        >>> Variable('article.section').resolve(c)
        'News'
        >>> Variable('article').resolve(c)
        {'section': 'News'}
        >>> class AClass: pass
        >>> c = AClass()
        >>> c.article = AClass()
        >>> c.article.section = 'News'

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
            is_safe = isinstance(value, SafeData)
            msgid = value.replace('%', '%%')
            msgid = mark_safe(msgid) if is_safe else msgid
            if self.message_context:
                return pgettext_lazy(self.message_context, msgid)
            else:
                return ugettext_lazy(msgid)
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
                    # ValueError/IndexError are for numpy.array lookup on
                    # numpy < 1.9 and 1.9+ respectively
                except (TypeError, AttributeError, KeyError, ValueError, IndexError):
                    try:  # attribute lookup
                        # Don't return class attributes if the class is the context:
                        if isinstance(current, BaseContext) and getattr(type(current), bit):
                            raise AttributeError
                        current = getattr(current, bit)
                    except (TypeError, AttributeError) as e:
                        # Reraise an AttributeError raised by a @property
                        if (isinstance(e, AttributeError) and
                                not isinstance(current, BaseContext) and bit in dir(current)):
                            raise
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
                        current = context.template.engine.string_if_invalid
                    else:
                        try:  # method call (assuming no args required)
                            current = current()
                        except TypeError:
                            try:
                                inspect.getcallargs(current)
                            except TypeError:  # arguments *were* required
                                current = context.template.engine.string_if_invalid  # invalid method call
                            else:
                                raise
        except Exception as e:
            template_name = getattr(context, 'template_name', None) or 'unknown'
            logger.debug(
                "Exception while resolving variable '%s' in template '%s'.",
                bit,
                template_name,
                exc_info=True,
            )

            if getattr(e, 'silent_variable_failure', False):
                current = context.template.engine.string_if_invalid
            else:
                raise

        return current


class Node(object):
    # Set this to True for nodes that must be first in the template (although
    # they can be preceded by text nodes.
    must_be_first = False
    child_nodelists = ('nodelist',)
    token = None

    def render(self, context):
        """
        Return the node rendered as a string.
        """
        pass

    def render_annotated(self, context):
        """
        Render the node. If debug is True and an exception occurs during
        rendering, the exception is annotated with contextual line information
        where it occurred in the template. For internal usage this method is
        preferred over using the render method directly.
        """
        try:
            return self.render(context)
        except Exception as e:
            if context.template.engine.debug and not hasattr(e, 'template_debug'):
                e.template_debug = context.template.get_exception_info(e, self.token)
            raise

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
                bit = node.render_annotated(context)
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


class TextNode(Node):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        rep = "<%s: %r>" % (self.__class__.__name__, self.s[:25])
        return force_str(rep, 'ascii', errors='replace')

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
