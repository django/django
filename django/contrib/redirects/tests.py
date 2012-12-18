from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six

from .models import Redirect


@override_settings(
    SITE_ID=1,
    APPEND_SLASH=True,
    MIDDLEWARE_CLASSES=list(settings.MIDDLEWARE_CLASSES) +
        ['django.contrib.redirects.middleware.RedirectFallbackMiddleware'],
)
class RedirectTests(TestCase):

    def setUp(self):
        self.site = Site.objects.get(pk=settings.SITE_ID)

    def test_model(self):
        r1 = Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='/new_target')
        self.assertEqual(six.text_type(r1), "/initial ---> /new_target")

    def test_redirect_middleware(self):
        r1 = Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='/new_target')
        response = self.client.get('/initial')
        self.assertRedirects(response,
            '/new_target', status_code=301, target_status_code=404)
        # Works also with trailing slash
        response = self.client.get('/initial/')
        self.assertRedirects(response,
            '/new_target', status_code=301, target_status_code=404)

    def test_response_gone(self):
        """When the redirect target is '', return a 410"""
        r1 = Redirect.objects.create(
            site=self.site, old_path='/initial', new_path='')
        response = self.client.get('/initial')
        self.assertEqual(response.status_code, 410)
