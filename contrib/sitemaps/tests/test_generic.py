from __future__ import unicode_literals

from django.test import override_settings

from .base import TestModel, SitemapTestsBase


@override_settings(ABSOLUTE_URL_OVERRIDES={})
class GenericViewsSitemapTests(SitemapTestsBase):

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
