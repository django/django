from __future__ import absolute_import

import copy
import os
import sys
import time

from django.conf import Settings
from django.db.models.loading import cache, load_app, get_model, get_models
from django.utils._os import upath
from django.utils.unittest import TestCase

class EggLoadingTest(TestCase):

    def setUp(self):
        self.old_path = sys.path[:]
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

        # This test adds dummy applications to the app cache. These
        # need to be removed in order to prevent bad interactions
        # with the flush operation in other tests.
        self.old_app_models = copy.deepcopy(cache.app_models)
        self.old_app_store = copy.deepcopy(cache.app_store)

    def tearDown(self):
        sys.path = self.old_path
        cache.app_models = self.old_app_models
        cache.app_store = self.old_app_store

    def test_egg1(self):
        """Models module can be loaded from an app in an egg"""
        egg_name = '%s/modelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('app_with_models')
        self.assertFalse(models is None)

    def test_egg2(self):
        """Loading an app from an egg that has no models returns no models (and no error)"""
        egg_name = '%s/nomodelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('app_no_models')
        self.assertTrue(models is None)

    def test_egg3(self):
        """Models module can be loaded from an app located under an egg's top-level package"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('omelet.app_with_models')
        self.assertFalse(models is None)

    def test_egg4(self):
        """Loading an app with no models from under the top-level egg package generates no error"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('omelet.app_no_models')
        self.assertTrue(models is None)

    def test_egg5(self):
        """Loading an app from an egg that has an import error in its models module raises that error"""
        egg_name = '%s/brokenapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        self.assertRaises(ImportError, load_app, 'broken_app')
        try:
            load_app('broken_app')
        except ImportError as e:
            # Make sure the message is indicating the actual
            # problem in the broken app.
            self.assertTrue("modelz" in e.args[0])


class GetModelsTest(TestCase):
    def setUp(self):
        from .not_installed import models
        self.not_installed_module = models


    def test_get_model_only_returns_installed_models(self):
        self.assertEqual(
            get_model("not_installed", "NotInstalledModel"), None)


    def test_get_model_with_not_installed(self):
        self.assertEqual(
            get_model(
                "not_installed", "NotInstalledModel", only_installed=False),
            self.not_installed_module.NotInstalledModel)


    def test_get_models_only_returns_installed_models(self):
        self.assertFalse(
            "NotInstalledModel" in
            [m.__name__ for m in get_models()])


    def test_get_models_with_app_label_only_returns_installed_models(self):
        self.assertEqual(get_models(self.not_installed_module), [])


    def test_get_models_with_not_installed(self):
        self.assertTrue(
            "NotInstalledModel" in [
                m.__name__ for m in get_models(only_installed=False)])


class NotInstalledModelsTest(TestCase):
    def test_related_not_installed_model(self):
        from .not_installed.models import NotInstalledModel
        self.assertEqual(
            set(NotInstalledModel._meta.get_all_field_names()),
            set(["id", "relatedmodel", "m2mrelatedmodel"]))
