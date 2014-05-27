from functools import wraps
import sys
import warnings

from freedom.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured  # NOQA
from freedom.db.models.query import Q, QuerySet, Prefetch  # NOQA
from freedom.db.models.expressions import F  # NOQA
from freedom.db.models.manager import Manager  # NOQA
from freedom.db.models.base import Model  # NOQA
from freedom.db.models.aggregates import *  # NOQA
from freedom.db.models.fields import *  # NOQA
from freedom.db.models.fields.subclassing import SubfieldBase        # NOQA
from freedom.db.models.fields.files import FileField, ImageField  # NOQA
from freedom.db.models.fields.related import (  # NOQA
    ForeignKey, ForeignObject, OneToOneField, ManyToManyField,
    ManyToOneRel, ManyToManyRel, OneToOneRel)
from freedom.db.models.fields.proxy import OrderWrt  # NOQA
from freedom.db.models.deletion import (  # NOQA
    CASCADE, PROTECT, SET, SET_NULL, SET_DEFAULT, DO_NOTHING, ProtectedError)
from freedom.db.models.lookups import Lookup, Transform  # NOQA
from freedom.db.models import signals  # NOQA
from freedom.utils.deprecation import RemovedInFreedom19Warning


def permalink(func):
    """
    Decorator that calls urlresolvers.reverse() to return a URL using
    parameters returned by the decorated function "func".

    "func" should be a function that returns a tuple in one of the
    following formats:
        (viewname, viewargs)
        (viewname, viewargs, viewkwargs)
    """
    from freedom.core.urlresolvers import reverse

    @wraps(func)
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        return reverse(bits[0], None, *bits[1:3])
    return inner


# Deprecated aliases for functions were exposed in this module.

def make_alias(function_name):
    # Close function_name.
    def alias(*args, **kwargs):
        warnings.warn(
            "freedom.db.models.%s is deprecated." % function_name,
            RemovedInFreedom19Warning, stacklevel=2)
        # This raises a second warning.
        from . import loading
        return getattr(loading, function_name)(*args, **kwargs)
    alias.__name__ = function_name
    return alias

this_module = sys.modules['freedom.db.models']

for function_name in ('get_apps', 'get_app_path', 'get_app_paths', 'get_app',
                      'get_models', 'get_model', 'register_models'):
    setattr(this_module, function_name, make_alias(function_name))

del this_module, make_alias, function_name
