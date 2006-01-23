"Utilities for loading models and the modules that contain them."

from django.conf import settings

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model')

_app_list = None # Cache of installed apps.

def get_apps():
    "Returns a list of all installed modules that contain models."
    global _app_list
    if _app_list is not None:
        return _app_list
    _app_list = []
    for app_name in settings.INSTALLED_APPS:
        try:
            _app_list.append(__import__(app_name + '.models', '', '', ['']))
        except ImportError, e:
            pass
    return _app_list

def get_app(app_label):
    "Returns the module containing the models for the given app_label."
    for app_name in settings.INSTALLED_APPS:
        if app_label == app_name.split('.')[-1]:
            return __import__('%s.models' % app_name, '', '', [''])
    raise ImproperlyConfigured, "App with label %s could not be found" % app_label

def get_models(app_mod=None):
    """
    Given a module containing models, returns a list of the models. Otherwise
    returns a list of all installed models.
    """
    if app_mod:
        return getattr(app_mod, '_MODELS', ())
    else:
        model_list = []
        for app_mod in get_apps():
            model_list.extend(getattr(app_mod, '_MODELS', ()))
        return model_list

def get_model(app_label, model_name):
    """
    Returns the model matching the given app_label and case-insensitive model_name.
    Returns None if no model is found.
    """
    for app_mod in get_apps():
        for model in get_models(app_mod):
            if model._meta.object_name.lower() == model_name:
                return model
