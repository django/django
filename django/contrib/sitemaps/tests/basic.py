from datetime import date
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils.unittest import skipUnless
from django.utils.formats import localize
from django.utils.translation import activate, deactivate


class SitemapTests(TestCase):
    urls = 'django.contrib.sitemaps.tests.urls'

    def setUp(self):
        self.old_USE_L10N = settings.USE_L10N
        self.old_Site_meta_installed = Site._meta.installed
        # Create a user that will double as sitemap content
        User.objects.create_user('testuser', 'test@example.com', 's3krit')

    def tearDown(self):
        settings.USE_L10N = self.old_USE_L10N
        Site._meta.installed = self.old_Site_meta_installed

    def test_simple_sitemap(self):
        "A simple sitemap can be rendered"
        # Retrieve the sitemap.
        response = self.client.get('/simple/sitemap.xml')
        # Check for all the important bits:
        self.assertEquals(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://example.com/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % date.today().strftime('%Y-%m-%d'))

    def test_localized_priority(self):
        "The priority value should not be localized (Refs #14164)"
        # Localization should be active
        settings.USE_L10N = True
        activate('fr')
        self.assertEqual(u'0,3', localize(0.3))

        # Retrieve the sitemap. Check that priorities
        # haven't been rendered in localized format
        response = self.client.get('/simple/sitemap.xml')
        self.assertContains(response, '<priority>0.5</priority>')
        self.assertContains(response, '<lastmod>%s</lastmod>' % date.today().strftime('%Y-%m-%d'))
        deactivate()

    def test_generic_sitemap(self):
        "A minimal generic sitemap can be rendered"
        # Retrieve the sitemap.
        response = self.client.get('/generic/sitemap.xml')

        expected = ''
        for username in User.objects.values_list("username", flat=True):
            expected += "<url><loc>http://example.com/users/%s/</loc></url>" %username
        # Check for all the important bits:
        self.assertEquals(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
""" %expected)

    @skipUnless("django.contrib.flatpages" in settings.INSTALLED_APPS, "django.contrib.flatpages app not installed.")
    def test_flatpage_sitemap(self):
        "Basic FlatPage sitemap test"

        # Import FlatPage inside the test so that when django.contrib.flatpages
        # is not installed we don't get problems trying to delete Site
        # objects (FlatPage has an M2M to Site, Site.delete() tries to
        # delete related objects, but the M2M table doesn't exist.
        from django.contrib.flatpages.models import FlatPage

        public = FlatPage.objects.create(
            url=u'/public/',
            title=u'Public Page',
            enable_comments=True,
            registration_required=False,
        )
        public.sites.add(settings.SITE_ID)
        private = FlatPage.objects.create(
            url=u'/private/',
            title=u'Private Page',
            enable_comments=True,
            registration_required=True
        )
        private.sites.add(settings.SITE_ID)
        response = self.client.get('/flatpages/sitemap.xml')
        # Public flatpage should be in the sitemap
        self.assertContains(response, '<loc>http://example.com%s</loc>' % public.url)
        # Private flatpage should not be in the sitemap
        self.assertNotContains(response, '<loc>http://example.com%s</loc>' % private.url)

    def test_requestsite_sitemap(self):
        # Make sure hitting the flatpages sitemap without the sites framework
        # installed doesn't raise an exception
        Site._meta.installed = False
        # Retrieve the sitemap.
        response = self.client.get('/simple/sitemap.xml')
        # Check for all the important bits:
        self.assertEquals(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://testserver/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % date.today().strftime('%Y-%m-%d'))

    def test_sitemap_get_urls_no_site_1(self):
        """
        Check we get ImproperlyConfigured if we don't pass a site object to
        Sitemap.get_urls and no Site objects exist
        """
        Site._meta.installed = True
        Site.objects.all().delete()
        self.assertRaises(ImproperlyConfigured, Sitemap().get_urls)

    def test_sitemap_get_urls_no_site_2(self):
        """
        Check we get ImproperlyConfigured when we don't pass a site object to
        Sitemap.get_urls if Site objects exists, but the sites framework is not
        actually installed.
        """
        Site.objects.get_current()
        Site._meta.installed = False
        self.assertRaises(ImproperlyConfigured, Sitemap().get_urls)
