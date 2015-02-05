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

# Multiple Template Engines

from .engine import Engine

from .utils import EngineHandler


engines = EngineHandler()

__all__ = ('Engine', 'engines')


# Django Template Language

# Public exceptions
from .base import (TemplateDoesNotExist, TemplateSyntaxError,           # NOQA
                   VariableDoesNotExist)
from .context import ContextPopException                                # NOQA

# Template parts
from .base import (Context, Node, NodeList, RequestContext,             # NOQA
                   StringOrigin, Template, Variable)

# Deprecated in Django 1.8, will be removed in Django 2.0.
from .base import resolve_variable                                      # NOQA

# Library management
from .base import Library                                               # NOQA


__all__ += ('Template', 'Context', 'RequestContext')
