from __future__ import unicode_literals

import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn(
    ('freedom.contrib.contenttypes.generic is deprecated and will be removed in '
     'Freedom 1.9. Its contents have been moved to the fields, forms, and admin '
     'submodules of freedom.contrib.contenttypes.'), RemovedInFreedom19Warning, stacklevel=2
)

from freedom.contrib.contenttypes.admin import (  # NOQA
    GenericInlineModelAdmin, GenericStackedInline, GenericTabularInline
)
from freedom.contrib.contenttypes.fields import (  # NOQA
    GenericForeignKey, GenericRelation
)
from freedom.contrib.contenttypes.forms import (  # NOQA
    BaseGenericInlineFormSet, generic_inlineformset_factory
)
