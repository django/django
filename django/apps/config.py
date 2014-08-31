from importlib import import_module
import os
import types

from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.utils.module_loading import module_has_submodule
from django.utils._os import upath


MODELS_MODULE_NAME = 'models'


class AppConfig(object):
    """
    Class representing a Django application and its configuration.
    """

    def __init__(self, app_name, app_module):
        # Full Python path to the application eg. 'django.contrib.admin'.
        self.name = app_name

        # Root module for the application eg. <module 'django.contrib.admin'
        # from 'django/contrib/admin/__init__.pyc'>.
        self.module = app_module

        # The following attributes could be defined at the class level in a
        # subclass, hence the test-and-set pattern.

        # Last component of the Python path to the application eg. 'admin'.
        # This value must be unique across a Django project.
        if not hasattr(self, 'label'):
            self.label = app_name.rpartition(".")[2]

        # Human-readable name for the application eg. "Admin".
        if not hasattr(self, 'verbose_name'):
            self.verbose_name = self.label.title()

        # Filesystem path to the application directory eg.
        # u'/usr/lib/python2.7/dist-packages/django/contrib/admin'. Unicode on
        # Python 2 and a str on Python 3.
        if not hasattr(self, 'path'):
            self.path = self._path_from_module(app_module)

        # Module containing models eg. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.pyc'>. Set by import_models().
        # None if the application doesn't have a models module.
        self.models_module = None

        # Mapping of lower case model names to model classes. Initially set to
        # None to prevent accidental access before import_models() runs.
        self.models = None

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.label)

    def _path_from_module(self, module):
        """Attempt to determine app's filesystem path from its module."""
        # See #21874 for extended discussion of the behavior of this method in
        # various cases.
        # Convert paths to list because Python 3.3 _NamespacePath does not
        # support indexing.
        paths = list(getattr(module, '__path__', []))
        if len(paths) != 1:
            filename = getattr(module, '__file__', None)
            if filename is not None:
                paths = [os.path.dirname(filename)]
        if len(paths) > 1:
            raise ImproperlyConfigured(
                "The app module %r has multiple filesystem locations (%r); "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % (module, paths))
        elif not paths:
            raise ImproperlyConfigured(
                "The app module %r has no filesystem location, "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % (module,))
        return upath(paths[0])

    @classmethod
    def create(cls, entry):
        """
        Factory that creates an app config from an entry in INSTALLED_APPS.
        """
        mod_path, _, ending = entry.rpartition('.')

        if not mod_path:
            # single-level module
            mod_path = ending

        # Attempt to import mod_path by itself. If this fails, the exception
        # should propagate up (nothing else can be done at that point).

        module = import_module(mod_path)

        obj = getattr(module, ending, None)

        if not obj or isinstance(obj, types.ModuleType):
            # Either the path ending is a module, or the given object doesn't
            # exist. Either way we need to perform an import here to allow
            # import-time exceptions to propagate
            module = import_module(entry)

            if not hasattr(module, 'default_app_config'):
                # This is a plain module entry, so create a default AppConfig
                return cls(entry, module)

            # otherwise, import the module path given in default_app_config
            entry = module.default_app_config
            mod_path, _, cls_name = entry.rpartition('.')
            module = import_module(mod_path)
        else:
            # if it is an attribute, we can assume it's an AppConfig class
            cls_name = ending

        # We now know that entry *should* be a <mod_path>.<cls_name>.
        # At this point we should allow AttributeError to propagate as normal
        # if the given class doesn't exist.
        cls = getattr(module, cls_name)

        # Check for obvious errors. (This check prevents duck typing, but
        # it could be removed if it became a problem in practice.)
        if not issubclass(cls, AppConfig):
            raise ImproperlyConfigured(
                "'%s' isn't a subclass of AppConfig." % entry)

        # Obtain app name here rather than in AppClass.__init__ to keep
        # all error checking for entries in INSTALLED_APPS in one place.
        try:
            app_name = cls.name
        except AttributeError:
            raise ImproperlyConfigured(
                "'%s' must supply a name attribute." % entry)

        # Ensure app_name points to a valid module.
        app_module = import_module(app_name)

        # Entry is a path to an app config class.
        return cls(app_name, app_module)

    def check_models_ready(self):
        """
        Raises an exception if models haven't been imported yet.
        """
        if self.models is None:
            raise AppRegistryNotReady(
                "Models for app '%s' haven't been imported yet." % self.label)

    def get_model(self, model_name):
        """
        Returns the model with the given case-insensitive model_name.

        Raises LookupError if no model exists with this name.
        """
        self.check_models_ready()
        try:
            return self.models[model_name.lower()]
        except KeyError:
            raise LookupError(
                "App '%s' doesn't have a '%s' model." % (self.label, model_name))

    def get_models(self, include_auto_created=False,
                   include_deferred=False, include_swapped=False):
        """
        Returns an iterable of models.

        By default, the following models aren't included:

        - auto-created models for many-to-many relations without
          an explicit intermediate table,
        - models created to satisfy deferred attribute queries,
        - models that have been swapped out.

        Set the corresponding keyword argument to True to include such models.
        Keyword arguments aren't documented; they're a private API.
        """
        self.check_models_ready()
        for model in self.models.values():
            if model._deferred and not include_deferred:
                continue
            if model._meta.auto_created and not include_auto_created:
                continue
            if model._meta.swapped and not include_swapped:
                continue
            yield model

    def import_models(self, all_models):
        # Dictionary of models for this app, primarily maintained in the
        # 'all_models' attribute of the Apps this AppConfig is attached to.
        # Injected as a parameter because it gets populated when models are
        # imported, which might happen before populate() imports models.
        self.models = all_models

        if module_has_submodule(self.module, MODELS_MODULE_NAME):
            models_module_name = '%s.%s' % (self.name, MODELS_MODULE_NAME)
            self.models_module = import_module(models_module_name)

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
