import sys
from types import ModuleType

from django.conf import DEFAULT_CONTENT_TYPE_DEPRECATED_MSG, Settings, settings
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango30Warning


class DefaultContentTypeTests(SimpleTestCase):
    msg = DEFAULT_CONTENT_TYPE_DEPRECATED_MSG

    @ignore_warnings(category=RemovedInDjango30Warning)
    def test_default_content_type_is_text_html(self):
        """
        Content-Type of the default error responses is text/html. Refs #20822.
        """
        with self.settings(DEFAULT_CONTENT_TYPE='text/xml'):
            response = self.client.get('/raises400/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/raises403/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/nonexistent_url/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/server_error/')
            self.assertEqual(response['Content-Type'], 'text/html')

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
            with self.settings(DEFAULT_CONTENT_TYPE='text/xml'):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.DEFAULT_CONTENT_TYPE = 'text/xml'
        settings_module.SECRET_KEY = 'abc'
        sys.modules['fake_settings_module'] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
                Settings('fake_settings_module')
        finally:
            del sys.modules['fake_settings_module']

    def test_access_warning(self):
        with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
            settings.DEFAULT_CONTENT_TYPE
        # Works a second time.
        with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
            settings.DEFAULT_CONTENT_TYPE

    @ignore_warnings(category=RemovedInDjango30Warning)
    def test_access(self):
        with self.settings(DEFAULT_CONTENT_TYPE='text/xml'):
            self.assertEqual(settings.DEFAULT_CONTENT_TYPE, 'text/xml')
            # Works a second time.
            self.assertEqual(settings.DEFAULT_CONTENT_TYPE, 'text/xml')
