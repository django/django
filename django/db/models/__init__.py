from django.conf import settings
from django.core import formfields, validators

from django.db import backend, connection

from django.utils.functional import curry
from django.utils.text import capfirst

from django.db.models.loading import get_installed_models, get_installed_model_modules
from django.db.models.query import Q
from django.db.models.manager import Manager
from django.db.models.base import Model

from django.db.models.fields import *
from django.db.models.fields.related import *

from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.db.models.exceptions import FieldDoesNotExist, BadKeywordArguments
from django.db.models import signals


# Admin stages.
ADD, CHANGE, BOTH = 1, 2, 3


#def get_module(app_label, module_name):
#    return __import__('%s.%s.%s' % (MODEL_PREFIX, app_label, module_name), '', '', [''])

def get_models(app):
    models = []
    get_models_helper(app, models)
    return models

def get_models_helper(mod, seen_models):
    if hasattr(mod, '_MODELS'):
        seen_models.extend(mod._MODELS)
    if hasattr(mod, '__all__'): 
        for name in mod.__all__:
            sub_mod = __import__("%s.%s" % (mod.__name__, name), '','',[''])
            get_models_helper(sub_mod, seen_models)

def get_app(app_label):
    
    for app_name in settings.INSTALLED_APPS:
        comps = app_name.split('.')
        if app_label == comps[-1]:
            app_models = __import__('%s.models' % app_name , '','',[''])
            return app_models
    
    raise ImproperlyConfigured, "App with label %s could not be found" % app_labelpostgres

class LazyDate:
    """
    Use in limit_choices_to to compare the field to dates calculated at run time
    instead of when the model is loaded.  For example::

        ... limit_choices_to = {'date__gt' : meta.LazyDate(days=-3)} ...

    which will limit the choices to dates greater than three days ago.
    """
    def __init__(self, **kwargs):
        self.delta = datetime.timedelta(**kwargs)

    def __str__(self):
        return str(self.__get_value__())

    def __repr__(self):
        return "<LazyDate: %s>" % self.delta

    def __get_value__(self):
        return datetime.datetime.now() + self.delta







