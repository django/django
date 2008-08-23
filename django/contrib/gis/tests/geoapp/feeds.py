from django.contrib.gis import feeds
from django.contrib.gis.tests.utils import mysql
from models import City, Country

class TestGeoRSS1(feeds.Feed):
    link = '/city/'
    title = 'Test GeoDjango Cities'

    def items(self):
        return City.objects.all()

    def item_link(self, item):
        return '/city/%s/' % item.pk

    def item_geometry(self, item):
        return item.point

class TestGeoRSS2(TestGeoRSS1):
    def geometry(self, obj):
        # This should attach a <georss:box> element for the extent of
        # of the cities in the database.  This tuple came from
        # calling `City.objects.extent()` -- we can't do that call here
        # because `extent` is not implemented for MySQL/Oracle.
        return (-123.30, -41.32, 174.78, 48.46)

    def item_geometry(self, item):
        # Returning a simple tuple for the geometry.
        return item.point.x, item.point.y

class TestGeoAtom1(TestGeoRSS1):
    feed_type = feeds.GeoAtom1Feed

class TestGeoAtom2(TestGeoRSS2):
    feed_type = feeds.GeoAtom1Feed

    def geometry(self, obj):
        # This time we'll use a 2-tuple of coordinates for the box.
        return ((-123.30, -41.32), (174.78, 48.46))

class TestW3CGeo1(TestGeoRSS1):
    feed_type = feeds.W3CGeoFeed

# The following feeds are invalid, and will raise exceptions.
class TestW3CGeo2(TestGeoRSS2):
    feed_type = feeds.W3CGeoFeed

class TestW3CGeo3(TestGeoRSS1):
    feed_type = feeds.W3CGeoFeed

    def item_geometry(self, item):
        from django.contrib.gis.geos import Polygon
        return Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))

# The feed dictionary to use for URLs.
feed_dict = {
    'rss1' : TestGeoRSS1,
    'rss2' : TestGeoRSS2,
    'atom1' : TestGeoAtom1,
    'atom2' : TestGeoAtom2,
    'w3cgeo1' : TestW3CGeo1,
    'w3cgeo2' : TestW3CGeo2,
    'w3cgeo3' : TestW3CGeo3,
}
