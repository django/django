from mango.apps import apps
from mango.test import SimpleTestCase


class NoModelTests(SimpleTestCase):

    def test_no_models(self):
        """It's possible to load an app with no models.py file."""
        app_config = apps.get_app_config('no_models')
        self.assertIsNone(app_config.models_module)
