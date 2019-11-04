from django.contrib import admin
from django.contrib.admin import sites
from django.test import SimpleTestCase, override_settings


@override_settings(INSTALLED_APPS=[
    'admin_default_site.apps.MyCustomAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
])
class CustomAdminSiteTests(SimpleTestCase):

    def setUp(self):
        # Reset admin.site since it may have already been instantiated by
        # another test app.
        self._old_site = admin.site
        admin.site = sites.site = sites.DefaultAdminSite()

    def tearDown(self):
        admin.site = sites.site = self._old_site

    def test_use_custom_admin_site(self):
        self.assertEqual(admin.site.__class__.__name__, 'CustomAdminSite')


class DefaultAdminSiteTests(SimpleTestCase):
    def test_use_default_admin_site(self):
        self.assertEqual(admin.site.__class__.__name__, 'AdminSite')
