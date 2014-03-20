from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpRequest
from django.test import TestCase, modify_settings, override_settings

from .middleware import CurrentSiteMiddleware
from .models import Site
from .requests import RequestSite
from .shortcuts import get_current_site


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
class SitesFrameworkTests(TestCase):

    def setUp(self):
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

    def test_save_another(self):
        # Regression for #17415
        # On some backends the sequence needs reset after save with explicit ID.
        # Test that there is no sequence collisions by saving another site.
        Site(domain="example2.com", name="example2.com").save()

    def test_site_manager(self):
        # Make sure that get_current() does not return a deleted Site object.
        s = Site.objects.get_current()
        self.assertTrue(isinstance(s, Site))
        s.delete()
        self.assertRaises(ObjectDoesNotExist, Site.objects.get_current)

    def test_site_cache(self):
        # After updating a Site object (e.g. via the admin), we shouldn't return a
        # bogus value from the SITE_CACHE.
        site = Site.objects.get_current()
        self.assertEqual("example.com", site.name)
        s2 = Site.objects.get(id=settings.SITE_ID)
        s2.name = "Example site"
        s2.save()
        site = Site.objects.get_current()
        self.assertEqual("Example site", site.name)

    def test_delete_all_sites_clears_cache(self):
        # When all site objects are deleted the cache should also
        # be cleared and get_current() should raise a DoesNotExist.
        self.assertIsInstance(Site.objects.get_current(), Site)
        Site.objects.all().delete()
        self.assertRaises(Site.DoesNotExist, Site.objects.get_current)

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_get_current_site(self):
        # Test that the correct Site object is returned
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "example.com",
            "SERVER_PORT": "80",
        }
        site = get_current_site(request)
        self.assertTrue(isinstance(site, Site))
        self.assertEqual(site.id, settings.SITE_ID)

        # Test that an exception is raised if the sites framework is installed
        # but there is no matching Site
        site.delete()
        self.assertRaises(ObjectDoesNotExist, get_current_site, request)

        # A RequestSite is returned if the sites framework is not installed
        with self.modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'}):
            site = get_current_site(request)
            self.assertTrue(isinstance(site, RequestSite))
            self.assertEqual(site.name, "example.com")

    def test_domain_name_with_whitespaces(self):
        # Regression for #17320
        # Domain names are not allowed contain whitespace characters
        site = Site(name="test name", domain="test test")
        self.assertRaises(ValidationError, site.full_clean)
        site.domain = "test\ttest"
        self.assertRaises(ValidationError, site.full_clean)
        site.domain = "test\ntest"
        self.assertRaises(ValidationError, site.full_clean)


class MiddlewareTest(TestCase):

    def test_request(self):
        """ Makes sure that the request has correct `site` attribute. """
        middleware = CurrentSiteMiddleware()
        request = HttpRequest()
        middleware.process_request(request)
        self.assertEqual(request.site.id, settings.SITE_ID)
