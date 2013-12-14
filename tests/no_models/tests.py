from django.apps import app_cache
from django.test import TestCase


class NoModelTests(TestCase):

    def test_no_models(self):
        """Test that it's possible to load an app with no models.py file."""
        app_config = app_cache.get_app_config('no_models')
        self.assertIsNone(app_config.models_module)
