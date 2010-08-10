from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

import imp
import sys
import os
import threading


class MultipleInstancesReturned(Exception):
    "The function returned multiple App instances with the same label"
    pass

class App(object):
    """
    An App in Django is a python package that:
        - is listen in the INSTALLED_APPS setting
        - has a models.py file that with class(es) subclassing ModelBase
    """
    def __init__(self, name):
        self.name = name
        # errors raised when trying to import the app
        self.errors = []
        self.models = []
        self.models_module = None

    def __repr__(self):
        return '<App: %s>' % self.name

class AppCache(object):
    """
    A cache that stores installed applications and their models. Used to
    provide reverse-relations and for app introspection (e.g. admin).
    """
    # Use the Borg pattern to share state between all instances. Details at
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66531.
    __shared_state = dict(
        # List of App instances
        app_instances = [],

        # Mapping of app_labels to a dictionary of model names to model code.
        app_models = SortedDict(),

        # -- Everything below here is only used when populating the cache --
        loaded = False,
        handled = {},
        postponed = [],
        nesting_level = 0,
        write_lock = threading.RLock(),
        _get_models_cache = {},
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

        try:
            app_module = import_module(app_name)
        except ImportError:
            # If the import fails, we assume it was because an path to a
            # class was passed (e.g. "foo.bar.MyApp")
            # We split the app_name by the rightmost dot to get the path
            # and classname, and then try importing it again
            if not '.' in app_name:
                raise
            app_name, app_classname = app_name.rsplit('.', 1)
            app_module = import_module(app_name)
            app_class = getattr(app_module, app_classname)
        else:
            app_class = App

        # check if an app instance with that name already exists
        app_instance = self.find_app(app_name)
        if not app_instance:
            if '.' in app_name:
                app_instance_name = app_name.rsplit('.', 1)[1]
            else:
                app_instance_name = app_name
            app_instance = app_class(app_instance_name)
            self.app_instances.append(app_instance)

        try:
            models = import_module('.models', app_name)
        except ImportError:
            self.nesting_level -= 1
            # If the app doesn't have a models module, we can just ignore the
            # ImportError and return no models for it.
            if not module_has_submodule(app_module, 'models'):
                return None
            # But if the app does have a models module, we need to figure out
            # whether to suppress or propagate the error. If can_postpone is
            # True then it may be that the package is still being imported by
            # Python and the models module isn't available yet. So we add the
            # app to the postponed list and we'll try it again after all the
            # recursion has finished (in populate). If can_postpone is False
            # then it's time to raise the ImportError.
            else:
                if can_postpone:
                    self.postponed.append(app_name)
                    return None
                else:
                    raise

        self.nesting_level -= 1
        app = self.find_app(app_name.split('.')[-1])
        if app and models is not app.models_module:
            app.models_module = models
        return models

    def find_app(self, name):
        "Returns the App instance that matches name"
        if '.' in name:
            name = name.rsplit('.', 1)[1]
        for app in self.app_instances:
            if app.name == name:
                return app

    def create_app(self, name):
        """create an app instance"""
        name = name.split('.')[-1]
        app = self.find_app(name)
        if not app:
            app = App(name)
            self.app_instances.append(app)
        return app

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
        return [app.models_module for app in self.app_instances\
                if app.models_module]

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
            raise ImproperlyConfigured("App with label %s could not be found" % app_label)
        finally:
            self.write_lock.release()

    def get_app_errors(self):
        "Returns the map of known problems with the INSTALLED_APPS."
        self._populate()
        errors = {}
        for app in self.app_instances:
            if app.errors:
                errors.update({app.label: app.errors})
        return errors

    def get_models(self, app_mod=None, include_auto_created=False, include_deferred=False):
        """
        Given a module containing models, returns a list of the models.
        Otherwise returns a list of all installed models.

        By default, auto-created models (i.e., m2m models without an
        explicit intermediate table) are not included. However, if you
        specify include_auto_created=True, they will be.

        By default, models created to satisfy deferred attribute
        queries are *not* included in the list of models. However, if
        you specify include_deferred, they will be.
        """
        cache_key = (app_mod, include_auto_created, include_deferred)
        try:
            return self._get_models_cache[cache_key]
        except KeyError:
            pass
        self._populate()
        if app_mod:
            app_label = app_mod.__name__.split('.')[-2]
            app = self.find_app(app_label)
            if app:
                app_list = [app]
        else:
            app_list = self.app_instances
        model_list = []
        for app in app_list:
            models = app.models
            model_list.extend(
                model for model in models
                if ((not model._deferred or include_deferred)
                    and (not model._meta.auto_created or include_auto_created))
            )
        self._get_models_cache[cache_key] = model_list
        return model_list

    def get_model(self, app_label, model_name, seed_cache=True):
        """
        Returns the model matching the given app_label and case-insensitive
        model_name.

        Returns None if no model is found.
        """
        if seed_cache:
            self._populate()
        app = self.find_app(app_label)
        if app:
            for model in app.models:
                if model_name.lower() == model._meta.object_name.lower():
                    return model

    def register_models(self, app_label, *models):
        """
        Register a set of models as belonging to an app.
        """
        app_instance = self.find_app(app_label)

        # Create a new App instance if the ModelBase tries to register
        # an app that isn't listed in INSTALLED_APPS
        if not app_instance:
            app_instance = App(app_label)
            self.app_instances.append(app_instance)

        for model in models:
            # Store as 'name: model' pair in a dictionary
            # in the models list of the App instance
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
            app_instance.models.append(model)
        self._get_models_cache.clear()

cache = AppCache()
