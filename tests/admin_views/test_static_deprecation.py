import warnings

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
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter('always')
                url = static('path')
            self.assertEqual(url, '/test/path')
            self.assertEqual(len(recorded), 1)
            self.assertIs(recorded[0].category, RemovedInDjango30Warning)
            self.assertEqual(str(recorded[0].message), msg)
        finally:
            staticfiles_storage.base_url = old_url
