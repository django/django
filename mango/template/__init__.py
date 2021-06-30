"""
Mango's support for templates.

The mango.template namespace contains two independent subsystems:

1. Multiple Template Engines: support for pluggable template backends,
   built-in backends and backend-independent APIs
2. Mango Template Language: Mango's own template engine, including its
   built-in loaders, context processors, tags and filters.

Ideally these subsystems would be implemented in distinct packages. However
keeping them together made the implementation of Multiple Template Engines
less disruptive .

Here's a breakdown of which modules belong to which subsystem.

Multiple Template Engines:

- mango.template.backends.*
- mango.template.loader
- mango.template.response

Mango Template Language:

- mango.template.base
- mango.template.context
- mango.template.context_processors
- mango.template.loaders.*
- mango.template.debug
- mango.template.defaultfilters
- mango.template.defaulttags
- mango.template.engine
- mango.template.loader_tags
- mango.template.smartif

Shared:

- mango.template.utils

"""

# Multiple Template Engines

from .engine import Engine
from .utils import EngineHandler

engines = EngineHandler()

__all__ = ('Engine', 'engines')


# Mango Template Language

# Public exceptions
from .base import VariableDoesNotExist                                  # NOQA isort:skip
from .context import Context, ContextPopException, RequestContext       # NOQA isort:skip
from .exceptions import TemplateDoesNotExist, TemplateSyntaxError       # NOQA isort:skip

# Template parts
from .base import (                                                     # NOQA isort:skip
    Node, NodeList, Origin, Template, Variable,
)

# Library management
from .library import Library                                            # NOQA isort:skip

# Import the .autoreload module to trigger the registrations of signals.
from . import autoreload                                                # NOQA isort:skip


__all__ += ('Template', 'Context', 'RequestContext')
