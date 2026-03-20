from django.apps import apps
from django.test import SimpleTestCase


class NoModelTests(SimpleTestCase):
    def test_no_models(self):
        """It's possible to load an app with no models.py file."""
        app_config = apps.get_app_config("no_models")
        self.assertIsNone(app_config.models_module)

    def test_app_label(self):
        app_config = apps.get_app_config("no_models")
        self.assertEqual(app_config.label, "no_models")

    def test_app_is_installed(self):
        self.assertTrue(apps.is_installed("no_models"))

    def test_get_models_returns_empty(self):
        app_config = apps.get_app_config("no_models")
        self.assertEqual(list(app_config.get_models()), [])
