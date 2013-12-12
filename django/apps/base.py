from collections import OrderedDict


class AppConfig(object):
    """
    Class representing a Django application and its configuration.
    """

    def __init__(self, label, models_module=None, installed=True):
        # Last component of the Python path to the application eg. 'admin'.
        self.label = label

        # Module containing models eg. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.pyc'>.
        self.models_module = models_module

        # Mapping of lower case model names to model classes.
        self.models = OrderedDict()

        # Whether the app is in INSTALLED_APPS or was automatically created
        # when one of its models was imported.
        self.installed = installed

    def __repr__(self):
        return '<AppConfig: %s>' % self.label
