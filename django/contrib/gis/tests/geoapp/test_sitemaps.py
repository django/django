from __future__ import absolute_import

from io import BytesIO
from xml.dom import minidom
import zipfile

from django.conf import settings
from django.contrib.gis.geos import HAS_GEOS
from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils.unittest import skipUnless

if HAS_GEOS:
    from .models import City, Country


@skipUnless(HAS_GEOS and HAS_SPATIAL_DB, "Geos and spatial db are required.")
class GeoSitemapTest(TestCase):

    urls = 'django.contrib.gis.tests.geoapp.urls'

    def setUp(self):
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()
        self.old_Site_meta_installed = Site._meta.installed
        Site._meta.installed = True

    def tearDown(self):
        Site._meta.installed = self.old_Site_meta_installed

    def assertChildNodes(self, elem, expected):
        "Taken from syndication/tests.py."
        actual = set([n.nodeName for n in elem.childNodes])
        expected = set(expected)
        self.assertEqual(actual, expected)

    def test_geositemap_index(self):
        "Tests geographic sitemap index."
        # Getting the geo index.
        doc = minidom.parseString(self.client.get('/sitemap.xml').content)
        index = doc.firstChild
        self.assertEqual(index.getAttribute('xmlns'), 'http://www.sitemaps.org/schemas/sitemap/0.9')
        self.assertEqual(3, len(index.getElementsByTagName('sitemap')))

    def test_geositemap_kml(self):
        "Tests KML/KMZ geographic sitemaps."
        for kml_type in ('kml', 'kmz'):
            doc = minidom.parseString(self.client.get('/sitemaps/%s.xml' % kml_type).content)

            # Ensuring the right sitemaps namespaces are present.
            urlset = doc.firstChild
            self.assertEqual(urlset.getAttribute('xmlns'), 'http://www.sitemaps.org/schemas/sitemap/0.9')
            self.assertEqual(urlset.getAttribute('xmlns:geo'), 'http://www.google.com/geo/schemas/sitemap/1.0')

            urls = urlset.getElementsByTagName('url')
            self.assertEqual(2, len(urls)) # Should only be 2 sitemaps.
            for url in urls:
                self.assertChildNodes(url, ['loc', 'geo:geo'])
                # Making sure the 'geo:format' element was properly set.
                geo_elem = url.getElementsByTagName('geo:geo')[0]
                geo_format = geo_elem.getElementsByTagName('geo:format')[0]
                self.assertEqual(kml_type, geo_format.childNodes[0].data)

                # Getting the relative URL since we don't have a real site.
                kml_url = url.getElementsByTagName('loc')[0].childNodes[0].data.split('http://example.com')[1]

                if kml_type == 'kml':
                    kml_doc = minidom.parseString(self.client.get(kml_url).content)
                elif kml_type == 'kmz':
                    # Have to decompress KMZ before parsing.
                    buf = BytesIO(self.client.get(kml_url).content)
                    zf = zipfile.ZipFile(buf)
                    self.assertEqual(1, len(zf.filelist))
                    self.assertEqual('doc.kml', zf.filelist[0].filename)
                    kml_doc = minidom.parseString(zf.read('doc.kml'))

                # Ensuring the correct number of placemarks are in the KML doc.
                if 'city' in kml_url:
                    model = City
                elif 'country' in kml_url:
                    model = Country
                self.assertEqual(model.objects.count(), len(kml_doc.getElementsByTagName('Placemark')))

    def test_geositemap_georss(self):
        "Tests GeoRSS geographic sitemaps."
        from .feeds import feed_dict

        doc = minidom.parseString(self.client.get('/sitemaps/georss.xml').content)

        # Ensuring the right sitemaps namespaces are present.
        urlset = doc.firstChild
        self.assertEqual(urlset.getAttribute('xmlns'), 'http://www.sitemaps.org/schemas/sitemap/0.9')
        self.assertEqual(urlset.getAttribute('xmlns:geo'), 'http://www.google.com/geo/schemas/sitemap/1.0')

        # Making sure the correct number of feed URLs were included.
        urls = urlset.getElementsByTagName('url')
        self.assertEqual(len(feed_dict), len(urls))

        for url in urls:
            self.assertChildNodes(url, ['loc', 'geo:geo'])
            # Making sure the 'geo:format' element was properly set to 'georss'.
            geo_elem = url.getElementsByTagName('geo:geo')[0]
            geo_format = geo_elem.getElementsByTagName('geo:format')[0]
            self.assertEqual('georss', geo_format.childNodes[0].data)
