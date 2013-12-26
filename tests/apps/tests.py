from __future__ import absolute_import

from django.apps import apps
from django.apps.registry import Apps
from django.db import models
from django.test import TestCase

from .models import TotallyNormal, SoAlternative, new_apps


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
        # Currently, non-master app registries are artificially considered
        # ready regardless of whether populate_models() has run.
        self.assertTrue(apps.ready)

    def test_models_py(self):
        """
        Tests that the models in the models.py file were loaded correctly.
        """
        self.assertEqual(apps.get_model("apps", "TotallyNormal"), TotallyNormal)
        self.assertEqual(apps.get_model("apps", "SoAlternative"), None)

        self.assertEqual(new_apps.get_model("apps", "TotallyNormal"), None)
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
        meta = type("Meta", tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = TotallyNormal.__module__
        temp_model = type("SouthPonies", (models.Model,), body)
        # Make sure it appeared in the right place!
        self.assertEqual(
            old_models,
            apps.get_models(apps.get_app_config("apps").models_module),
        )
        self.assertEqual(new_apps.get_model("apps", "SouthPonies"), temp_model)
