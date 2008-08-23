from django.contrib.gis.sitemaps import GeoRSSSitemap, KMLSitemap, KMZSitemap
from models import City, Country
from feeds import feed_dict

sitemaps = {'kml' : KMLSitemap([City, Country]),
            'kmz' : KMZSitemap([City, Country]),
            'georss' : GeoRSSSitemap(feed_dict),
            }
