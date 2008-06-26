"Utilities for loading models and the modules that contain them."

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict

import sys
import os
import threading

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

class AppCache(object):
    """
    A cache that stores installed applications and their models. Used to
    provide reverse-relations and for app introspection (e.g. admin).
    """
    # Use the Borg pattern to share state between all instances. Details at
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66531.
    __shared_state = dict(
        # Keys of app_store are the model modules for each application.
        app_store = SortedDict(),

        # Mapping of app_labels to a dictionary of model names to model code.
        app_models = SortedDict(),

        # Mapping of app_labels to errors raised when trying to import the app.
        app_errors = {},

        # -- Everything below here is only used when populating the cache --
        loaded = False,
        handled = {},
        postponed = [],
        nesting_level = 0,
        write_lock = threading.RLock(),
    )

    def __init__(self):
        self.__dict__ = self.__shared_state

    def _populate(self):
        """
        Fill in all the cache information. This method is threadsafe, in the
        sense that every caller will see the same state upon return, and if the
        cache is already initialised, it does no work.
        """
        if self.loaded:
            return
        self.write_lock.acquire()
        try:
            if self.loaded:
                return
            for app_name in settings.INSTALLED_APPS:
                if app_name in self.handled:
                    continue
                self.load_app(app_name, True)
            if not self.nesting_level:
                for app_name in self.postponed:
                    self.load_app(app_name)
                self.loaded = True
        finally:
            self.write_lock.release()

    def load_app(self, app_name, can_postpone=False):
        """
        Loads the app with the provided fully qualified name, and returns the
        model module.
        """
        self.handled[app_name] = None
        self.nesting_level += 1
        mod = __import__(app_name, {}, {}, ['models'])
        self.nesting_level -= 1
        if not hasattr(mod, 'models'):
            if can_postpone:
                # Either the app has no models, or the package is still being
                # imported by Python and the model module isn't available yet.
                # We will check again once all the recursion has finished (in
                # populate).
                self.postponed.append(app_name)
            return None
        if mod.models not in self.app_store:
            self.app_store[mod.models] = len(self.app_store)
        return mod.models

    def app_cache_ready(self):
        """
        Returns true if the model cache is fully populated.

        Useful for code that wants to cache the results of get_models() for
        themselves once it is safe to do so.
        """
        return self.loaded

    def get_apps(self):
        "Returns a list of all installed modules that contain models."
        self._populate()

        # Ensure the returned list is always in the same order (with new apps
        # added at the end). This avoids unstable ordering on the admin app
        # list page, for example.
        apps = [(v, k) for k, v in self.app_store.items()]
        apps.sort()
        return [elt[1] for elt in apps]

    def get_app(self, app_label, emptyOK=False):
        """
        Returns the module containing the models for the given app_label. If
        the app has no models in it and 'emptyOK' is True, returns None.
        """
        self._populate()
        self.write_lock.acquire()
        try:
            for app_name in settings.INSTALLED_APPS:
                if app_label == app_name.split('.')[-1]:
                    mod = self.load_app(app_name, False)
                    if mod is None:
                        if emptyOK:
                            return None
                    else:
                        return mod
            raise ImproperlyConfigured, "App with label %s could not be found" % app_label
        finally:
            self.write_lock.release()

    def get_app_errors(self):
        "Returns the map of known problems with the INSTALLED_APPS."
        self._populate()
        return self.app_errors

    def get_models(self, app_mod=None):
        """
        Given a module containing models, returns a list of the models.
        Otherwise returns a list of all installed models.
        """
        self._populate()
        if app_mod:
            return self.app_models.get(app_mod.__name__.split('.')[-2], SortedDict()).values()
        else:
            model_list = []
            for app_entry in self.app_models.itervalues():
                model_list.extend(app_entry.values())
            return model_list

    def get_model(self, app_label, model_name, seed_cache=True):
        """
        Returns the model matching the given app_label and case-insensitive
        model_name.

        Returns None if no model is found.
        """
        if seed_cache:
            self._populate()
        return self.app_models.get(app_label, SortedDict()).get(model_name.lower())

    def register_models(self, app_label, *models):
        """
        Register a set of models as belonging to an app.
        """
        for model in models:
            # Store as 'name: model' pair in a dictionary
            # in the app_models dictionary
            model_name = model._meta.object_name.lower()
            model_dict = self.app_models.setdefault(app_label, SortedDict())
            if model_name in model_dict:
                # The same model may be imported via different paths (e.g.
                # appname.models and project.appname.models). We use the source
                # filename as a means to detect identity.
                fname1 = os.path.abspath(sys.modules[model.__module__].__file__)
                fname2 = os.path.abspath(sys.modules[model_dict[model_name].__module__].__file__)
                # Since the filename extension could be .py the first time and
                # .pyc or .pyo the second time, ignore the extension when
                # comparing.
                if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                    continue
            model_dict[model_name] = model

cache = AppCache()

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = cache.get_apps
get_app = cache.get_app
get_app_errors = cache.get_app_errors
get_models = cache.get_models
get_model = cache.get_model
register_models = cache.register_models
load_app = cache.load_app
app_cache_ready = cache.app_cache_ready
