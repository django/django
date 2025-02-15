"""
Thibaud's support for templates.

The thibaud.template namespace contains two independent subsystems:

1. Multiple Template Engines: support for pluggable template backends,
   built-in backends and backend-independent APIs
2. Thibaud Template Language: Thibaud's own template engine, including its
   built-in loaders, context processors, tags and filters.

Ideally these subsystems would be implemented in distinct packages. However
keeping them together made the implementation of Multiple Template Engines
less disruptive .

Here's a breakdown of which modules belong to which subsystem.

Multiple Template Engines:

- thibaud.template.backends.*
- thibaud.template.loader
- thibaud.template.response

Thibaud Template Language:

- thibaud.template.base
- thibaud.template.context
- thibaud.template.context_processors
- thibaud.template.loaders.*
- thibaud.template.debug
- thibaud.template.defaultfilters
- thibaud.template.defaulttags
- thibaud.template.engine
- thibaud.template.loader_tags
- thibaud.template.smartif

Shared:

- thibaud.template.utils

"""

# Multiple Template Engines

from .engine import Engine
from .utils import EngineHandler

engines = EngineHandler()

__all__ = ("Engine", "engines")


# Thibaud Template Language

# Public exceptions
from .base import VariableDoesNotExist  # NOQA isort:skip
from .context import Context, ContextPopException, RequestContext  # NOQA isort:skip
from .exceptions import TemplateDoesNotExist, TemplateSyntaxError  # NOQA isort:skip

# Template parts
from .base import (  # NOQA isort:skip
    Node,
    NodeList,
    Origin,
    Template,
    Variable,
)

# Library management
from .library import Library  # NOQA isort:skip

# Import the .autoreload module to trigger the registrations of signals.
from . import autoreload  # NOQA isort:skip


__all__ += ("Template", "Context", "RequestContext")
