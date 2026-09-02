import sys
from types import ModuleType

from django.conf import DEFAULT_AUTO_FIELD_DEPRECATED_MSG, Settings, settings
from django.test import SimpleTestCase, override_settings
from django.utils.deprecation import RemovedInDjango71Warning


# RemovedInDjango71Warning.
class DefaultAutoFieldDeprecationTests(SimpleTestCase):
    msg = DEFAULT_AUTO_FIELD_DEPRECATED_MSG

    def test_override_settings_warns(self):
        with self.assertRaisesMessage(RemovedInDjango71Warning, self.msg):
            with override_settings(DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"):
                settings.DEFAULT_AUTO_FIELD

    def test_settings_module_warns(self):
        settings_module = ModuleType("fake_settings_module")
        settings_module.SECRET_KEY = "secret"
        settings_module.INSTALLED_APPS = []
        settings_module.DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
        sys.modules["fake_settings_module"] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango71Warning, self.msg):
                Settings("fake_settings_module")
        finally:
            del sys.modules["fake_settings_module"]
