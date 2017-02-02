from django import http
from django.conf import settings
from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, modify_settings, override_settings


@modify_settings(MIDDLEWARE={'append': 'django.contrib.redirects.middleware.RedirectFallbackMiddleware'})
@override_settings(APPEND_SLASH=False, SITE_ID=1)
class RedirectTests(TestCase):

    def setUp(self):
        self.site = Site.objects.get(pk=settings.SITE_ID)

    def test_model(self):
        r1 = Redirect.objects.create(site=self.site, old_path='/initial', new_path='/new_target')
        self.assertEqual(str(r1), "/initial ---> /new_target")

    def test_redirect(self):
        Redirect.objects.create(site=self.site, old_path='/initial', new_path='/new_target')
        response = self.client.get('/initial')
        self.assertRedirects(response, '/new_target', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash(self):
        Redirect.objects.create(site=self.site, old_path='/initial/', new_path='/new_target/')
        response = self.client.get('/initial')
        self.assertRedirects(response, '/new_target/', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash_and_query_string(self):
        Redirect.objects.create(site=self.site, old_path='/initial/?foo', new_path='/new_target/')
        response = self.client.get('/initial?foo')
        self.assertRedirects(response, '/new_target/', status_code=301, target_status_code=404)

    def test_response_gone(self):
        """When the redirect target is '', return a 410"""
        Redirect.objects.create(site=self.site, old_path='/initial', new_path='')
        response = self.client.get('/initial')
        self.assertEqual(response.status_code, 410)

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_sites_not_installed(self):
        with self.assertRaises(ImproperlyConfigured):
            RedirectFallbackMiddleware()


class OverriddenRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    # Use HTTP responses different from the defaults
    response_gone_class = http.HttpResponseForbidden
    response_redirect_class = http.HttpResponseRedirect


@modify_settings(MIDDLEWARE={'append': 'redirects_tests.tests.OverriddenRedirectFallbackMiddleware'})
@override_settings(SITE_ID=1)
class OverriddenRedirectMiddlewareTests(TestCase):

    def setUp(self):
        self.site = Site.objects.get(pk=settings.SITE_ID)

    def test_response_gone_class(self):
        Redirect.objects.create(site=self.site, old_path='/initial/', new_path='')
        response = self.client.get('/initial/')
        self.assertEqual(response.status_code, 403)

    def test_response_redirect_class(self):
        Redirect.objects.create(site=self.site, old_path='/initial/', new_path='/new_target/')
        response = self.client.get('/initial/')
        self.assertEqual(response.status_code, 302)
