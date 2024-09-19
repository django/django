import os

from django.apps import apps
from django.test import SimpleTestCase
from django.test.utils import extend_sys_path


class EggLoadingTest(SimpleTestCase):
    def setUp(self):
        self.egg_dir = "%s/eggs" % os.path.dirname(__file__)
        self.addCleanup(apps.clear_cache)

    def test_egg1(self):
        egg_name = "%s/modelapp.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=["app_with_models"]):
                models_module = apps.get_app_config("app_with_models").models_module
                self.assertIsNotNone(models_module)
        del apps.all_models["app_with_models"]

    def test_egg2(self):
        egg_name = "%s/nomodelapp.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=["app_no_models"]):
                models_module = apps.get_app_config("app_no_models").models_module
                self.assertIsNone(models_module)
        del apps.all_models["app_no_models"]

    def test_egg3(self):
        egg_name = "%s/omelet.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=["omelet.app_with_models"]):
                models_module = apps.get_app_config("app_with_models").models_module
                self.assertIsNotNone(models_module)
        del apps.all_models["app_with_models"]

    def test_egg4(self):
        egg_name = "%s/omelet.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=["omelet.app_no_models"]):
                models_module = apps.get_app_config("app_no_models").models_module
                self.assertIsNone(models_module)
        del apps.all_models["app_no_models"]

    def test_egg5(self):
        egg_name = "%s/brokenapp.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            with self.assertRaisesMessage(ImportError, "modelz"):
                with self.settings(INSTALLED_APPS=["broken_app"]):
                    pass


class GetModelsTest(SimpleTestCase):
    def setUp(self):
        from .not_installed import models

        self.not_installed_module = models

    def test_get_model_only_returns_installed_models(self):
        with self.assertRaises(LookupError):
            apps.get_model("not_installed", "NotInstalledModel")

    def test_get_models_only_returns_installed_models(self):
        self.assertNotIn("NotInstalledModel", [m.__name__ for m in apps.get_models()])
