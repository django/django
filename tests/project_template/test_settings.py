import sys
import unittest

from django.test import TestCase


@unittest.skipIf(sys.version_info < (3, 3),
    'Python < 3.3 cannot import the project template because '
    'django/conf/project_template doesn\'t have an __init__.py file.')
class TestStartProjectSettings(TestCase):

    def test_middleware_classes_headers(self):
        """
        Ensure headers sent by the default MIDDLEWARE_CLASSES do not
        inadvertently change. For example, we never want "Vary: Cookie" to
        appear in the list since it prevents the caching of responses.
        """
        from django.conf.project_template.project_name.settings import MIDDLEWARE_CLASSES

        with self.settings(
            MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES,
            ROOT_URLCONF='project_template.urls',
        ):
            response = self.client.get('/empty/')
            headers = sorted(response.serialize_headers().split(b'\r\n'))
            self.assertEqual(headers, [
                b'Content-Type: text/html; charset=utf-8',
                b'X-Frame-Options: SAMEORIGIN',
            ])
