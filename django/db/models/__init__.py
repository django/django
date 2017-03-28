from django.core.exceptions import ObjectDoesNotExist
from django.db.models import signals
from django.db.models.aggregates import *  # NOQA
from django.db.models.aggregates import __all__ as aggregates_all
from django.db.models.deletion import (
    CASCADE, DO_NOTHING, PROTECT, SET, SET_DEFAULT, SET_NULL, ProtectedError,
)
from django.db.models.expressions import (
    Case, Exists, Expression, ExpressionWrapper, F, Func, OuterRef, Subquery,
    Value, When,
)
from django.db.models.fields import *  # NOQA
from django.db.models.fields import __all__ as fields_all
from django.db.models.fields.files import FileField, ImageField
from django.db.models.fields.proxy import OrderWrt
from django.db.models.indexes import *  # NOQA
from django.db.models.indexes import __all__ as indexes_all
from django.db.models.lookups import Lookup, Transform
from django.db.models.manager import Manager
from django.db.models.query import (
    Prefetch, Q, QuerySet, prefetch_related_objects,
)

# Imports that would create circular imports if sorted
from django.db.models.base import DEFERRED, Model  # isort:skip
from django.db.models.fields.related import (  # isort:skip
    ForeignKey, ForeignObject, OneToOneField, ManyToManyField,
    ManyToOneRel, ManyToManyRel, OneToOneRel,
)


def permalink(func):
    """
    Decorator that calls urls.reverse() to return a URL using parameters
    returned by the decorated function "func".

    "func" should be a function that returns a tuple in one of the
    following formats:
        (viewname, viewargs)
        (viewname, viewargs, viewkwargs)
    """
    import warnings
    from functools import wraps

    from django.urls import reverse
    from django.utils.deprecation import RemovedInDjango21Warning

    warnings.warn(
        'permalink() is deprecated in favor of calling django.urls.reverse() '
        'in the decorated method.',
        RemovedInDjango21Warning,
        stacklevel=2,
    )

    @wraps(func)
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        return reverse(bits[0], None, *bits[1:3])
    return inner


__all__ = aggregates_all + fields_all + indexes_all
__all__ += [
    'ObjectDoesNotExist', 'signals',
    'CASCADE', 'DO_NOTHING', 'PROTECT', 'SET', 'SET_DEFAULT', 'SET_NULL',
    'ProtectedError',
    'Case', 'Exists', 'Expression', 'ExpressionWrapper', 'F', 'Func',
    'OuterRef', 'Subquery', 'Value', 'When',
    'FileField', 'ImageField', 'OrderWrt', 'Lookup', 'Transform', 'Manager',
    'Prefetch', 'Q', 'QuerySet', 'prefetch_related_objects', 'DEFERRED', 'Model',
    'ForeignKey', 'ForeignObject', 'OneToOneField', 'ManyToManyField',
    'ManyToOneRel', 'ManyToManyRel', 'OneToOneRel', 'permalink',
]
