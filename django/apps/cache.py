"Utilities for loading models and the modules that contain them."

from collections import OrderedDict
import copy
import imp
from importlib import import_module
import os
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import module_has_submodule
from django.utils._os import upath
from django.utils import six

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

MODELS_MODULE_NAME = 'models'


class ModelDict(OrderedDict):
    """
    We need to special-case the deepcopy for this, as the keys are modules,
    which can't be deep copied.
    """
    def __deepcopy__(self, memo):
        return self.__class__([(key, copy.deepcopy(value, memo))
                               for key, value in self.items()])


class UnavailableApp(Exception):
    pass


def _initialize():
    """
    Returns a dictionary to be used as the initial value of the
    [shared] state of the app cache.
    """
    return dict(
        # Mapping of installed app_labels to model modules for that app.
        app_labels=OrderedDict(),

        # Mapping of app_labels to a dictionary of model names to model code.
        # May contain apps that are not installed.
        app_models=ModelDict(),

        # Mapping of app_labels to errors raised when trying to import the app.
        app_errors={},

        # Pending lookups for lazy relations
        pending_lookups={},

        # List of app_labels that allows restricting the set of apps.
        # Used by TransactionTestCase.available_apps for performance reasons.
        available_apps=None,

        # -- Everything below here is only used when populating the cache --
        loads_installed=True,
        loaded=False,
        handled=set(),
        postponed=[],
        nesting_level=0,
        _get_models_cache={},
    )


class BaseAppCache(object):
    """
    A cache that stores installed applications and their models. Used to
    provide reverse-relations and for app introspection (e.g. admin).

    This provides the base (non-Borg) AppCache class - the AppCache
    subclass adds borg-like behaviour for the few cases where it's needed.
    """

    def __init__(self):
        self.__dict__ = _initialize()
        # This stops _populate loading from INSTALLED_APPS and ignores the
        # only_installed arguments to get_model[s]
        self.loads_installed = False

    def _populate(self):
        """
        Fill in all the cache information. This method is threadsafe, in the
        sense that every caller will see the same state upon return, and if the
        cache is already initialised, it does no work.
        """
        if self.loaded:
            return
        if not self.loads_installed:
            self.loaded = True
            return
        # Note that we want to use the import lock here - the app loading is
        # in many cases initiated implicitly by importing, and thus it is
        # possible to end up in deadlock when one thread initiates loading
        # without holding the importer lock and another thread then tries to
        # import something which also launches the app loading. For details of
        # this situation see #18251.
        imp.acquire_lock()
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
            imp.release_lock()

    def _label_for(self, app_mod):
        """
        Return app_label for given models module.

        """
        return app_mod.__name__.split('.')[-2]

    def load_app(self, app_name, can_postpone=False):
        """
        Loads the app with the provided fully qualified name, and returns the
        model module.
        """
        app_module = import_module(app_name)
        self.handled.add(app_name)
        self.nesting_level += 1
        try:
            models = import_module('%s.%s' % (app_name, MODELS_MODULE_NAME))
        except ImportError:
            self.nesting_level -= 1
            # If the app doesn't have a models module, we can just ignore the
            # ImportError and return no models for it.
            if not module_has_submodule(app_module, MODELS_MODULE_NAME):
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
        label = self._label_for(models)
        if label not in self.app_labels:
            self.app_labels[label] = models
        return models

    def app_cache_ready(self):
        """
        Returns true if the model cache is fully populated.

        Useful for code that wants to cache the results of get_models() for
        themselves once it is safe to do so.
        """
        return self.loaded

    def get_apps(self):
        """
        Returns a list of all installed modules that contain models.
        """
        self._populate()

        # app_labels is an OrderedDict, which ensures that the returned list
        # is always in the same order (with new apps added at the end). This
        # avoids unstable ordering on the admin app list page, for example.
        apps = self.app_labels.items()
        if self.available_apps is not None:
            apps = [app for app in apps if app[0] in self.available_apps]
        return [app[1] for app in apps]

    def _get_app_package(self, app):
        return '.'.join(app.__name__.split('.')[:-1])

    def get_app_package(self, app_label):
        return self._get_app_package(self.get_app(app_label))

    def _get_app_path(self, app):
        if hasattr(app, '__path__'):        # models/__init__.py package
            app_path = app.__path__[0]
        else:                               # models.py module
            app_path = app.__file__
        return os.path.dirname(upath(app_path))

    def get_app_path(self, app_label):
        return self._get_app_path(self.get_app(app_label))

    def get_app_paths(self):
        """
        Returns a list of paths to all installed apps.

        Useful for discovering files at conventional locations inside apps
        (static files, templates, etc.)
        """
        self._populate()

        app_paths = []
        for app in self.get_apps():
            app_paths.append(self._get_app_path(app))
        return app_paths

    def get_app(self, app_label, emptyOK=False):
        """
        Returns the module containing the models for the given app_label.

        Returns None if the app has no models in it and emptyOK is True.

        Raises UnavailableApp when set_available_apps() in in effect and
        doesn't include app_label.
        """
        self._populate()
        imp.acquire_lock()
        try:
            for app_name in settings.INSTALLED_APPS:
                if app_label == app_name.split('.')[-1]:
                    mod = self.load_app(app_name, False)
                    if mod is None and not emptyOK:
                        raise ImproperlyConfigured("App with label %s is missing a models.py module." % app_label)
                    if self.available_apps is not None and app_label not in self.available_apps:
                        raise UnavailableApp("App with label %s isn't available." % app_label)
                    return mod
            raise ImproperlyConfigured("App with label %s could not be found" % app_label)
        finally:
            imp.release_lock()

    def get_app_errors(self):
        "Returns the map of known problems with the INSTALLED_APPS."
        self._populate()
        return self.app_errors

    def get_models(self, app_mod=None,
                   include_auto_created=False, include_deferred=False,
                   only_installed=True, include_swapped=False):
        """
        Given a module containing models, returns a list of the models.
        Otherwise returns a list of all installed models.

        By default, auto-created models (i.e., m2m models without an
        explicit intermediate table) are not included. However, if you
        specify include_auto_created=True, they will be.

        By default, models created to satisfy deferred attribute
        queries are *not* included in the list of models. However, if
        you specify include_deferred, they will be.

        By default, models that aren't part of installed apps will *not*
        be included in the list of models. However, if you specify
        only_installed=False, they will be. If you're using a non-default
        AppCache, this argument does nothing - all models will be included.

        By default, models that have been swapped out will *not* be
        included in the list of models. However, if you specify
        include_swapped, they will be.
        """
        if not self.loads_installed:
            only_installed = False
        cache_key = (app_mod, include_auto_created, include_deferred, only_installed, include_swapped)
        model_list = None
        try:
            model_list = self._get_models_cache[cache_key]
            if self.available_apps is not None and only_installed:
                model_list = [m for m in model_list if m._meta.app_label in self.available_apps]
            return model_list
        except KeyError:
            pass
        self._populate()
        if app_mod:
            app_label = self._label_for(app_mod)
            if app_label in self.app_labels:
                app_list = [self.app_models.get(app_label, ModelDict())]
            else:
                app_list = []
        else:
            if only_installed:
                app_list = [self.app_models.get(app_label, ModelDict())
                            for app_label in six.iterkeys(self.app_labels)]
            else:
                app_list = six.itervalues(self.app_models)
        model_list = []
        for app in app_list:
            model_list.extend(
                model for model in app.values()
                if ((not model._deferred or include_deferred) and
                    (not model._meta.auto_created or include_auto_created) and
                    (not model._meta.swapped or include_swapped))
            )
        self._get_models_cache[cache_key] = model_list
        if self.available_apps is not None and only_installed:
            model_list = [m for m in model_list if m._meta.app_label in self.available_apps]
        return model_list

    def get_model(self, app_label, model_name,
                  seed_cache=True, only_installed=True):
        """
        Returns the model matching the given app_label and case-insensitive
        model_name.

        Returns None if no model is found.

        Raises UnavailableApp when set_available_apps() in in effect and
        doesn't include app_label.
        """
        if not self.loads_installed:
            only_installed = False
        if seed_cache:
            self._populate()
        if only_installed and app_label not in self.app_labels:
            return None
        if (self.available_apps is not None and only_installed
                and app_label not in self.available_apps):
            raise UnavailableApp("App with label %s isn't available." % app_label)
        try:
            return self.app_models[app_label][model_name.lower()]
        except KeyError:
            return None

    def register_models(self, app_label, *models):
        """
        Register a set of models as belonging to an app.
        """
        for model in models:
            # Store as 'name: model' pair in a dictionary
            # in the app_models dictionary
            model_name = model._meta.model_name
            model_dict = self.app_models.setdefault(app_label, ModelDict())
            if model_name in model_dict:
                # The same model may be imported via different paths (e.g.
                # appname.models and project.appname.models). We use the source
                # filename as a means to detect identity.
                fname1 = os.path.abspath(upath(sys.modules[model.__module__].__file__))
                fname2 = os.path.abspath(upath(sys.modules[model_dict[model_name].__module__].__file__))
                # Since the filename extension could be .py the first time and
                # .pyc or .pyo the second time, ignore the extension when
                # comparing.
                if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                    continue
            model_dict[model_name] = model
        self._get_models_cache.clear()

    def set_available_apps(self, available):
        if not set(available).issubset(set(settings.INSTALLED_APPS)):
            extra = set(available) - set(settings.INSTALLED_APPS)
            raise ValueError("Available apps isn't a subset of installed "
                "apps, extra apps: " + ", ".join(extra))
        self.available_apps = set(app.rsplit('.', 1)[-1] for app in available)

    def unset_available_apps(self):
        self.available_apps = None


class AppCache(BaseAppCache):
    """
    A cache that stores installed applications and their models. Used to
    provide reverse-relations and for app introspection (e.g. admin).

    Borg version of the BaseAppCache class.
    """

    __shared_state = _initialize()

    def __init__(self):
        self.__dict__ = self.__shared_state


cache = AppCache()


# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = cache.get_apps
get_app_package = cache.get_app_package
get_app_path = cache.get_app_path
get_app_paths = cache.get_app_paths
get_app = cache.get_app
get_app_errors = cache.get_app_errors
get_models = cache.get_models
get_model = cache.get_model
register_models = cache.register_models
load_app = cache.load_app
app_cache_ready = cache.app_cache_ready
