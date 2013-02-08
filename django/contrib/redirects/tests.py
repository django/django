from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six

from .middleware import RedirectFallbackMiddleware
from .models import Redirect


@override_settings(
    APPEND_SLASH=False,
    MIDDLEWARE_CLASSES=list(settings.MIDDLEWARE_CLASSES) +
        ['django.contrib.redirects.middleware.RedirectFallbackMiddleware'],
    SITE_ID=1,
)
class RedirectTests(TestCase):

    def setUp(self):
        self.site = Site.objects.get(pk=settings.SITE_ID)

    def test_model(self):
        r1 = Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='/new_target')
        self.assertEqual(six.text_type(r1), "/initial ---> /new_target")

    def test_redirect(self):
        Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='/new_target')
        response = self.client.get('/initial')
        self.assertRedirects(response,
            '/new_target', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash(self):
        Redirect.objects.create(
            site=self.site, old_path='/initial/', new_path='/new_target/')
        response = self.client.get('/initial')
        self.assertRedirects(response,
            '/new_target/', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash_and_query_string(self):
        Redirect.objects.create(
            site=self.site, old_path='/initial/?foo', new_path='/new_target/')
        response = self.client.get('/initial?foo')
        self.assertRedirects(response,
            '/new_target/', status_code=301, target_status_code=404)

    def test_response_gone(self):
        """When the redirect target is '', return a 410"""
        Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='')
        response = self.client.get('/initial')
        self.assertEqual(response.status_code, 410)

    @override_settings(
        INSTALLED_APPS=[app for app in settings.INSTALLED_APPS
                        if app != 'django.contrib.sites'])
    def test_sites_not_installed(self):
        with self.assertRaises(ImproperlyConfigured):
            RedirectFallbackMiddleware()
