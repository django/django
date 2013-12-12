from __future__ import unicode_literals

import os
import sys
from unittest import TestCase

from django.apps import app_cache
from django.apps.cache import AppCache
from django.test.utils import override_settings
from django.utils._os import upath


class EggLoadingTest(TestCase):

    def setUp(self):
        self.old_path = sys.path[:]
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        self._old_models = app_cache.app_configs['app_loading'].models.copy()

    def tearDown(self):
        app_cache.app_configs['app_loading'].models = self._old_models
        app_cache._get_models_cache = {}

        sys.path = self.old_path

    def test_egg1(self):
        """Models module can be loaded from an app in an egg"""
        egg_name = '%s/modelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = app_cache.load_app('app_with_models')
        self.assertFalse(models is None)

    def test_egg2(self):
        """Loading an app from an egg that has no models returns no models (and no error)"""
        egg_name = '%s/nomodelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = app_cache.load_app('app_no_models')
        self.assertTrue(models is None)

    def test_egg3(self):
        """Models module can be loaded from an app located under an egg's top-level package"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = app_cache.load_app('omelet.app_with_models')
        self.assertFalse(models is None)

    def test_egg4(self):
        """Loading an app with no models from under the top-level egg package generates no error"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = app_cache.load_app('omelet.app_no_models')
        self.assertTrue(models is None)

    def test_egg5(self):
        """Loading an app from an egg that has an import error in its models module raises that error"""
        egg_name = '%s/brokenapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        self.assertRaises(ImportError, app_cache.load_app, 'broken_app')
        raised = None
        try:
            app_cache.load_app('broken_app')
        except ImportError as e:
            raised = e

        # Make sure the message is indicating the actual
        # problem in the broken app.
        self.assertTrue(raised is not None)
        self.assertTrue("modelz" in raised.args[0])

    def test_missing_app(self):
        """
        Test that repeated app loading doesn't succeed in case there is an
        error. Refs #17667.
        """
        # AppCache is a Borg, so we can instantiate one and change its
        # loaded to False to force the following code to actually try to
        # populate the cache.
        a = AppCache()
        a.loaded = False
        try:
            with override_settings(INSTALLED_APPS=('notexists',)):
                self.assertRaises(ImportError, app_cache.get_model, 'notexists', 'nomodel', seed_cache=True)
                self.assertRaises(ImportError, app_cache.get_model, 'notexists', 'nomodel', seed_cache=True)
        finally:
            a.loaded = True


class GetModelsTest(TestCase):
    def setUp(self):
        from .not_installed import models
        self.not_installed_module = models

    def test_get_model_only_returns_installed_models(self):
        self.assertEqual(
            app_cache.get_model("not_installed", "NotInstalledModel"), None)

    def test_get_model_with_not_installed(self):
        self.assertEqual(
            app_cache.get_model(
                "not_installed", "NotInstalledModel", only_installed=False),
            self.not_installed_module.NotInstalledModel)

    def test_get_models_only_returns_installed_models(self):
        self.assertFalse(
            "NotInstalledModel" in
            [m.__name__ for m in app_cache.get_models()])

    def test_get_models_with_app_label_only_returns_installed_models(self):
        self.assertEqual(app_cache.get_models(self.not_installed_module), [])

    def test_get_models_with_not_installed(self):
        self.assertTrue(
            "NotInstalledModel" in [
                m.__name__ for m in app_cache.get_models(only_installed=False)])


class NotInstalledModelsTest(TestCase):
    def test_related_not_installed_model(self):
        from .not_installed.models import NotInstalledModel
        self.assertEqual(
            set(NotInstalledModel._meta.get_all_field_names()),
            set(["id", "relatedmodel", "m2mrelatedmodel"]))
