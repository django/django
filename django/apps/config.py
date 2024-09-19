import inspect
import os
from importlib import import_module
from typing import Any, Dict, Iterable, List, Optional, Type

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.module_loading import import_string, module_has_submodule

APPS_MODULE_NAME = "apps"
MODELS_MODULE_NAME = "models"


class AppConfig:
    """Class representing a Django application and its configuration."""

    name: str
    module: Any
    apps: Any
    label: str
    verbose_name: str
    path: str
    models_module: Optional[Any]
    models: Optional[Dict[str, Any]]

    def __init__(self, app_name: str, app_module: Any) -> None:
        # Full Python path to the application e.g. 'django.contrib.admin'.
        self.name = app_name

        # Root module for the application e.g. <module 'django.contrib.admin'
        # from 'django/contrib/admin/__init__.py'>.
        self.module = app_module

        # Reference to the Apps registry that holds this AppConfig. Set by the
        # registry when it registers the AppConfig instance.
        self.apps = None

        # The following attributes could be defined at the class level in a
        # subclass, hence the test-and-set pattern.

        # Last component of the Python path to the application e.g. 'admin'.
        # This value must be unique across a Django project.
        if not hasattr(self, "label"):
            self.label = app_name.rpartition(".")[2]
        if not self.label.isidentifier():
            raise ImproperlyConfigured(
                f"The app label '{self.label}' is not a valid Python identifier."
            )

        # Human-readable name for the application e.g. "Admin".
        if not hasattr(self, "verbose_name"):
            self.verbose_name = self.label.title()

        # Filesystem path to the application directory e.g.
        # '/path/to/django/contrib/admin'.
        if not hasattr(self, "path"):
            self.path = self._path_from_module(app_module)

        # Module containing models e.g. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.py'>. Set by import_models().
        # None if the application doesn't have a models module.
        self.models_module = None

        # Mapping of lowercase model names to model classes. Initially set to
        # None to prevent accidental access before import_models() runs.
        self.models = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.label}>"

    @cached_property
    def default_auto_field(self) -> str:
        from django.conf import settings

        return settings.DEFAULT_AUTO_FIELD

    @property
    def _is_default_auto_field_overridden(self) -> bool:
        return self.__class__.default_auto_field is not AppConfig.default_auto_field

    def _path_from_module(self, module: Any) -> str:
        """Attempt to determine app's filesystem path from its module."""
        # See #21874 for extended discussion of the behavior of this method in
        # various cases.
        # Convert to list because __path__ may not support indexing.
        paths = list(getattr(module, "__path__", []))
        if len(paths) != 1:
            filename = getattr(module, "__file__", None)
            if filename is not None:
                paths = [os.path.dirname(filename)]
            else:
                # For unknown reasons, sometimes the list returned by __path__
                # contains duplicates that must be removed (#25246).
                paths = list(set(paths))
        if len(paths) > 1:
            raise ImproperlyConfigured(
                f"The app module {module!r} has multiple filesystem locations ({paths!r}); "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute."
            )
        elif not paths:
            raise ImproperlyConfigured(
                f"The app module {module!r} has no filesystem location; "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute."
            )
        return paths[0]

    @classmethod
    def create(cls, entry: str) -> 'AppConfig':
        """
        Factory that creates an app config from an entry in INSTALLED_APPS.
        """
        app_config_class: Optional[Type['AppConfig']] = None
        app_name: Optional[str] = None
        app_module: Optional[Any] = None

        # Try to import the app module.
        try:
            app_module = import_module(entry)
        except Exception:
            pass
        else:
            app_config_class = cls._find_default_app_config(entry, app_module)

            # Use the default app config class if none was found.
            if app_config_class is None:
                app_config_class = cls
                app_name = entry

        # If importing the app module failed, try to import an AppConfig class.
        if app_config_class is None:
            try:
                app_config_class = import_string(entry)
            except Exception:
                pass

        # If both imports failed, raise an error.
        if app_module is None and app_config_class is None:
            cls._handle_import_error(entry)

        # Ensure the app_config_class is a subclass of AppConfig.
        if not issubclass(app_config_class, AppConfig):
            raise ImproperlyConfigured(f"'{entry}' isn't a subclass of AppConfig.")

        # Obtain app name.
        if app_name is None:
            try:
                app_name = app_config_class.name
            except AttributeError:
                raise ImproperlyConfigured(f"'{entry}' must supply a name attribute.")

        # Ensure app_name points to a valid module.
        try:
            app_module = import_module(app_name)
        except ImportError:
            raise ImproperlyConfigured(
                f"Cannot import '{app_name}'. Check that '{app_config_class.__module__}.{app_config_class.__qualname__}.name' is correct."
            )

        return app_config_class(app_name, app_module)

    @classmethod
    def _find_default_app_config(cls, entry: str, app_module: Any) -> Optional[Type['AppConfig']]:
        """
        Find the default AppConfig class in the app's 'apps' submodule.
        """
        if module_has_submodule(app_module, APPS_MODULE_NAME):
            mod_path = f"{entry}.{APPS_MODULE_NAME}"
            mod = import_module(mod_path)
            # Find AppConfig candidates excluding those with default = False.
            app_configs = [
                candidate for _, candidate in inspect.getmembers(mod, inspect.isclass)
                if issubclass(candidate, cls) and candidate is not cls and getattr(candidate, "default", True)
            ]
            if len(app_configs) == 1:
                return app_configs[0]
            else:
                # Find AppConfig candidates with default = True.
                default_configs = [
                    candidate for candidate in app_configs if getattr(candidate, "default", False)
                ]
                if len(default_configs) > 1:
                    candidates = [candidate.__name__ for candidate in default_configs]
                    raise RuntimeError(
                        f"{mod_path!r} declares more than one default AppConfig: {', '.join(candidates)}."
                    )
                elif default_configs:
                    return default_configs[0]
        return None

    @classmethod
    def _handle_import_error(cls, entry: str) -> None:
        """
        Handle import errors by providing informative error messages.
        """
        mod_path, _, cls_name = entry.rpartition(".")
        if mod_path and cls_name[0].isupper():
            # Likely intended to be an AppConfig class.
            mod = import_module(mod_path)
            candidates = [
                name for name, candidate in inspect.getmembers(mod, inspect.isclass)
                if issubclass(candidate, cls) and candidate is not cls
            ]
            msg = f"Module '{mod_path}' does not contain a '{cls_name}' class."
            if candidates:
                msg += f" Choices are: {', '.join(candidates)}."
            raise ImportError(msg)
        else:
            # Re-trigger the module import exception.
            import_module(entry)

    def get_model(self, model_name: str, require_ready: bool = True) -> Any:
        """
        Return the model with the given case-insensitive model_name.

        Raise LookupError if no model exists with this name.
        """
        if require_ready:
            self.apps.check_models_ready()
        else:
            self.apps.check_apps_ready()
        try:
            return self.models[model_name.lower()]
        except KeyError:
            raise LookupError(f"App '{self.label}' doesn't have a '{model_name}' model.")

    def get_models(
        self, include_auto_created: bool = False, include_swapped: bool = False
    ) -> Iterable[Any]:
        """
        Return an iterable of models.

        By default, the following models aren't included:

        - auto-created models for many-to-many relations without
          an explicit intermediate table,
        - models that have been swapped out.

        Set the corresponding keyword argument to True to include such models.
        """
        self.apps.check_models_ready()
        for model in self.models.values():
            if model._meta.auto_created and not include_auto_created:
                continue
            if model._meta.swapped and not include_swapped:
                continue
            yield model

    def import_models(self) -> None:
        """
        Import the models module for the app and populate the models dictionary.
        """
        self.models = self.apps.all_models[self.label]

        if module_has_submodule(self.module, MODELS_MODULE_NAME):
            models_module_name = f"{self.name}.{MODELS_MODULE_NAME}"
            self.models_module = import_module(models_module_name)

    def ready(self) -> None:
        """
        Override this method in subclasses to run code when Django starts.
        """
        pass
