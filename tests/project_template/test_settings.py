import os
import shutil
import unittest

from django import conf
from django.test import TestCase
from django.utils import six
from django.utils._os import upath


@unittest.skipIf(
    six.PY2,
    'Python 2 cannot import the project template because '
    'django/conf/project_template doesn\'t have an __init__.py file.'
)
class TestStartProjectSettings(TestCase):
    def setUp(self):
        # Ensure settings.py exists
        project_dir = os.path.join(
            os.path.dirname(upath(conf.__file__)),
            'project_template',
            'project_name',
        )
        template_settings_py = os.path.join(project_dir, 'settings.py-tpl')
        test_settings_py = os.path.join(project_dir, 'settings.py')
        shutil.copyfile(template_settings_py, test_settings_py)
        self.addCleanup(os.remove, test_settings_py)

    def test_middleware_headers(self):
        """
        Ensure headers sent by the default MIDDLEWARE don't inadvertently
        change. For example, we never want "Vary: Cookie" to appear in the list
        since it prevents the caching of responses.
        """
        from django.conf.project_template.project_name.settings import MIDDLEWARE

        with self.settings(
            MIDDLEWARE=MIDDLEWARE,
            ROOT_URLCONF='project_template.urls',
        ):
            response = self.client.get('/empty/')
            headers = sorted(response.serialize_headers().split(b'\r\n'))
            self.assertEqual(headers, [
                b'Content-Type: text/html; charset=utf-8',
                b'X-Frame-Options: SAMEORIGIN',
            ])
