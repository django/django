from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.core import validators
from django.db import connection
from django.db.models.loading import get_apps, get_app, get_models, get_model, register_models
from django.db.models.query import Q
from django.db.models.manager import Manager
from django.db.models.base import Model, AdminOptions
from django.db.models.fields import *
from django.db.models.fields.subclassing import SubfieldBase
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField, ManyToOneRel, ManyToManyRel, OneToOneRel, TABULAR, STACKED
from django.db.models import signals
from django.utils.functional import curry
from django.utils.text import capfirst

# Admin stages.
ADD, CHANGE, BOTH = 1, 2, 3

def permalink(func):
    """
    Decorator that calls urlresolvers.reverse() to return a URL using
    parameters returned by the decorated function "func".

    "func" should be a function that returns a tuple in one of the
    following formats:
        (viewname, viewargs)
        (viewname, viewargs, viewkwargs)
    """
    from django.core.urlresolvers import reverse
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        return reverse(bits[0], None, *bits[1:3])
    return inner
