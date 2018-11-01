from xml.dom import minidom

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase, modify_settings, override_settings

from .models import City


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
@override_settings(ROOT_URLCONF='gis_tests.geoapp.urls')
class GeoFeedTest(TestCase):
    fixtures = ['initial']

    def setUp(self):
        Site(id=settings.SITE_ID, domain="example.com", name="example.com").save()

    def assertChildNodes(self, elem, expected):
        "Taken from syndication/tests.py."
        actual = {n.nodeName for n in elem.childNodes}
        expected = set(expected)
        self.assertEqual(actual, expected)

    def test_geofeed_rss(self):
        "Tests geographic feeds using GeoRSS over RSSv2."
        # Uses `GEOSGeometry` in `item_geometry`
        doc1 = minidom.parseString(self.client.get('/feeds/rss1/').content)
        # Uses a 2-tuple in `item_geometry`
        doc2 = minidom.parseString(self.client.get('/feeds/rss2/').content)
        feed1, feed2 = doc1.firstChild, doc2.firstChild

        # Making sure the box got added to the second GeoRSS feed.
        self.assertChildNodes(feed2.getElementsByTagName('channel')[0],
                              ['title', 'link', 'description', 'language',
                               'lastBuildDate', 'item', 'georss:box', 'atom:link']
                              )

        # Incrementing through the feeds.
        for feed in [feed1, feed2]:
            # Ensuring the georss namespace was added to the <rss> element.
            self.assertEqual(feed.getAttribute('xmlns:georss'), 'http://www.georss.org/georss')
            chan = feed.getElementsByTagName('channel')[0]
            items = chan.getElementsByTagName('item')
            self.assertEqual(len(items), City.objects.count())

            # Ensuring the georss element was added to each item in the feed.
            for item in items:
                self.assertChildNodes(item, ['title', 'link', 'description', 'guid', 'georss:point'])

    def test_geofeed_atom(self):
        "Testing geographic feeds using GeoRSS over Atom."
        doc1 = minidom.parseString(self.client.get('/feeds/atom1/').content)
        doc2 = minidom.parseString(self.client.get('/feeds/atom2/').content)
        feed1, feed2 = doc1.firstChild, doc2.firstChild

        # Making sure the box got added to the second GeoRSS feed.
        self.assertChildNodes(feed2, ['title', 'link', 'id', 'updated', 'entry', 'georss:box'])

        for feed in [feed1, feed2]:
            # Ensuring the georsss namespace was added to the <feed> element.
            self.assertEqual(feed.getAttribute('xmlns:georss'), 'http://www.georss.org/georss')
            entries = feed.getElementsByTagName('entry')
            self.assertEqual(len(entries), City.objects.count())

            # Ensuring the georss element was added to each entry in the feed.
            for entry in entries:
                self.assertChildNodes(entry, ['title', 'link', 'id', 'summary', 'georss:point'])

    def test_geofeed_w3c(self):
        "Testing geographic feeds using W3C Geo."
        doc = minidom.parseString(self.client.get('/feeds/w3cgeo1/').content)
        feed = doc.firstChild
        # Ensuring the geo namespace was added to the <feed> element.
        self.assertEqual(feed.getAttribute('xmlns:geo'), 'http://www.w3.org/2003/01/geo/wgs84_pos#')
        chan = feed.getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')
        self.assertEqual(len(items), City.objects.count())

        # Ensuring the geo:lat and geo:lon element was added to each item in the feed.
        for item in items:
            self.assertChildNodes(item, ['title', 'link', 'description', 'guid', 'geo:lat', 'geo:lon'])

        # Boxes and Polygons aren't allowed in W3C Geo feeds.
        with self.assertRaises(ValueError):  # Box in <channel>
            self.client.get('/feeds/w3cgeo2/')
        with self.assertRaises(ValueError):  # Polygons in <entry>
            self.client.get('/feeds/w3cgeo3/')
