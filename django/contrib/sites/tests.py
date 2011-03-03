from django.conf import settings
from django.contrib.sites.models import Site, RequestSite, get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.test import TestCase


class SitesFrameworkTests(TestCase):

    def setUp(self):
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()
        self.old_Site_meta_installed = Site._meta.installed
        Site._meta.installed = True

    def tearDown(self):
        Site._meta.installed = self.old_Site_meta_installed

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
        self.assertEqual(u"example.com", site.name)
        s2 = Site.objects.get(id=settings.SITE_ID)
        s2.name = "Example site"
        s2.save()
        site = Site.objects.get_current()
        self.assertEqual(u"Example site", site.name)

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
        Site._meta.installed = False
        site = get_current_site(request)
        self.assertTrue(isinstance(site, RequestSite))
        self.assertEqual(site.name, u"example.com")
