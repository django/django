from __future__ import unicode_literals

from datetime import date

from django.test import ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango110Warning

from .base import SitemapTestsBase


@override_settings(ROOT_URLCONF='sitemaps_tests.urls.https')
class HTTPSSitemapTests(SitemapTestsBase):
    protocol = 'https'

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_secure_sitemap_index(self):
        "A secure sitemap index can be rendered"
        # The URL for views.sitemap in tests/urls/https.py has been updated
        # with a name but since reversing by Python path is tried first
        # before reversing by name and works since we're giving
        # name='django.contrib.sitemaps.views.sitemap', we need to silence
        # the erroneous warning until reversing by dotted path is removed.
        # The test will work without modification when it's removed.
        response = self.client.get('/secure/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/secure/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    def test_secure_sitemap_section(self):
        "A secure sitemap section can be rendered"
        response = self.client.get('/secure/sitemap-simple.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today())
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)


@override_settings(SECURE_PROXY_SSL_HEADER=False)
class HTTPSDetectionSitemapTests(SitemapTestsBase):
    extra = {'wsgi.url_scheme': 'https'}

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_sitemap_index_with_https_request(self):
        "A sitemap index requested in HTTPS is rendered with HTTPS links"
        # The URL for views.sitemap in tests/urls/https.py has been updated
        # with a name but since reversing by Python path is tried first
        # before reversing by name and works since we're giving
        # name='django.contrib.sitemaps.views.sitemap', we need to silence
        # the erroneous warning until reversing by dotted path is removed.
        # The test will work without modification when it's removed.
        response = self.client.get('/simple/index.xml', **self.extra)
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url.replace('http://', 'https://')
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    def test_sitemap_section_with_https_request(self):
        "A sitemap section requested in HTTPS is rendered with HTTPS links"
        response = self.client.get('/simple/sitemap-simple.xml', **self.extra)
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url.replace('http://', 'https://'), date.today())
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)
