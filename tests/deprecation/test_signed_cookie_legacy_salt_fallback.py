import sys
from types import ModuleType

from django.conf import (
    SIGNED_COOKIE_LEGACY_SALT_DEPRECATED_MSG,
    LazySettings,
    Settings,
    settings,
)
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango70Warning


# RemovedInDjango70Warning.
class SignedCookieLegacySaltFallbackDeprecationTests(SimpleTestCase):
    msg = SIGNED_COOKIE_LEGACY_SALT_DEPRECATED_MSG

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
            with self.settings(SIGNED_COOKIE_LEGACY_SALT_FALLBACK=True):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType("fake_settings_module")
        settings_module.USE_TZ = False
        settings_module.SIGNED_COOKIE_LEGACY_SALT_FALLBACK = True
        sys.modules["fake_settings_module"] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
                Settings("fake_settings_module")
        finally:
            del sys.modules["fake_settings_module"]

    def test_settings_assignment_warning(self):
        lazy_settings = LazySettings()
        with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
            lazy_settings.SIGNED_COOKIE_LEGACY_SALT_FALLBACK = True

    def test_access(self):
        # Warning is not raised on access.
        self.assertEqual(settings.SIGNED_COOKIE_LEGACY_SALT_FALLBACK, False)
