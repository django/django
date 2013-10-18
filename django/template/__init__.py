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

>>> from django import template
>>> s = u'<html>{% if test %}<h1>{{ varvalue }}</h1>{% endif %}</html>'
>>> t = template.Template(s)

(t is now a compiled template, and its render() method can be called multiple
times with multiple contexts)

>>> c = template.Context({'test':True, 'varvalue': 'Hello'})
>>> t.render(c)
u'<html><h1>Hello</h1></html>'
>>> c = template.Context({'test':False, 'varvalue': 'Hello'})
>>> t.render(c)
u'<html></html>'
"""

# Template lexing symbols
from django.template.base import (ALLOWED_VARIABLE_CHARS, BLOCK_TAG_END,  # NOQA
    BLOCK_TAG_START, COMMENT_TAG_END, COMMENT_TAG_START,
    FILTER_ARGUMENT_SEPARATOR, FILTER_SEPARATOR, SINGLE_BRACE_END,
    SINGLE_BRACE_START, TOKEN_BLOCK, TOKEN_COMMENT, TOKEN_TEXT, TOKEN_VAR,
    TRANSLATOR_COMMENT_MARK, UNKNOWN_SOURCE, VARIABLE_ATTRIBUTE_SEPARATOR,
    VARIABLE_TAG_END, VARIABLE_TAG_START, filter_re, tag_re)

# Exceptions
from django.template.base import (ContextPopException, InvalidTemplateLibrary,  # NOQA
    TemplateDoesNotExist, TemplateEncodingError, TemplateSyntaxError,
    VariableDoesNotExist)

# Template parts
from django.template.base import (Context, FilterExpression, Lexer, Node,  # NOQA
    NodeList, Parser, RequestContext, Origin, StringOrigin, Template,
    TextNode, Token, TokenParser, Variable, VariableNode, constant_string,
    filter_raw_string)

# Compiling templates
from django.template.base import (compile_string, resolve_variable,  # NOQA
    unescape_string_literal, generic_tag_compiler)

# Library management
from django.template.base import (Library, add_to_builtins, builtins,  # NOQA
    get_library, get_templatetags_modules, get_text_list, import_library,
    libraries)

__all__ = ('Template', 'Context', 'RequestContext', 'compile_string')
