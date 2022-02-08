import os

from django.apps import AppConfig, apps
from django.apps.registry import Apps
from django.contrib.admin.models import LogEntry
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.test.utils import extend_sys_path, isolate_apps
from django.utils.deprecation import RemovedInDjango41Warning

from .explicit_default_config_app.apps import ExplicitDefaultConfig
from .explicit_default_config_empty_apps import ExplicitDefaultConfigEmptyApps
from .explicit_default_config_mismatch_app.not_apps import ExplicitDefaultConfigMismatch
from .explicit_default_config_without_apps import ExplicitDefaultConfigWithoutApps
from .models import SoAlternative, TotallyNormal, new_apps
from .one_config_app.apps import OneConfig
from .two_configs_one_default_app.apps import TwoConfig

# Small list with a variety of cases for tests that iterate on installed apps.
# Intentionally not in alphabetical order to check if the order is preserved.

SOME_INSTALLED_APPS = [
    "apps.apps.MyAdmin",
    "apps.apps.MyAuth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

SOME_INSTALLED_APPS_NAMES = [
    "django.contrib.admin",
    "django.contrib.auth",
] + SOME_INSTALLED_APPS[2:]

HERE = os.path.dirname(__file__)


class AppsTests(SimpleTestCase):
    def test_singleton_master(self):
        """
        Only one master registry can exist.
        """
        with self.assertRaises(RuntimeError):
            Apps(installed_apps=None)

    def test_ready(self):
        """
        Tests the ready property of the master registry.
        """
        # The master app registry is always ready when the tests run.
        self.assertIs(apps.ready, True)
        # Non-master app registries are populated in __init__.
        self.assertIs(Apps().ready, True)
        # The condition is set when apps are ready
        self.assertIs(apps.ready_event.is_set(), True)
        self.assertIs(Apps().ready_event.is_set(), True)

    def test_bad_app_config(self):
        """
        Tests when INSTALLED_APPS contains an incorrect app config.
        """
        msg = "'apps.apps.BadConfig' must supply a name attribute."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            with self.settings(INSTALLED_APPS=["apps.apps.BadConfig"]):
                pass

    def test_not_an_app_config(self):
        """
        Tests when INSTALLED_APPS contains a class that isn't an app config.
        """
        msg = "'apps.apps.NotAConfig' isn't a subclass of AppConfig."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            with self.settings(INSTALLED_APPS=["apps.apps.NotAConfig"]):
                pass

    def test_no_such_app(self):
        """
        Tests when INSTALLED_APPS contains an app that doesn't exist, either
        directly or via an app config.
        """
        with self.assertRaises(ImportError):
            with self.settings(INSTALLED_APPS=["there is no such app"]):
                pass
        msg = (
            "Cannot import 'there is no such app'. Check that "
            "'apps.apps.NoSuchApp.name' is correct."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            with self.settings(INSTALLED_APPS=["apps.apps.NoSuchApp"]):
                pass

    def test_no_such_app_config(self):
        msg = "Module 'apps' does not contain a 'NoSuchConfig' class."
        with self.assertRaisesMessage(ImportError, msg):
            with self.settings(INSTALLED_APPS=["apps.NoSuchConfig"]):
                pass

    def test_no_such_app_config_with_choices(self):
        msg = (
            "Module 'apps.apps' does not contain a 'NoSuchConfig' class. "
            "Choices are: 'BadConfig', 'ModelPKAppsConfig', 'MyAdmin', "
            "'MyAuth', 'NoSuchApp', 'PlainAppsConfig', 'RelabeledAppsConfig'."
        )
        with self.assertRaisesMessage(ImportError, msg):
            with self.settings(INSTALLED_APPS=["apps.apps.NoSuchConfig"]):
                pass

    def test_no_config_app(self):
        """Load an app that doesn't provide an AppConfig class."""
        with self.settings(INSTALLED_APPS=["apps.no_config_app"]):
            config = apps.get_app_config("no_config_app")
        self.assertIsInstance(config, AppConfig)

    def test_one_config_app(self):
        """Load an app that provides an AppConfig class."""
        with self.settings(INSTALLED_APPS=["apps.one_config_app"]):
            config = apps.get_app_config("one_config_app")
        self.assertIsInstance(config, OneConfig)

    def test_two_configs_app(self):
        """Load an app that provides two AppConfig classes."""
        with self.settings(INSTALLED_APPS=["apps.two_configs_app"]):
            config = apps.get_app_config("two_configs_app")
        self.assertIsInstance(config, AppConfig)

    def test_two_default_configs_app(self):
        """Load an app that provides two default AppConfig classes."""
        msg = (
            "'apps.two_default_configs_app.apps' declares more than one "
            "default AppConfig: 'TwoConfig', 'TwoConfigBis'."
        )
        with self.assertRaisesMessage(RuntimeError, msg):
            with self.settings(INSTALLED_APPS=["apps.two_default_configs_app"]):
                pass

    def test_two_configs_one_default_app(self):
        """
        Load an app that provides two AppConfig classes, one being the default.
        """
        with self.settings(INSTALLED_APPS=["apps.two_configs_one_default_app"]):
            config = apps.get_app_config("two_configs_one_default_app")
        self.assertIsInstance(config, TwoConfig)

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_configs(self):
        """
        Tests apps.get_app_configs().
        """
        app_configs = apps.get_app_configs()
        self.assertEqual(
            [app_config.name for app_config in app_configs], SOME_INSTALLED_APPS_NAMES
        )

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_config(self):
        """
        Tests apps.get_app_config().
        """
        app_config = apps.get_app_config("admin")
        self.assertEqual(app_config.name, "django.contrib.admin")

        app_config = apps.get_app_config("staticfiles")
        self.assertEqual(app_config.name, "django.contrib.staticfiles")

        with self.assertRaises(LookupError):
            apps.get_app_config("admindocs")

        msg = "No installed app with label 'django.contrib.auth'. Did you mean 'myauth'"
        with self.assertRaisesMessage(LookupError, msg):
            apps.get_app_config("django.contrib.auth")

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_is_installed(self):
        """
        Tests apps.is_installed().
        """
        self.assertIs(apps.is_installed("django.contrib.admin"), True)
        self.assertIs(apps.is_installed("django.contrib.auth"), True)
        self.assertIs(apps.is_installed("django.contrib.staticfiles"), True)
        self.assertIs(apps.is_installed("django.contrib.admindocs"), False)

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_model(self):
        """
        Tests apps.get_model().
        """
        self.assertEqual(apps.get_model("admin", "LogEntry"), LogEntry)
        with self.assertRaises(LookupError):
            apps.get_model("admin", "LogExit")

        # App label is case-sensitive, Model name is case-insensitive.
        self.assertEqual(apps.get_model("admin", "loGentrY"), LogEntry)
        with self.assertRaises(LookupError):
            apps.get_model("Admin", "LogEntry")

        # A single argument is accepted.
        self.assertEqual(apps.get_model("admin.LogEntry"), LogEntry)
        with self.assertRaises(LookupError):
            apps.get_model("admin.LogExit")
        with self.assertRaises(ValueError):
            apps.get_model("admin_LogEntry")

    @override_settings(INSTALLED_APPS=["apps.apps.RelabeledAppsConfig"])
    def test_relabeling(self):
        self.assertEqual(apps.get_app_config("relabeled").name, "apps")

    def test_duplicate_labels(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured, "Application labels aren't unique"
        ):
            with self.settings(INSTALLED_APPS=["apps.apps.PlainAppsConfig", "apps"]):
                pass

    def test_duplicate_names(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured, "Application names aren't unique"
        ):
            with self.settings(
                INSTALLED_APPS=["apps.apps.RelabeledAppsConfig", "apps"]
            ):
                pass

    def test_import_exception_is_not_masked(self):
        """
        App discovery should preserve stack traces. Regression test for #22920.
        """
        with self.assertRaisesMessage(ImportError, "Oops"):
            with self.settings(INSTALLED_APPS=["import_error_package"]):
                pass

    def test_models_py(self):
        """
        The models in the models.py file were loaded correctly.
        """
        self.assertEqual(apps.get_model("apps", "TotallyNormal"), TotallyNormal)
        with self.assertRaises(LookupError):
            apps.get_model("apps", "SoAlternative")

        with self.assertRaises(LookupError):
            new_apps.get_model("apps", "TotallyNormal")
        self.assertEqual(new_apps.get_model("apps", "SoAlternative"), SoAlternative)

    def test_models_not_loaded(self):
        """
        apps.get_models() raises an exception if apps.models_ready isn't True.
        """
        apps.models_ready = False
        try:
            # The cache must be cleared to trigger the exception.
            apps.get_models.cache_clear()
            with self.assertRaisesMessage(
                AppRegistryNotReady, "Models aren't loaded yet."
            ):
                apps.get_models()
        finally:
            apps.models_ready = True

    def test_dynamic_load(self):
        """
        Makes a new model at runtime and ensures it goes into the right place.
        """
        old_models = list(apps.get_app_config("apps").get_models())
        # Construct a new model in a new app registry
        body = {}
        new_apps = Apps(["apps"])
        meta_contents = {
            "app_label": "apps",
            "apps": new_apps,
        }
        meta = type("Meta", (), meta_contents)
        body["Meta"] = meta
        body["__module__"] = TotallyNormal.__module__
        temp_model = type("SouthPonies", (models.Model,), body)
        # Make sure it appeared in the right place!
        self.assertEqual(list(apps.get_app_config("apps").get_models()), old_models)
        with self.assertRaises(LookupError):
            apps.get_model("apps", "SouthPonies")
        self.assertEqual(new_apps.get_model("apps", "SouthPonies"), temp_model)

    def test_model_clash(self):
        """
        Test for behavior when two models clash in the app registry.
        """
        new_apps = Apps(["apps"])
        meta_contents = {
            "app_label": "apps",
            "apps": new_apps,
        }

        body = {}
        body["Meta"] = type("Meta", (), meta_contents)
        body["__module__"] = TotallyNormal.__module__
        type("SouthPonies", (models.Model,), body)

        # When __name__ and __module__ match we assume the module
        # was reloaded and issue a warning. This use-case is
        # useful for REPL. Refs #23621.
        body = {}
        body["Meta"] = type("Meta", (), meta_contents)
        body["__module__"] = TotallyNormal.__module__
        msg = (
            "Model 'apps.southponies' was already registered. "
            "Reloading models is not advised as it can lead to inconsistencies, "
            "most notably with related models."
        )
        with self.assertRaisesMessage(RuntimeWarning, msg):
            type("SouthPonies", (models.Model,), body)

        # If it doesn't appear to be a reloaded module then we expect
        # a RuntimeError.
        body = {}
        body["Meta"] = type("Meta", (), meta_contents)
        body["__module__"] = TotallyNormal.__module__ + ".whatever"
        with self.assertRaisesMessage(
            RuntimeError, "Conflicting 'southponies' models in application 'apps':"
        ):
            type("SouthPonies", (models.Model,), body)

    def test_get_containing_app_config_apps_not_ready(self):
        """
        apps.get_containing_app_config() should raise an exception if
        apps.apps_ready isn't True.
        """
        apps.apps_ready = False
        try:
            with self.assertRaisesMessage(
                AppRegistryNotReady, "Apps aren't loaded yet"
            ):
                apps.get_containing_app_config("foo")
        finally:
            apps.apps_ready = True

    @isolate_apps("apps", kwarg_name="apps")
    def test_lazy_model_operation(self, apps):
        """
        Tests apps.lazy_model_operation().
        """
        model_classes = []
        initial_pending = set(apps._pending_operations)

        def test_func(*models):
            model_classes[:] = models

        class LazyA(models.Model):
            pass

        # Test models appearing twice, and models appearing consecutively
        model_keys = [
            ("apps", model_name)
            for model_name in ["lazya", "lazyb", "lazyb", "lazyc", "lazya"]
        ]
        apps.lazy_model_operation(test_func, *model_keys)

        # LazyModelA shouldn't be waited on since it's already registered,
        # and LazyModelC shouldn't be waited on until LazyModelB exists.
        self.assertEqual(
            set(apps._pending_operations) - initial_pending, {("apps", "lazyb")}
        )

        # Multiple operations can wait on the same model
        apps.lazy_model_operation(test_func, ("apps", "lazyb"))

        class LazyB(models.Model):
            pass

        self.assertEqual(model_classes, [LazyB])

        # Now we are just waiting on LazyModelC.
        self.assertEqual(
            set(apps._pending_operations) - initial_pending, {("apps", "lazyc")}
        )

        class LazyC(models.Model):
            pass

        # Everything should be loaded - make sure the callback was executed properly.
        self.assertEqual(model_classes, [LazyA, LazyB, LazyB, LazyC, LazyA])


class Stub:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AppConfigTests(SimpleTestCase):
    """Unit tests for AppConfig class."""

    def test_path_set_explicitly(self):
        """If subclass sets path as class attr, no module attributes needed."""

        class MyAppConfig(AppConfig):
            path = "foo"

        ac = MyAppConfig("label", Stub())

        self.assertEqual(ac.path, "foo")

    def test_explicit_path_overrides(self):
        """If path set as class attr, overrides __path__ and __file__."""

        class MyAppConfig(AppConfig):
            path = "foo"

        ac = MyAppConfig("label", Stub(__path__=["a"], __file__="b/__init__.py"))

        self.assertEqual(ac.path, "foo")

    def test_dunder_path(self):
        """If single element in __path__, use it (in preference to __file__)."""
        ac = AppConfig("label", Stub(__path__=["a"], __file__="b/__init__.py"))

        self.assertEqual(ac.path, "a")

    def test_no_dunder_path_fallback_to_dunder_file(self):
        """If there is no __path__ attr, use __file__."""
        ac = AppConfig("label", Stub(__file__="b/__init__.py"))

        self.assertEqual(ac.path, "b")

    def test_empty_dunder_path_fallback_to_dunder_file(self):
        """If the __path__ attr is empty, use __file__ if set."""
        ac = AppConfig("label", Stub(__path__=[], __file__="b/__init__.py"))

        self.assertEqual(ac.path, "b")

    def test_multiple_dunder_path_fallback_to_dunder_file(self):
        """If the __path__ attr is length>1, use __file__ if set."""
        ac = AppConfig("label", Stub(__path__=["a", "b"], __file__="c/__init__.py"))

        self.assertEqual(ac.path, "c")

    def test_no_dunder_path_or_dunder_file(self):
        """If there is no __path__ or __file__, raise ImproperlyConfigured."""
        with self.assertRaises(ImproperlyConfigured):
            AppConfig("label", Stub())

    def test_empty_dunder_path_no_dunder_file(self):
        """If the __path__ attr is empty and there is no __file__, raise."""
        with self.assertRaises(ImproperlyConfigured):
            AppConfig("label", Stub(__path__=[]))

    def test_multiple_dunder_path_no_dunder_file(self):
        """If the __path__ attr is length>1 and there is no __file__, raise."""
        with self.assertRaises(ImproperlyConfigured):
            AppConfig("label", Stub(__path__=["a", "b"]))

    def test_duplicate_dunder_path_no_dunder_file(self):
        """
        If the __path__ attr contains duplicate paths and there is no
        __file__, they duplicates should be deduplicated (#25246).
        """
        ac = AppConfig("label", Stub(__path__=["a", "a"]))
        self.assertEqual(ac.path, "a")

    def test_repr(self):
        ac = AppConfig("label", Stub(__path__=["a"]))
        self.assertEqual(repr(ac), "<AppConfig: label>")

    def test_invalid_label(self):
        class MyAppConfig(AppConfig):
            label = "invalid.label"

        msg = "The app label 'invalid.label' is not a valid Python identifier."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            MyAppConfig("test_app", Stub())

    @override_settings(
        INSTALLED_APPS=["apps.apps.ModelPKAppsConfig"],
        DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField",
    )
    def test_app_default_auto_field(self):
        apps_config = apps.get_app_config("apps")
        self.assertEqual(
            apps_config.default_auto_field,
            "django.db.models.BigAutoField",
        )
        self.assertIs(apps_config._is_default_auto_field_overridden, True)

    @override_settings(
        INSTALLED_APPS=["apps.apps.PlainAppsConfig"],
        DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField",
    )
    def test_default_auto_field_setting(self):
        apps_config = apps.get_app_config("apps")
        self.assertEqual(
            apps_config.default_auto_field,
            "django.db.models.SmallAutoField",
        )
        self.assertIs(apps_config._is_default_auto_field_overridden, False)


class NamespacePackageAppTests(SimpleTestCase):
    # We need nsapp to be top-level so our multiple-paths tests can add another
    # location for it (if its inside a normal package with an __init__.py that
    # isn't possible). In order to avoid cluttering the already-full tests/ dir
    # (which is on sys.path), we add these new entries to sys.path temporarily.
    base_location = os.path.join(HERE, "namespace_package_base")
    other_location = os.path.join(HERE, "namespace_package_other_base")
    app_path = os.path.join(base_location, "nsapp")

    def test_single_path(self):
        """
        A Py3.3+ namespace package can be an app if it has only one path.
        """
        with extend_sys_path(self.base_location):
            with self.settings(INSTALLED_APPS=["nsapp"]):
                app_config = apps.get_app_config("nsapp")
                self.assertEqual(app_config.path, self.app_path)

    def test_multiple_paths(self):
        """
        A Py3.3+ namespace package with multiple locations cannot be an app.

        (Because then we wouldn't know where to load its templates, static
        assets, etc. from.)
        """
        # Temporarily add two directories to sys.path that both contain
        # components of the "nsapp" package.
        with extend_sys_path(self.base_location, self.other_location):
            with self.assertRaises(ImproperlyConfigured):
                with self.settings(INSTALLED_APPS=["nsapp"]):
                    pass

    def test_multiple_paths_explicit_path(self):
        """
        Multiple locations are ok only if app-config has explicit path.
        """
        # Temporarily add two directories to sys.path that both contain
        # components of the "nsapp" package.
        with extend_sys_path(self.base_location, self.other_location):
            with self.settings(INSTALLED_APPS=["nsapp.apps.NSAppConfig"]):
                app_config = apps.get_app_config("nsapp")
                self.assertEqual(app_config.path, self.app_path)


class DeprecationTests(SimpleTestCase):
    @ignore_warnings(category=RemovedInDjango41Warning)
    def test_explicit_default_app_config(self):
        with self.settings(INSTALLED_APPS=["apps.explicit_default_config_app"]):
            config = apps.get_app_config("explicit_default_config_app")
        self.assertIsInstance(config, ExplicitDefaultConfig)

    def test_explicit_default_app_config_warning(self):
        """
        Load an app that specifies a default AppConfig class matching the
        autodetected one.
        """
        msg = (
            "'apps.explicit_default_config_app' defines default_app_config = "
            "'apps.explicit_default_config_app.apps.ExplicitDefaultConfig'. "
            "Django now detects this configuration automatically. You can "
            "remove default_app_config."
        )
        with self.assertRaisesMessage(RemovedInDjango41Warning, msg):
            with self.settings(INSTALLED_APPS=["apps.explicit_default_config_app"]):
                pass
        with ignore_warnings(category=RemovedInDjango41Warning):
            with self.settings(INSTALLED_APPS=["apps.explicit_default_config_app"]):
                self.assertIsInstance(
                    apps.get_app_config("explicit_default_config_app"),
                    ExplicitDefaultConfig,
                )

    def test_explicit_default_app_config_mismatch(self):
        """
        Load an app that specifies a default AppConfig class not matching the
        autodetected one.
        """
        msg = (
            "'apps.explicit_default_config_mismatch_app' defines "
            "default_app_config = 'apps.explicit_default_config_mismatch_app."
            "not_apps.ExplicitDefaultConfigMismatch'. However, Django's "
            "automatic detection picked another configuration, 'apps."
            "explicit_default_config_mismatch_app.apps."
            "ImplicitDefaultConfigMismatch'. You should move the default "
            "config class to the apps submodule of your application and, if "
            "this module defines several config classes, mark the default one "
            "with default = True."
        )
        with self.assertRaisesMessage(RemovedInDjango41Warning, msg):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_mismatch_app"]
            ):
                pass
        with ignore_warnings(category=RemovedInDjango41Warning):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_mismatch_app"]
            ):
                self.assertIsInstance(
                    apps.get_app_config("explicit_default_config_mismatch_app"),
                    ExplicitDefaultConfigMismatch,
                )

    def test_explicit_default_app_config_empty_apps(self):
        """
        Load an app that specifies a default AppConfig class in __init__ and
        have an empty apps module.
        """
        msg = (
            "'apps.explicit_default_config_empty_apps' defines "
            "default_app_config = 'apps.explicit_default_config_empty_apps."
            "ExplicitDefaultConfigEmptyApps'. However, Django's automatic "
            "detection did not find this configuration. You should move the "
            "default config class to the apps submodule of your application "
            "and, if this module defines several config classes, mark the "
            "default one with default = True."
        )
        with self.assertRaisesMessage(RemovedInDjango41Warning, msg):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_empty_apps"]
            ):
                pass
        with ignore_warnings(category=RemovedInDjango41Warning):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_empty_apps"]
            ):
                self.assertIsInstance(
                    apps.get_app_config("explicit_default_config_empty_apps"),
                    ExplicitDefaultConfigEmptyApps,
                )

    def test_explicit_default_app_config_without_apps(self):
        """
        Load an app that specifies a default AppConfig class in __init__ and do
        not have an apps module.
        """
        msg = (
            "'apps.explicit_default_config_without_apps' defines "
            "default_app_config = 'apps.explicit_default_config_without_apps."
            "ExplicitDefaultConfigWithoutApps'. However, Django's automatic "
            "detection did not find this configuration. You should move the "
            "default config class to the apps submodule of your application "
            "and, if this module defines several config classes, mark the "
            "default one with default = True."
        )
        with self.assertRaisesMessage(RemovedInDjango41Warning, msg):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_without_apps"]
            ):
                pass
        with ignore_warnings(category=RemovedInDjango41Warning):
            with self.settings(
                INSTALLED_APPS=["apps.explicit_default_config_without_apps"]
            ):
                self.assertIsInstance(
                    apps.get_app_config("explicit_default_config_without_apps"),
                    ExplicitDefaultConfigWithoutApps,
                )
