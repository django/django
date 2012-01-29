from datetime import date

from django.test.utils import override_settings

from .base import SitemapTestsBase

class HTTPSSitemapTests(SitemapTestsBase):
    protocol = 'https'
    urls = 'django.contrib.sitemaps.tests.urls.https'

    def test_secure_sitemap_index(self):
        "A secure sitemap index can be rendered"
        response = self.client.get('/secure/index.xml')
        self.assertEqual(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/secure/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url)

    def test_secure_sitemap_section(self):
        "A secure sitemap section can be rendered"
        response = self.client.get('/secure/sitemap-simple.xml')
        self.assertEqual(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url, date.today()))

#@override_settings(SECURE_PROXY_SSL_HEADER=False)
class HTTPSDetectionSitemapTests(SitemapTestsBase):
    extra = {'wsgi.url_scheme': 'https'}

    def test_sitemap_index_with_https_request(self):
        "A sitemap index requested in HTTPS is rendered with HTTPS links"
        response = self.client.get('/simple/index.xml', **self.extra)
        self.assertEqual(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>%s/simple/sitemap-simple.xml</loc></sitemap>
</sitemapindex>
""" % self.base_url.replace('http://', 'https://'))

    def test_sitemap_section_with_https_request(self):
        "A sitemap section requested in HTTPS is rendered with HTTPS links"
        response = self.client.get('/simple/sitemap-simple.xml', **self.extra)
        self.assertEqual(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>%s/location/</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % (self.base_url.replace('http://', 'https://'), date.today()))

HTTPSDetectionSitemapTests = override_settings(SECURE_PROXY_SSL_HEADER=False)(HTTPSDetectionSitemapTests)
