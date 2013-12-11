from __future__ import absolute_import

from django.apps.cache import cache, BaseAppCache
from django.db import models
from django.test import TestCase

from .models import TotallyNormal, SoAlternative, new_app_cache


class AppCacheTests(TestCase):
    """
    Tests the AppCache borg and non-borg versions
    """

    def test_models_py(self):
        """
        Tests that the models in the models.py file were loaded correctly.
        """
        self.assertEqual(cache.get_model("app_cache", "TotallyNormal"), TotallyNormal)
        self.assertEqual(cache.get_model("app_cache", "SoAlternative"), None)

        self.assertEqual(new_app_cache.get_model("app_cache", "TotallyNormal"), None)
        self.assertEqual(new_app_cache.get_model("app_cache", "SoAlternative"), SoAlternative)

    def test_dynamic_load(self):
        """
        Makes a new model at runtime and ensures it goes into the right place.
        """
        old_models = cache.get_models(cache.get_app("app_cache"))
        # Construct a new model in a new app cache
        body = {}
        new_app_cache = BaseAppCache()
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
            cache.get_models(cache.get_app("app_cache")),
        )
        self.assertEqual(new_app_cache.get_model("app_cache", "SouthPonies"), temp_model)
