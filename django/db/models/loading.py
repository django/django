"Utilities for loading models and the modules that contain them."

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import sys
import os

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models')

_app_list = []   # Cache of installed apps.
                 # Entry is not placed in app_list cache until entire app is loaded.
_app_models = {} # Dictionary of models against app label
                 # Each value is a dictionary of model name: model class
                 # Applabel and Model entry exists in cache when individual model is loaded.
_app_errors = {} # Dictionary of errors that were experienced when loading the INSTALLED_APPS
                 # Key is the app_name of the model, value is the exception that was raised
                 # during model loading.
_loaded = False  # Has the contents of settings.INSTALLED_APPS been loaded?
                 # i.e., has get_apps() been called?

def get_apps():
    "Returns a list of all installed modules that contain models."
    global _app_list
    global _loaded
    if not _loaded:
        _loaded = True
        for app_name in settings.INSTALLED_APPS:
            try:
                load_app(app_name)
            except Exception, e:
                # Problem importing the app
                _app_errors[app_name] = e
    return _app_list

def get_app(app_label, emptyOK = False):
    "Returns the module containing the models for the given app_label. If the app has no models in it and 'emptyOK' is True, returns None."
    get_apps() # Run get_apps() to populate the _app_list cache. Slightly hackish.
    for app_name in settings.INSTALLED_APPS:
        if app_label == app_name.split('.')[-1]:
            mod = load_app(app_name)
            if mod is None:
                if emptyOK:
                    return None
            else:
                return mod
    raise ImproperlyConfigured, "App with label %s could not be found" % app_label

def load_app(app_name):
    "Loads the app with the provided fully qualified name, and returns the model module."
    global _app_list
    mod = __import__(app_name, '', '', ['models'])
    if not hasattr(mod, 'models'):
        return None
    if mod.models not in _app_list:
        _app_list.append(mod.models)
    return mod.models

def get_app_errors():
    "Returns the map of known problems with the INSTALLED_APPS"
    global _app_errors
    get_apps() # Run get_apps() to populate the _app_list cache. Slightly hackish.
    return _app_errors

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
        if model_dict.has_key(model_name):
            # The same model may be imported via different paths (e.g.
            # appname.models and project.appname.models). We use the source
            # filename as a means to detect identity.
            fname1 = os.path.abspath(sys.modules[model.__module__].__file__)
            fname2 = os.path.abspath(sys.modules[model_dict[model_name].__module__].__file__)
            # Since the filename extension could be .py the first time and .pyc
            # or .pyo the second time, ignore the extension when comparing.
            if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                continue
        model_dict[model_name] = model
