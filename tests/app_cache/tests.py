from __future__ import absolute_import

from django.core.apps import app_cache
from django.core.apps.cache import AppCache
from django.db import models
from django.test import TestCase

from .models import TotallyNormal, SoAlternative, new_app_cache


class AppCacheTests(TestCase):

    def test_models_py(self):
        """
        Tests that the models in the models.py file were loaded correctly.
        """
        self.assertEqual(app_cache.get_model("app_cache", "TotallyNormal"), TotallyNormal)
        self.assertEqual(app_cache.get_model("app_cache", "SoAlternative"), None)

        self.assertEqual(new_app_cache.get_model("app_cache", "TotallyNormal"), None)
        self.assertEqual(new_app_cache.get_model("app_cache", "SoAlternative"), SoAlternative)

    def test_dynamic_load(self):
        """
        Makes a new model at runtime and ensures it goes into the right place.
        """
        old_models = app_cache.get_models(app_cache.get_app_config("app_cache").models_module)
        # Construct a new model in a new app cache
        body = {}
        new_app_cache = AppCache()
        meta_contents = {
            'app_label': "app_cache",
            'app_cache': new_app_cache,
        }
        meta = type("Meta", tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = TotallyNormal.__module__
        temp_model = type("SouthPonies", (models.Model,), body)
        # Make sure it appeared in the right place!
        self.assertEqual(
            old_models,
            app_cache.get_models(app_cache.get_app_config("app_cache").models_module),
        )
        self.assertEqual(new_app_cache.get_model("app_cache", "SouthPonies"), temp_model)

    def test_singleton_master(self):
        """
        Ensures that only one master app cache can exist.
        """
        with self.assertRaises(RuntimeError):
            AppCache(master=True)
