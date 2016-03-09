from __future__ import unicode_literals

from django.test import override_settings

from .base import SitemapTestsBase
from .models import TestModel


@override_settings(ABSOLUTE_URL_OVERRIDES={})
class GenericViewsSitemapTests(SitemapTestsBase):

    def test_generic_sitemap_index(self):
        "A minimal generic sitemap index can be rendered"
        response = self.client.get('/generic/index.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>http://example.com/simple/sitemap-generic.xml</loc><lastmod>1799-01-31T23:59:59-05:51</lastmod></sitemap>
</sitemapindex>
"""
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)

    def test_generic_sitemap(self):
        "A minimal generic sitemap can be rendered"
        response = self.client.get('/generic/sitemap.xml')
        expected = ''
        for pk in TestModel.objects.values_list("id", flat=True):
            expected += "<url><loc>%s/testmodel/%s/</loc></url>" % (self.base_url, pk)
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
""" % expected
        self.assertXMLEqual(response.content.decode('utf-8'), expected_content)
