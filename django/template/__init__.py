"""
Django's support for templates.

The django.template namespace contains two independent subsystems:

1. Multiple Template Engines: support for pluggable template backends,
   built-in backends and backend-independent APIs
2. Django Template Language: Django's own template engine, including its
   built-in loaders, context processors, tags and filters.

Ideally these subsystems would be implemented in distinct packages. However
keeping them together made the implementation of Multiple Template Engines
less disruptive .

Here's a breakdown of which modules belong to which subsystem.

Multiple Template Engines:

- django.template.backends.*
- django.template.loader
- django.template.response

Django Template Language:

- django.template.base
- django.template.context
- django.template.context_processors
- django.template.loaders.*
- django.template.debug
- django.template.defaultfilters
- django.template.defaulttags
- django.template.engine
- django.template.loader_tags
- django.template.smartif

Shared:

- django.template.utils

"""

from .base import (
    FilterExpression,
    Lexer,
    Node,
    NodeList,
    Origin,
    Parser,
    PartialTemplate,
    Template,
    Token,
    TokenType,
    Variable,
    VariableDoesNotExist,
)
from .context import Context, ContextPopException, RenderContext, RequestContext
from .engine import Engine
from .exceptions import TemplateDoesNotExist, TemplateSyntaxError
from .library import Library
from .utils import EngineHandler, InvalidTemplateEngineError

engines = EngineHandler()

# Import the .autoreload module to trigger the registrations of signals.
from . import autoreload  # noqa: F401 E402 isort:skip

__all__ = (
    "Context",
    "ContextPopException",
    "Engine",
    "EngineHandler",
    "FilterExpression",
    "InvalidTemplateEngineError",
    "Lexer",
    "Library",
    "Node",
    "NodeList",
    "Origin",
    "Parser",
    "PartialTemplate",
    "RenderContext",
    "RequestContext",
    "Template",
    "TemplateDoesNotExist",
    "TemplateSyntaxError",
    "Token",
    "TokenType",
    "Variable",
    "VariableDoesNotExist",
    "engines",
)
