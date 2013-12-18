"Utilities for loading models and the modules that contain them."

from collections import defaultdict, OrderedDict
from contextlib import contextmanager
from importlib import import_module
import os
import sys
import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_lock, module_has_submodule
from django.utils._os import upath

from .base import AppConfig


MODELS_MODULE_NAME = 'models'


class UnavailableApp(Exception):
    pass


class AppCache(object):
    """
    A cache that stores installed applications and their models. Used to
    provide reverse-relations and for app introspection.
    """

    def __init__(self, master=False):
        # Only one master of the app-cache may exist at a given time, and it
        # shall be the app_cache variable defined at the end of this module.
        if master and hasattr(sys.modules[__name__], 'app_cache'):
            raise RuntimeError("You may create only one master app cache.")

        # When master is set to False, the app cache isn't populated from
        # INSTALLED_APPS and ignores the only_installed arguments to
        # get_model[s].
        self.master = master

        # Mapping of app labels => model names => model classes. Used to
        # register models before the app cache is populated and also for
        # applications that aren't installed.
        self.all_models = defaultdict(OrderedDict)

        # Mapping of labels to AppConfig instances for installed apps.
        self.app_configs = OrderedDict()

        # Pending lookups for lazy relations
        self.pending_lookups = {}

        # Set of app names. Allows restricting the set of installed apps.
        # Used by TransactionTestCase.available_apps for performance reasons.
        self.available_apps = None

        # -- Everything below here is only used when populating the cache --
        self.loaded = False
        self.handled = set()
        self.postponed = []
        self.nesting_level = 0
        self._get_models_cache = {}

    def populate(self):
        """
        Fill in all the cache information. This method is threadsafe, in the
        sense that every caller will see the same state upon return, and if the
        cache is already initialised, it does no work.
        """
        if self.loaded:
            return
        if not self.master:
            self.loaded = True
            return
        # Note that we want to use the import lock here - the app loading is
        # in many cases initiated implicitly by importing, and thus it is
        # possible to end up in deadlock when one thread initiates loading
        # without holding the importer lock and another thread then tries to
        # import something which also launches the app loading. For details of
        # this situation see #18251.
        with import_lock():
            if self.loaded:
                return
            for app_name in settings.INSTALLED_APPS:
                if app_name in self.handled:
                    continue
                self.load_app(app_name, can_postpone=True)
            if not self.nesting_level:
                for app_name in self.postponed:
                    self.load_app(app_name)
                self.loaded = True

    def load_app(self, app_name, can_postpone=False):
        """
        Loads the app with the provided fully qualified name, and returns the
        model module.
        """
        app_module = import_module(app_name)
        self.handled.add(app_name)
        self.nesting_level += 1
        try:
            models_module = import_module('%s.%s' % (app_name, MODELS_MODULE_NAME))
        except ImportError:
            # If the app doesn't have a models module, we can just swallow the
            # ImportError and return no models for this app.
            if not module_has_submodule(app_module, MODELS_MODULE_NAME):
                models_module = None
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
                    return
                else:
                    raise
        finally:
            self.nesting_level -= 1

        app_config = AppConfig(app_name, app_module, models_module)
        app_config.models = self.all_models[app_config.label]
        self.app_configs[app_config.label] = app_config

        return models_module

    def app_cache_ready(self):
        """
        Returns true if the model cache is fully populated.

        Useful for code that wants to cache the results of get_models() for
        themselves once it is safe to do so.
        """
        return self.loaded

    def get_app_configs(self, only_with_models_module=False):
        """
        Return an iterable of application configurations.

        If only_with_models_module in True (non-default), only applications
        containing a models module are considered.
        """
        self.populate()
        for app_config in self.app_configs.values():
            if only_with_models_module and app_config.models_module is None:
                continue
            if self.available_apps is not None and app_config.name not in self.available_apps:
                continue
            yield app_config

    def get_app_config(self, app_label, only_with_models_module=False):
        """
        Returns the application configuration for the given app_label.

        Raises LookupError if no application exists with this app_label.

        Raises UnavailableApp when set_available_apps() disables the
        application with this app_label.

        If only_with_models_module in True (non-default), only applications
        containing a models module are considered.
        """
        self.populate()
        app_config = self.app_configs.get(app_label)
        if app_config is None:
            raise LookupError("No installed app with label %r." % app_label)
        if only_with_models_module and app_config.models_module is None:
            raise LookupError("App with label %r doesn't have a models module." % app_label)
        if self.available_apps is not None and app_config.name not in self.available_apps:
            raise UnavailableApp("App with label %r isn't available." % app_label)
        return app_config

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
        if not self.master:
            only_installed = False
        cache_key = (app_mod, include_auto_created, include_deferred, only_installed, include_swapped)
        model_list = None
        try:
            model_list = self._get_models_cache[cache_key]
            if self.available_apps is not None and only_installed:
                model_list = [
                    m for m in model_list
                    if self.app_configs[m._meta.app_label].name in self.available_apps
                ]
            return model_list
        except KeyError:
            pass
        self.populate()
        if app_mod:
            app_label = app_mod.__name__.split('.')[-2]
            if only_installed:
                try:
                    model_dicts = [self.app_configs[app_label].models]
                except KeyError:
                    model_dicts = []
            else:
                model_dicts = [self.all_models[app_label]]
        else:
            if only_installed:
                model_dicts = [app_config.models for app_config in self.app_configs.values()]
            else:
                model_dicts = self.all_models.values()
        model_list = []
        for model_dict in model_dicts:
            model_list.extend(
                model for model in model_dict.values()
                if ((not model._deferred or include_deferred) and
                    (not model._meta.auto_created or include_auto_created) and
                    (not model._meta.swapped or include_swapped))
            )
        self._get_models_cache[cache_key] = model_list
        if self.available_apps is not None and only_installed:
            model_list = [
                m for m in model_list
                if self.app_configs[m._meta.app_label].name in self.available_apps
            ]
        return model_list

    def get_model(self, app_label, model_name, only_installed=True):
        """
        Returns the model matching the given app_label and case-insensitive
        model_name.

        Returns None if no model is found.

        Raises UnavailableApp when set_available_apps() in in effect and
        doesn't include app_label.
        """
        if not self.master:
            only_installed = False
        self.populate()
        if only_installed:
            app_config = self.app_configs.get(app_label)
            if app_config is None:
                return None
            if (self.available_apps is not None
                    and app_config.name not in self.available_apps):
                raise UnavailableApp("App with label %s isn't available." % app_label)
        return self.all_models[app_label].get(model_name.lower())

    def register_model(self, app_label, model):
        # Since this method is called when models are imported, it cannot
        # perform imports because of the risk of import loops. It mustn't
        # call get_app_config().
        model_name = model._meta.model_name
        models = self.all_models[app_label]
        if model_name in models:
            # The same model may be imported via different paths (e.g.
            # appname.models and project.appname.models). We use the source
            # filename as a means to detect identity.
            fname1 = os.path.abspath(upath(sys.modules[model.__module__].__file__))
            fname2 = os.path.abspath(upath(sys.modules[models[model_name].__module__].__file__))
            # Since the filename extension could be .py the first time and
            # .pyc or .pyo the second time, ignore the extension when
            # comparing.
            if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                return
        models[model_name] = model
        self._get_models_cache.clear()

    def registered_model(self, app_label, model_name):
        """
        Test if a model is registered and return the model class or None.

        It's safe to call this method at import time, even while the app cache
        is being populated.
        """
        return self.all_models[app_label].get(model_name.lower())

    def set_available_apps(self, available):
        available = set(available)
        installed = set(settings.INSTALLED_APPS)
        if not available.issubset(installed):
            raise ValueError("Available apps isn't a subset of installed "
                "apps, extra apps: %s" % ", ".join(available - installed))
        self.available_apps = available

    def unset_available_apps(self):
        self.available_apps = None

    ### DANGEROUS METHODS ### (only used to preserve existing tests)

    def _begin_with_app(self, app_name):
        # Returns an opaque value that can be passed to _end_with_app().
        app_module = import_module(app_name)
        models_module = import_module('%s.models' % app_name)
        app_config = AppConfig(app_name, app_module, models_module)
        if app_config.label in self.app_configs:
            return None
        else:
            app_config.models = self.all_models[app_config.label]
            self.app_configs[app_config.label] = app_config
            return app_config

    def _end_with_app(self, app_config):
        if app_config is not None:
            del self.app_configs[app_config.label]

    @contextmanager
    def _with_app(self, app_name):
        app_config = self._begin_with_app(app_name)
        try:
            yield
        finally:
            self._end_with_app(app_config)

    def _begin_without_app(self, app_name):
        # Returns an opaque value that can be passed to _end_without_app().
        return self.app_configs.pop(app_name.rpartition(".")[2], None)

    def _end_without_app(self, app_config):
        if app_config is not None:
            self.app_configs[app_config.label] = app_config

    @contextmanager
    def _without_app(self, app_name):
        app_config = self._begin_without_app(app_name)
        try:
            yield
        finally:
            self._end_without_app(app_config)

    def _begin_empty(self):
        app_configs, self.app_configs = self.app_configs, OrderedDict()
        return app_configs

    def _end_empty(self, app_configs):
        self.app_configs = app_configs

    @contextmanager
    def _empty(self):
        app_configs = self._begin_empty()
        try:
            yield
        finally:
            self._end_empty(app_configs)

    ### DEPRECATED METHODS GO BELOW THIS LINE ###

    def get_app(self, app_label):
        """
        Returns the module containing the models for the given app_label.

        Raises UnavailableApp when set_available_apps() in in effect and
        doesn't include app_label.
        """
        warnings.warn(
            "get_app_config(app_label).models_module supersedes get_app(app_label).",
            PendingDeprecationWarning, stacklevel=2)
        try:
            return self.get_app_config(app_label).models_module
        except LookupError as exc:
            # Change the exception type for backwards compatibility.
            raise ImproperlyConfigured(*exc.args)

    def get_apps(self):
        """
        Returns a list of all installed modules that contain models.
        """
        warnings.warn(
            "[a.models_module for a in get_app_configs()] supersedes get_apps().",
            PendingDeprecationWarning, stacklevel=2)
        return [app_config.models_module for app_config in self.get_app_configs()]

    def _get_app_package(self, app):
        return '.'.join(app.__name__.split('.')[:-1])

    def get_app_package(self, app_label):
        warnings.warn(
            "get_app_config(label).name supersedes get_app_package(label).",
            PendingDeprecationWarning, stacklevel=2)
        return self._get_app_package(self.get_app(app_label))

    def _get_app_path(self, app):
        if hasattr(app, '__path__'):        # models/__init__.py package
            app_path = app.__path__[0]
        else:                               # models.py module
            app_path = app.__file__
        return os.path.dirname(upath(app_path))

    def get_app_path(self, app_label):
        warnings.warn(
            "get_app_config(label).path supersedes get_app_path(label).",
            PendingDeprecationWarning, stacklevel=2)
        return self._get_app_path(self.get_app(app_label))

    def get_app_paths(self):
        """
        Returns a list of paths to all installed apps.

        Useful for discovering files at conventional locations inside apps
        (static files, templates, etc.)
        """
        warnings.warn(
            "[a.path for a in get_app_configs()] supersedes get_app_paths().",
            PendingDeprecationWarning, stacklevel=2)

        self.populate()

        app_paths = []
        for app in self.get_apps():
            app_paths.append(self._get_app_path(app))
        return app_paths

    def register_models(self, app_label, *models):
        """
        Register a set of models as belonging to an app.
        """
        warnings.warn(
            "register_models(app_label, models) is deprecated.",
            PendingDeprecationWarning, stacklevel=2)
        for model in models:
            self.register_model(app_label, model)


app_cache = AppCache(master=True)
