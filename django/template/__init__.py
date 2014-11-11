### Multiple Template Engines

from .utils import EngineHandler


engines = EngineHandler()

__all__ = ('engines',)


### Django Template Language

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
