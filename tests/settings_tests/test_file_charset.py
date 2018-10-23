import sys
from types import ModuleType

from django.conf import FILE_CHARSET_DEPRECATED_MSG, Settings, settings
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango31Warning


class DeprecationTests(SimpleTestCase):
    msg = FILE_CHARSET_DEPRECATED_MSG

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango31Warning, self.msg):
            with self.settings(FILE_CHARSET='latin1'):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.FILE_CHARSET = 'latin1'
        settings_module.SECRET_KEY = 'ABC'
        sys.modules['fake_settings_module'] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango31Warning, self.msg):
                Settings('fake_settings_module')
        finally:
            del sys.modules['fake_settings_module']

    def test_access_warning(self):
        with self.assertRaisesMessage(RemovedInDjango31Warning, self.msg):
            settings.FILE_CHARSET
        # Works a second time.
        with self.assertRaisesMessage(RemovedInDjango31Warning, self.msg):
            settings.FILE_CHARSET

    @ignore_warnings(category=RemovedInDjango31Warning)
    def test_access(self):
        with self.settings(FILE_CHARSET='latin1'):
            self.assertEqual(settings.FILE_CHARSET, 'latin1')
            # Works a second time.
            self.assertEqual(settings.FILE_CHARSET, 'latin1')
