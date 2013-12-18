from collections import OrderedDict

from django.utils._os import upath


class AppConfig(object):
    """
    Class representing a Django application and its configuration.
    """

    def __init__(self, name, app_module, models_module):
        # Full Python path to the application eg. 'django.contrib.admin'.
        # This is the value that appears in INSTALLED_APPS.
        self.name = name

        # Last component of the Python path to the application eg. 'admin'.
        # This value must be unique across a Django project.
        self.label = name.rpartition(".")[2]

        # Root module eg. <module 'django.contrib.admin' from
        # 'django/contrib/admin/__init__.pyc'>.
        self.app_module = app_module

        # Module containing models eg. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.pyc'>. None if the application
        # doesn't have a models module.
        self.models_module = models_module

        # Mapping of lower case model names to model classes.
        # Populated by calls to AppCache.register_model().
        self.models = OrderedDict()

        # Whether the app is in INSTALLED_APPS or was automatically created
        # when one of its models was imported.
        self.installed = app_module is not None

        # Filesystem path to the application directory eg.
        # u'/usr/lib/python2.7/dist-packages/django/contrib/admin'.
        # This is a unicode object on Python 2 and a str on Python 3.
        self.path = upath(app_module.__path__[0]) if app_module is not None else None

    def __repr__(self):
        return '<AppConfig: %s>' % self.label
