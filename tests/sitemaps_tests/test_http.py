import os
from datetime import date
from unittest import skipUnless

from django.apps import apps
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test import modify_settings, override_settings
from django.utils.formats import localize
from django.utils.translation import activate, deactivate

from .base import SitemapTestsBase
from .models import TestModel


class HTTPSitemapTests(SitemapTestsBase):

    def test_simple_sitemap_index(self):
        "A simple sitemap index can be rendered"
        response = self.client.get('/simple/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode(), expected_content)

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
    }])
    def test_simple_sitemap_custom_index(self):
        "A simple sitemap index can be rendered with a custom template"
        response = self.client.get('/simple/custom-index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<!-- This is a customised template -->
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_simple_sitemap_section(self):
        "A simple sitemap section can be rendered"
        response = self.client.get('/simple/sitemap-simple.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_simple_sitemap(self):
        "A simple sitemap can be rendered"
        response = self.client.get('/simple/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode(), expected_content)

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
    }])
    def test_simple_custom_sitemap(self):
        "A simple sitemap can be rendered with a custom template"
        response = self.client.get('/simple/custom-sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<!-- This is a customised template -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_sitemap_last_modified(self):
        "Last-Modified header is set correctly"
        response = self.client.get('/lastmod/sitemap.xml')
        self.assertEqual(response['Last-Modified'], 'Wed, 13 Mar 2013 10:00:00 GMT')

    def test_sitemap_last_modified_date(self):
        """
        The Last-Modified header should be support dates (without time).
        """
        response = self.client.get('/lastmod/date-sitemap.xml')
        self.assertEqual(response['Last-Modified'], 'Wed, 13 Mar 2013 00:00:00 GMT')

    def test_sitemap_last_modified_tz(self):
        """
        The Last-Modified header should be converted from timezone aware dates
        to GMT.
        """
        response = self.client.get('/lastmod/tz-sitemap.xml')
        self.assertEqual(response['Last-Modified'], 'Wed, 13 Mar 2013 15:00:00 GMT')

    def test_sitemap_last_modified_missing(self):
        "Last-Modified header is missing when sitemap has no lastmod"
        response = self.client.get('/generic/sitemap.xml')
        self.assertFalse(response.has_header('Last-Modified'))

    def test_sitemap_last_modified_mixed(self):
        "Last-Modified header is omitted when lastmod not on all items"
        response = self.client.get('/lastmod-mixed/sitemap.xml')
        self.assertFalse(response.has_header('Last-Modified'))

    def test_sitemaps_lastmod_mixed_ascending_last_modified_missing(self):
        """
        The Last-Modified header is omitted when lastmod isn't found in all
        sitemaps. Test sitemaps are sorted by lastmod in ascending order.
        """
        response = self.client.get('/lastmod-sitemaps/mixed-ascending.xml')
        self.assertFalse(response.has_header('Last-Modified'))

    def test_sitemaps_lastmod_mixed_descending_last_modified_missing(self):
        """
        The Last-Modified header is omitted when lastmod isn't found in all
        sitemaps. Test sitemaps are sorted by lastmod in descending order.
        """
        response = self.client.get('/lastmod-sitemaps/mixed-descending.xml')
        self.assertFalse(response.has_header('Last-Modified'))

    def test_sitemaps_lastmod_ascending(self):
        """
        The Last-Modified header is set to the most recent sitemap lastmod.
        Test sitemaps are sorted by lastmod in ascending order.
        """
        response = self.client.get('/lastmod-sitemaps/ascending.xml')
        self.assertEqual(response['Last-Modified'], 'Sat, 20 Apr 2013 05:00:00 GMT')

    def test_sitemaps_lastmod_descending(self):
        """
        The Last-Modified header is set to the most recent sitemap lastmod.
        Test sitemaps are sorted by lastmod in descending order.
        """
        response = self.client.get('/lastmod-sitemaps/descending.xml')
        self.assertEqual(response['Last-Modified'], 'Sat, 20 Apr 2013 05:00:00 GMT')

    @skipUnless(settings.USE_I18N, "Internationalization is not enabled")
    @override_settings(USE_L10N=True)
    def test_localized_priority(self):
        "The priority value should not be localized (Refs #14164)"
        activate('fr')
        self.assertEqual('0,3', localize(0.3))

        # Priorities haven't been rendered in localized format.
        response = self.client.get('/simple/sitemap.xml')
        self.assertContains(response, '<priority>0.5</priority>')
        self.assertContains(response, '<lastmod>%s</lastmod>' % date.today())
        deactivate()

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_requestsite_sitemap(self):
        # Hitting the flatpages sitemap without the sites framework installed
        # doesn't raise an exception.
        response = self.client.get('/simple/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://testserver/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % date.today()
        self.assertXMLEqual(response.content.decode(), expected_content)

    @skipUnless(apps.is_installed('django.contrib.sites'),
                "django.contrib.sites app not installed.")
    def test_sitemap_get_urls_no_site_1(self):
        """
        Check we get ImproperlyConfigured if we don't pass a site object to
        Sitemap.get_urls and no Site objects exist
        """
        Site.objects.all().delete()
        with self.assertRaises(ImproperlyConfigured):
            Sitemap().get_urls()

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_sitemap_get_urls_no_site_2(self):
        """
        Check we get ImproperlyConfigured when we don't pass a site object to
        Sitemap.get_urls if Site objects exists, but the sites framework is not
        actually installed.
        """
        with self.assertRaises(ImproperlyConfigured):
            Sitemap().get_urls()

    def test_sitemap_item(self):
        """
        Check to make sure that the raw item is included with each
        Sitemap.get_url() url result.
        """
        test_sitemap = Sitemap()
        test_sitemap.items = TestModel.objects.order_by('pk').all

        def is_testmodel(url):
            return isinstance(url['item'], TestModel)
        item_in_url_info = all(map(is_testmodel, test_sitemap.get_urls()))
        self.assertTrue(item_in_url_info)

    def test_cached_sitemap_index(self):
        """
        A cached sitemap index can be rendered (#2713).
        """
        response = self.client.get('/cached/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/cached/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_x_robots_sitemap(self):
        response = self.client.get('/simple/index.xml')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, noodp, noarchive')

        response = self.client.get('/simple/sitemap.xml')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, noodp, noarchive')

    def test_empty_sitemap(self):
        response = self.client.get('/empty/sitemap.xml')
        self.assertEqual(response.status_code, 200)

    @override_settings(LANGUAGES=(('en', 'English'), ('pt', 'Portuguese')))
    def test_simple_i18nsitemap_index(self):
        "A simple i18n sitemap index can be rendered"
        response = self.client.get('/simple/i18n.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{0}/en/i18n/testmodel/{1}/</loc><changefreq>never</changefreq><priority>0.5</priority></url><url><loc>{0}/pt/i18n/testmodel/{1}/</loc><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""".format(self.base_url, self.i18n_model.pk)
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_sitemap_without_entries(self):
        response = self.client.get('/sitemap-without-entries/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

</urlset>"""
        self.assertXMLEqual(response.content.decode(), expected_content)
