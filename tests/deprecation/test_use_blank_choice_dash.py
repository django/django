import sys
from types import ModuleType

from django.conf import (
    USE_BLANK_CHOICE_DASH_DEPRECATED_MSG,
    LazySettings,
    Settings,
    settings,
)
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango70Warning


# RemovedInDjango70Warning.
class UseBlankChoiceDashDeprecationTests(SimpleTestCase):
    msg = USE_BLANK_CHOICE_DASH_DEPRECATED_MSG

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
            with self.settings(USE_BLANK_CHOICE_DASH=True):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType("fake_settings_module")
        settings_module.USE_TZ = False
        settings_module.USE_BLANK_CHOICE_DASH = True
        sys.modules["fake_settings_module"] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
                Settings("fake_settings_module")
        finally:
            del sys.modules["fake_settings_module"]

    def test_settings_assignment_warning(self):
        settings = LazySettings()
        with self.assertRaisesMessage(RemovedInDjango70Warning, self.msg):
            settings.USE_BLANK_CHOICE_DASH = True

    def test_access(self):
        # Warning is not raised on access.
        self.assertEqual(settings.USE_BLANK_CHOICE_DASH, False)
