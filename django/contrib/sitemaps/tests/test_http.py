from __future__ import unicode_literals

import os
from datetime import date
from unittest import skipUnless

from django.conf import settings
from django.contrib.sitemaps import Sitemap, GenericSitemap
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings
from django.utils.formats import localize
from django.utils._os import upath
from django.utils.translation import activate, deactivate

from .base import TestModel, SitemapTestsBase


class HTTPSitemapTests(SitemapTestsBase):

    def test_simple_sitemap_index(self):
        "A simple sitemap index can be rendered"
        response = self.client.get('/simple/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    @override_settings(
        TEMPLATE_DIRS=(os.path.join(os.path.dirname(upath(__file__)), 'templates'),)
    )
    def test_simple_sitemap_custom_index(self):
        "A simple sitemap index can be rendered with a custom template"
        response = self.client.get('/simple/custom-index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<!-- This is a customised template -->
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)


    def test_simple_sitemap_section(self):
        "A simple sitemap section can be rendered"
        response = self.client.get('/simple/sitemap-simple.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    def test_simple_sitemap(self):
        "A simple sitemap can be rendered"
        response = self.client.get('/simple/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    @override_settings(
        TEMPLATE_DIRS=(os.path.join(os.path.dirname(upath(__file__)), 'templates'),)
    )
    def test_simple_custom_sitemap(self):
        "A simple sitemap can be rendered with a custom template"
        response = self.client.get('/simple/custom-sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<!-- This is a customised template -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    @skipUnless(settings.USE_I18N, "Internationalization is not enabled")
    @override_settings(USE_L10N=True)
    def test_localized_priority(self):
        "The priority value should not be localized (Refs #14164)"
        activate('fr')
        self.assertEqual('0,3', localize(0.3))

        # Retrieve the sitemap. Check that priorities
        # haven't been rendered in localized format
        response = self.client.get('/simple/sitemap.xml')
        self.assertContains(response, '<priority>0.5</priority>')
        self.assertContains(response, '<lastmod>%s</lastmod>' % date.today())
        deactivate()

    def test_requestsite_sitemap(self):
        # Make sure hitting the flatpages sitemap without the sites framework
        # installed doesn't raise an exception
        Site._meta.installed = False
        response = self.client.get('/simple/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://testserver/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % date.today()
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    @skipUnless("django.contrib.sites" in settings.INSTALLED_APPS,
                "django.contrib.sites app not installed.")
    def test_sitemap_get_urls_no_site_1(self):
        """
        Check we get ImproperlyConfigured if we don't pass a site object to
        Sitemap.get_urls and no Site objects exist
        """
        Site.objects.all().delete()
        self.assertRaises(ImproperlyConfigured, Sitemap().get_urls)

    def test_sitemap_get_urls_no_site_2(self):
        """
        Check we get ImproperlyConfigured when we don't pass a site object to
        Sitemap.get_urls if Site objects exists, but the sites framework is not
        actually installed.
        """
        Site._meta.installed = False
        self.assertRaises(ImproperlyConfigured, Sitemap().get_urls)

    def test_sitemap_item(self):
        """
        Check to make sure that the raw item is included with each
        Sitemap.get_url() url result.
        """
        test_sitemap = GenericSitemap({'queryset': TestModel.objects.all()})
        def is_testmodel(url):
            return isinstance(url['item'], TestModel)
        item_in_url_info = all(map(is_testmodel, test_sitemap.get_urls()))
        self.assertTrue(item_in_url_info)

    def test_cached_sitemap_index(self):
        """
        Check that a cached sitemap index can be rendered (#2713).
        """
        response = self.client.get('/cached/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/cached/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    def test_x_robots_sitemap(self):
        response = self.client.get('/simple/index.xml')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, noodp, noarchive')

        response = self.client.get('/simple/sitemap.xml')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, noodp, noarchive')
