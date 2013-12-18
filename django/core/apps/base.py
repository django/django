from importlib import import_module

from django.utils.module_loading import module_has_submodule
from django.utils._os import upath


MODELS_MODULE_NAME = 'models'


class AppConfig(object):
    """
    Class representing a Django application and its configuration.
    """

    def __init__(self, app_name):
        # Full Python path to the application eg. 'django.contrib.admin'.
        # This is the value that appears in INSTALLED_APPS.
        self.name = app_name

        # Last component of the Python path to the application eg. 'admin'.
        # This value must be unique across a Django project.
        self.label = app_name.rpartition(".")[2]

        # Root module eg. <module 'django.contrib.admin' from
        # 'django/contrib/admin/__init__.pyc'>.
        self.app_module = import_module(app_name)

        # Module containing models eg. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.pyc'>. Set by import_models().
        # None if the application doesn't have a models module.
        self.models_module = None

        # Mapping of lower case model names to model classes. Initally set to
        # None to prevent accidental access before import_models() runs.
        self.models = None

        # Filesystem path to the application directory eg.
        # u'/usr/lib/python2.7/dist-packages/django/contrib/admin'.
        # This is a unicode object on Python 2 and a str on Python 3.
        self.path = upath(self.app_module.__path__[0])

    def __repr__(self):
        return '<AppConfig: %s>' % self.label

    def import_models(self, all_models):
        # Dictionary of models for this app, stored in the 'all_models'
        # attribute of the AppCache this AppConfig is attached to. Injected as
        # a parameter because it may get populated before this method has run.
        self.models = all_models

        if module_has_submodule(self.app_module, MODELS_MODULE_NAME):
            models_module_name = '%s.%s' % (self.name, MODELS_MODULE_NAME)
            self.models_module = import_module(models_module_name)
