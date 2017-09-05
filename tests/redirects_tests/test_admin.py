from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth.models import User
from django.contrib.redirects.models import Redirect
from django.test import (
    RequestFactory, TestCase, modify_settings, override_settings,
)
from django.urls import reverse


class RedirectAdminTests(TestCase):
    def setUp(self):
        from django.contrib.redirects.admin import RedirectAdmin
        self.ma = RedirectAdmin(Redirect, admin.site)

    def test_site_field_enabled(self):
        request = RequestFactory().get('/')

        fields = flatten_fieldsets(self.ma.get_fieldsets(request))

        self.assertIn('site', fields)

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_no_site_field(self):
        request = RequestFactory().get('/')

        fields = flatten_fieldsets(self.ma.get_fieldsets(request))

        self.assertNotIn('site', fields)

    @override_settings(ROOT_URLCONF='redirects_tests.urls')
    def test_model_registered(self):
        superuser = User.objects.create_superuser(
            username='admin', password='something', email='test@test.org',
        )
        self.client.force_login(superuser)

        response = self.client.get(reverse('admin:redirects_redirect_add'))

        self.assertEqual(response.status_code, 200)
