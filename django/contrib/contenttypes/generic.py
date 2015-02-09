from __future__ import unicode_literals

import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    ('django.contrib.contenttypes.generic is deprecated and will be removed in '
     'Django 1.9. Its contents have been moved to the fields, forms, and admin '
     'submodules of django.contrib.contenttypes.'), RemovedInDjango19Warning, stacklevel=2
)

from django.contrib.contenttypes.admin import (  # NOQA isort:skip
    GenericInlineModelAdmin, GenericStackedInline, GenericTabularInline,
)
from django.contrib.contenttypes.fields import (  # NOQA isort:skip
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.forms import (  # NOQA isort:skip
    BaseGenericInlineFormSet, generic_inlineformset_factory,
)
