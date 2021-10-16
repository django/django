from django.conf import settings
from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.http.response import HttpResponse, HttpResponseRedirectBase
from django.test import TestCase, modify_settings, override_settings
from django.test.utils import isolate_apps


@modify_settings(MIDDLEWARE={'append': 'django.contrib.redirects.middleware.RedirectFallbackMiddleware'})
@override_settings(APPEND_SLASH=False, ROOT_URLCONF='redirects_tests.urls', SITE_ID=1)
class RedirectTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.get(pk=settings.SITE_ID)

    def test_model(self):
        r1 = Redirect.objects.create(site=self.site, redirect_type=301, old_path='/initial', new_path='/new_target')
        self.assertEqual(str(r1), "/initial ---> /new_target")

    def test_redirect(self):
        Redirect.objects.create(site=self.site, redirect_type=301, old_path='/initial', new_path='/new_target')
        response = self.client.get('/initial')
        self.assertRedirects(response, '/new_target', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash(self):
        Redirect.objects.create(site=self.site, redirect_type=301, old_path='/initial/', new_path='/new_target/')
        response = self.client.get('/initial')
        self.assertRedirects(response, '/new_target/', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_with_append_slash_and_query_string(self):
        Redirect.objects.create(site=self.site, redirect_type=301, old_path='/initial/?foo', new_path='/new_target/')
        response = self.client.get('/initial?foo')
        self.assertRedirects(response, '/new_target/', status_code=301, target_status_code=404)

    @override_settings(APPEND_SLASH=True)
    def test_redirect_not_found_with_append_slash(self):
        """
        Exercise the second Redirect.DoesNotExist branch in
        RedirectFallbackMiddleware.
        """
        response = self.client.get('/test')
        self.assertEqual(response.status_code, 404)

    def test_redirect_shortcircuits_non_404_response(self):
        """RedirectFallbackMiddleware short-circuits on non-404 requests."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_response_gone(self):
        Redirect.objects.create(site=self.site, redirect_type=410, old_path='/initial', new_path='')
        response = self.client.get('/initial')
        self.assertEqual(response.status_code, 410)

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_sites_not_installed(self):
        def get_response(request):
            return HttpResponse()

        msg = (
            'You cannot use RedirectFallbackMiddleware when '
            'django.contrib.sites is not installed.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            RedirectFallbackMiddleware(get_response)


@isolate_apps('redirects_tests')
@modify_settings(MIDDLEWARE={'append': 'redirects_tests.tests.OverriddenRedirectFallbackMiddleware'})
@override_settings(SITE_ID=1)
class OverriddenRedirectMiddlewareTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.get(pk=settings.SITE_ID)

    def test_response_redirect_types(self):

        class OverriddenRedirect(Redirect):
            RedirectTypes = models.IntegerChoices(
                'RedirectTypes',
                [
                    ('Permanent Redirect', 308),
                    *[(m.name, m.value) for m in Redirect.RedirectTypes]
                ],
            )

        class NewHttpResponseRedirect(HttpResponseRedirectBase):
            status_code = 308

        class OverriddenRedirectFallbackMiddleware(RedirectFallbackMiddleware):
            # Override the default Redirect model class
            redirect_model_class = OverriddenRedirect

            # Add an HTTP status-response pair to the defaults
            def get_response_redirect_types(self):
                redirect_types = super().get_response_redirect_types()
                redirect_types.update({308: NewHttpResponseRedirect})
                return redirect_types

        OverriddenRedirect.objects.create(
            site=self.site, redirect_type=308, old_path='/initial/', new_path='/new_target/'
        )
        response = self.client.get('/initial/')
        self.assertEqual(response.status_code, 308)
        OverriddenRedirect.objects.create(
            site=self.site, redirect_type=999, old_path='/initial/', new_path='/new_target/'
        )
        response = self.client.get('/initial/')
        self.assertEqual(response.status_code, 404)
