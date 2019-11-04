from django.contrib.admin.templatetags.admin_static import static
from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango30Warning


class AdminStaticDeprecationTests(SimpleTestCase):
    def test(self):
        """
        admin_static.static points to the collectstatic version
        (as django.contrib.collectstatic is in INSTALLED_APPS).
        """
        msg = (
            '{% load admin_static %} is deprecated in favor of '
            '{% load static %}.'
        )
        old_url = staticfiles_storage.base_url
        staticfiles_storage.base_url = '/test/'
        try:
            with self.assertWarnsMessage(RemovedInDjango30Warning, msg):
                url = static('path')
            self.assertEqual(url, '/test/path')
        finally:
            staticfiles_storage.base_url = old_url
