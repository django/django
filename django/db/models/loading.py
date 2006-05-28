"Utilities for loading models and the modules that contain them."

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models')

_app_list = None # Cache of installed apps.
_app_models = {} # Dictionary of models against app label
                 # Each value is a dictionary of model name: model class

def get_apps():
    "Returns a list of all installed modules that contain models."
    global _app_list
    if _app_list is not None:
        return _app_list
    _app_list = []
    for app_name in settings.INSTALLED_APPS:
        try:
            mod = __import__(app_name, '', '', ['models'])
        except ImportError:
            pass # Assume this app doesn't have a models.py in it.
                 # GOTCHA: It may have a models.py that raises ImportError.
        else:
            try:
                _app_list.append(mod.models)
            except AttributeError:
                pass # This app doesn't have a models.py in it.
    return _app_list

def get_app(app_label):
    "Returns the module containing the models for the given app_label."
    for app_name in settings.INSTALLED_APPS:
        if app_label == app_name.split('.')[-1]:
            return __import__(app_name, '', '', ['models']).models
    raise ImproperlyConfigured, "App with label %s could not be found" % app_label

def get_models(app_mod=None):
    """
    Given a module containing models, returns a list of the models. Otherwise
    returns a list of all installed models.
    """
    app_list = get_apps() # Run get_apps() to populate the _app_list cache. Slightly hackish.
    if app_mod:
        return _app_models.get(app_mod.__name__.split('.')[-2], {}).values()
    else:
        model_list = []
        for app_mod in app_list:
            model_list.extend(get_models(app_mod))
        return model_list

def get_model(app_label, model_name):
    """
    Returns the model matching the given app_label and case-insensitive model_name.
    Returns None if no model is found.
    """
    get_apps() # Run get_apps() to populate the _app_list cache. Slightly hackish.
    try:
        model_dict = _app_models[app_label]
    except KeyError:
        return None

    try:
        return model_dict[model_name.lower()]
    except KeyError:
        return None

def register_models(app_label, *models):
    """
    Register a set of models as belonging to an app.
    """
    for model in models:
        # Store as 'name: model' pair in a dictionary
        # in the _app_models dictionary
        model_name = model._meta.object_name.lower()
        model_dict = _app_models.setdefault(app_label, {})
        model_dict[model_name] = model
