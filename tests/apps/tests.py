from __future__ import absolute_import, unicode_literals

from django.apps import apps
from django.apps.registry import Apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import TestCase, override_settings

from .models import TotallyNormal, SoAlternative, new_apps


# Small list with a variety of cases for tests that iterate on installed apps.
# Intentionally not in alphabetical order to check if the order is preserved.

SOME_INSTALLED_APPS = [
    'apps.apps.MyAdmin',
    'apps.apps.MyAuth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

SOME_INSTALLED_APPS_NAMES = [
    'django.contrib.admin',
    'django.contrib.auth',
] + SOME_INSTALLED_APPS[2:]

SOME_INSTALLED_APPS_WTH_MODELS_NAMES = SOME_INSTALLED_APPS_NAMES[:4]


class AppsTests(TestCase):

    def test_singleton_master(self):
        """
        Ensures that only one master registry can exist.
        """
        with self.assertRaises(RuntimeError):
            Apps(master=True)

    def test_ready(self):
        """
        Tests the ready property of the master registry.
        """
        # The master app registry is always ready when the tests run.
        self.assertTrue(apps.ready)

    def test_non_master_ready(self):
        """
        Tests the ready property of a registry other than the master.
        """
        apps = Apps()
        self.assertFalse(apps.ready)
        apps.populate_apps([])
        self.assertFalse(apps.ready)
        apps.populate_models()
        self.assertTrue(apps.ready)

    def test_bad_app_config(self):
        """
        Tests when INSTALLED_APPS contains an incorrect app config.
        """
        with self.assertRaises(ImproperlyConfigured):
            with self.settings(INSTALLED_APPS=['apps.apps.BadConfig']):
                pass

    def test_not_an_app_config(self):
        """
        Tests when INSTALLED_APPS contains a class that isn't an app config.
        """
        with self.assertRaises(ImproperlyConfigured):
            with self.settings(INSTALLED_APPS=['apps.apps.NotAConfig']):
                pass

    def test_no_such_app(self):
        """
        Tests when INSTALLED_APPS contains an app that doesn't exist, either
        directly or via an app config.
        """
        with self.assertRaises(ImportError):
            with self.settings(INSTALLED_APPS=['there is no such app']):
                pass
        with self.assertRaises(ImportError):
            with self.settings(INSTALLED_APPS=['apps.apps.NoSuchApp']):
                pass

    def test_no_such_app_config(self):
        """
        Tests when INSTALLED_APPS contains an entry that doesn't exist.
        """
        with self.assertRaises(ImportError):
            with self.settings(INSTALLED_APPS=['apps.apps.NoSuchConfig']):
                pass

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_configs(self):
        """
        Tests get_app_configs().
        """
        app_configs = apps.get_app_configs()
        self.assertListEqual(
            [app_config.name for app_config in app_configs],
            SOME_INSTALLED_APPS_NAMES)

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_configs_with_models(self):
        """
        Tests get_app_configs(only_with_models_module=True).
        """
        app_configs = apps.get_app_configs(only_with_models_module=True)
        self.assertListEqual(
            [app_config.name for app_config in app_configs],
            SOME_INSTALLED_APPS_WTH_MODELS_NAMES)

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_config(self):
        """
        Tests get_app_config().
        """
        app_config = apps.get_app_config('admin')
        self.assertEqual(app_config.name, 'django.contrib.admin')

        app_config = apps.get_app_config('staticfiles')
        self.assertEqual(app_config.name, 'django.contrib.staticfiles')

        with self.assertRaises(LookupError):
            apps.get_app_config('webdesign')

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_get_app_config_with_models(self):
        """
        Tests get_app_config(only_with_models_module=True).
        """
        app_config = apps.get_app_config('admin', only_with_models_module=True)
        self.assertEqual(app_config.name, 'django.contrib.admin')

        with self.assertRaises(LookupError):
            apps.get_app_config('staticfiles', only_with_models_module=True)

    @override_settings(INSTALLED_APPS=SOME_INSTALLED_APPS)
    def test_has_app(self):
        self.assertTrue(apps.has_app('django.contrib.admin'))
        self.assertTrue(apps.has_app('django.contrib.staticfiles'))
        self.assertFalse(apps.has_app('django.contrib.webdesign'))

    def test_models_py(self):
        """
        Tests that the models in the models.py file were loaded correctly.
        """
        self.assertEqual(apps.get_model("apps", "TotallyNormal"), TotallyNormal)
        with self.assertRaises(LookupError):
            apps.get_model("apps", "SoAlternative")

        with self.assertRaises(LookupError):
            new_apps.get_model("apps", "TotallyNormal")
        self.assertEqual(new_apps.get_model("apps", "SoAlternative"), SoAlternative)

    def test_dynamic_load(self):
        """
        Makes a new model at runtime and ensures it goes into the right place.
        """
        old_models = apps.get_models(apps.get_app_config("apps").models_module)
        # Construct a new model in a new app registry
        body = {}
        new_apps = Apps()
        meta_contents = {
            'app_label': "apps",
            'apps': new_apps,
        }
        meta = type(str("Meta"), tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = TotallyNormal.__module__
        temp_model = type(str("SouthPonies"), (models.Model,), body)
        # Make sure it appeared in the right place!
        self.assertEqual(
            old_models,
            apps.get_models(apps.get_app_config("apps").models_module),
        )
        with self.assertRaises(LookupError):
            apps.get_model("apps", "SouthPonies")
        self.assertEqual(new_apps.get_model("apps", "SouthPonies"), temp_model)
