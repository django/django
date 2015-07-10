from django.apps import apps
from django.test import SimpleTestCase


class NoModelTests(SimpleTestCase):

    def test_no_models(self):
        """Test that it's possible to load an app with no models.py file."""
        app_config = apps.get_app_config('no_models')
        self.assertIsNone(app_config.models_module)
