from __future__ import unicode_literals

import zipfile
from io import BytesIO
from xml.dom import minidom

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase, modify_settings, override_settings

from .models import City, Country


@modify_settings(INSTALLED_APPS={'append': ['django.contrib.sites', 'django.contrib.sitemaps']})
@override_settings(ROOT_URLCONF='gis_tests.geoapp.urls')
class GeoSitemapTest(TestCase):

    def setUp(self):
        super(GeoSitemapTest, self).setUp()
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

    def assertChildNodes(self, elem, expected):
        "Taken from syndication/tests.py."
        actual = set(n.nodeName for n in elem.childNodes)
        expected = set(expected)
        self.assertEqual(actual, expected)

    def test_geositemap_kml(self):
        "Tests KML/KMZ geographic sitemaps."
        for kml_type in ('kml', 'kmz'):
            doc = minidom.parseString(self.client.get('/sitemaps/%s.xml' % kml_type).content)

            # Ensuring the right sitemaps namespace is present.
            urlset = doc.firstChild
            self.assertEqual(urlset.getAttribute('xmlns'), 'http://www.sitemaps.org/schemas/sitemap/0.9')

            urls = urlset.getElementsByTagName('url')
            self.assertEqual(2, len(urls))  # Should only be 2 sitemaps.
            for url in urls:
                self.assertChildNodes(url, ['loc'])

                # Getting the relative URL since we don't have a real site.
                kml_url = url.getElementsByTagName('loc')[0].childNodes[0].data.split('http://example.com')[1]

                if kml_type == 'kml':
                    kml_doc = minidom.parseString(self.client.get(kml_url).content)
                elif kml_type == 'kmz':
                    # Have to decompress KMZ before parsing.
                    buf = BytesIO(self.client.get(kml_url).content)
                    with zipfile.ZipFile(buf) as zf:
                        self.assertEqual(1, len(zf.filelist))
                        self.assertEqual('doc.kml', zf.filelist[0].filename)
                        kml_doc = minidom.parseString(zf.read('doc.kml'))

                # Ensuring the correct number of placemarks are in the KML doc.
                if 'city' in kml_url:
                    model = City
                elif 'country' in kml_url:
                    model = Country
                self.assertEqual(model.objects.count(), len(kml_doc.getElementsByTagName('Placemark')))
