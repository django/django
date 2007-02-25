from django.contrib.admin import ModelAdmin
from django.db.models import Model

class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class AdminSite(object):
    def __init__(self):
        self._registry = {} # model_class -> admin_class

    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.
        """
        admin_class = admin_class or ModelAdmin
        # TODO: Handle options
        if issubclass(model_or_iterable, Model):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__class__.__name__)
            self._registry[model] = admin_class

    def unregister(self, model_or_iterable):
        if issubclass(model_or_iterable, Model):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__class__.__name__)
            del self._registry[model]

# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = AdminSite()
