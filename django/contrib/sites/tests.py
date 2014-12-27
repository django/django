from __future__ import unicode_literals

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import router
from django.http import HttpRequest
from django.test import TestCase, modify_settings, override_settings

from .management import create_default_site
from .middleware import CurrentSiteMiddleware
from .models import Site
from .requests import RequestSite
from .shortcuts import get_current_site


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
class SitesFrameworkTests(TestCase):

    def setUp(self):
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

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


class JustOtherRouter(object):
    def allow_migrate(self, db, model):
        return db == 'other'


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
class CreateDefaultSiteTests(TestCase):
    multi_db = True

    def setUp(self):
        self.app_config = apps.get_app_config('sites')
        # Delete the site created as part of the default migration process.
        Site.objects.all().delete()

    def test_basic(self):
        """
        #15346, #15573 - create_default_site() creates an example site only if
        none exist.
        """
        create_default_site(self.app_config, verbosity=0)
        self.assertEqual(Site.objects.count(), 1)

        create_default_site(self.app_config, verbosity=0)
        self.assertEqual(Site.objects.count(), 1)

    def test_multi_db(self):
        """
        #16353, #16828 - The default site creation should respect db routing.
        """
        old_routers = router.routers
        router.routers = [JustOtherRouter()]
        try:
            create_default_site(self.app_config, using='default', verbosity=0)
            create_default_site(self.app_config, using='other', verbosity=0)
            self.assertFalse(Site.objects.using('default').exists())
            self.assertTrue(Site.objects.using('other').exists())
        finally:
            router.routers = old_routers

    def test_save_another(self):
        """
        #17415 - Another site can be created right after the default one.

        On some backends the sequence needs to be reset after saving with an
        explicit ID. Test that there isn't a sequence collisions by saving
        another site. This test is only meaningful with databases that use
        sequences for automatic primary keys such as PostgreSQL and Oracle.
        """
        create_default_site(self.app_config, verbosity=0)
        Site(domain='example2.com', name='example2.com').save()


class MiddlewareTest(TestCase):

    def test_request(self):
        """ Makes sure that the request has correct `site` attribute. """
        middleware = CurrentSiteMiddleware()
        request = HttpRequest()
        middleware.process_request(request)
        self.assertEqual(request.site.id, settings.SITE_ID)
