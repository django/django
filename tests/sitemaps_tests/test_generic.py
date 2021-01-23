from datetime import datetime

from django.contrib.sitemaps import GenericSitemap
from django.test import override_settings

from .base import SitemapTestsBase
from .models import TestModel


@override_settings(ABSOLUTE_URL_OVERRIDES={})
class GenericViewsSitemapTests(SitemapTestsBase):

    def test_generic_sitemap_attributes(self):
        datetime_value = datetime.now()
        queryset = TestModel.objects.all()
        generic_sitemap = GenericSitemap(
            info_dict={
                'queryset': queryset,
                'date_field': datetime_value,
            },
            priority=0.6,
            changefreq='monthly',
            protocol='https',
        )
        attr_values = (
            ('date_field', datetime_value),
            ('priority', 0.6),
            ('changefreq', 'monthly'),
            ('protocol', 'https'),
        )
        for attr_name, expected_value in attr_values:
            with self.subTest(attr_name=attr_name):
                self.assertEqual(getattr(generic_sitemap, attr_name), expected_value)
        self.assertCountEqual(generic_sitemap.queryset, queryset)

    def test_generic_sitemap(self):
        "A minimal generic sitemap can be rendered"
        response = self.client.get('/generic/sitemap.xml')
        expected = ''
        for pk in TestModel.objects.values_list("id", flat=True):
            expected += "<url><loc>%s/testmodel/%s/</loc></url>" % (self.base_url, pk)
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
%s
</urlset>
""" % expected
        self.assertXMLEqual(response.content.decode(), expected_content)

    def test_generic_sitemap_lastmod(self):
        test_model = TestModel.objects.first()
        TestModel.objects.update(lastmod=datetime(2013, 3, 13, 10, 0, 0))
        response = self.client.get('/generic-lastmod/sitemap.xml')
        expected_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
<url><loc>%s/testmodel/%s/</loc><lastmod>2013-03-13</lastmod></url>
</urlset>
""" % (self.base_url, test_model.pk)
        self.assertXMLEqual(response.content.decode(), expected_content)
        self.assertEqual(response.headers['Last-Modified'], 'Wed, 13 Mar 2013 10:00:00 GMT')
