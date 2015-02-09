from __future__ import unicode_literals

import os
import sys
import warnings

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import TestCase
from django.test.utils import extend_sys_path
from django.utils import six
from django.utils._os import upath
from django.utils.deprecation import RemovedInDjango19Warning


class EggLoadingTest(TestCase):

    def setUp(self):
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

    def tearDown(self):
        apps.clear_cache()

    def test_egg1(self):
        """Models module can be loaded from an app in an egg"""
        egg_name = '%s/modelapp.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=['app_with_models']):
                models_module = apps.get_app_config('app_with_models').models_module
                self.assertIsNotNone(models_module)
        del apps.all_models['app_with_models']

    def test_egg2(self):
        """Loading an app from an egg that has no models returns no models (and no error)"""
        egg_name = '%s/nomodelapp.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=['app_no_models']):
                models_module = apps.get_app_config('app_no_models').models_module
                self.assertIsNone(models_module)
        del apps.all_models['app_no_models']

    def test_egg3(self):
        """Models module can be loaded from an app located under an egg's top-level package"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=['omelet.app_with_models']):
                models_module = apps.get_app_config('app_with_models').models_module
                self.assertIsNotNone(models_module)
        del apps.all_models['app_with_models']

    def test_egg4(self):
        """Loading an app with no models from under the top-level egg package generates no error"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=['omelet.app_no_models']):
                models_module = apps.get_app_config('app_no_models').models_module
                self.assertIsNone(models_module)
        del apps.all_models['app_no_models']

    def test_egg5(self):
        """Loading an app from an egg that has an import error in its models module raises that error"""
        egg_name = '%s/brokenapp.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with six.assertRaisesRegex(self, ImportError, 'modelz'):
                with self.settings(INSTALLED_APPS=['broken_app']):
                    pass


class GetModelsTest(TestCase):
    def setUp(self):
        from .not_installed import models
        self.not_installed_module = models

    def test_get_model_only_returns_installed_models(self):
        with self.assertRaises(LookupError):
            apps.get_model("not_installed", "NotInstalledModel")

    def test_get_models_only_returns_installed_models(self):
        self.assertNotIn(
            "NotInstalledModel",
            [m.__name__ for m in apps.get_models()])

    def test_exception_raised_if_model_declared_outside_app(self):

        class FakeModule(models.Model):
            __name__ = str("models_that_do_not_live_in_an_app")

        sys.modules['models_not_in_app'] = FakeModule

        def declare_model_outside_app():
            models.base.ModelBase.__new__(
                models.base.ModelBase,
                str('Outsider'),
                (models.Model,),
                {'__module__': 'models_not_in_app'})

        msg = (
            'Unable to detect the app label for model "Outsider." '
            'Ensure that its module, "models_that_do_not_live_in_an_app", '
            'is located inside an installed app.'
        )
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=RemovedInDjango19Warning)
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                declare_model_outside_app()
