from __future__ import absolute_import

from django.contrib.gis.sitemaps import GeoRSSSitemap, KMLSitemap, KMZSitemap

from .feeds import feed_dict
from .models import City, Country


sitemaps = {'kml' : KMLSitemap([City, Country]),
            'kmz' : KMZSitemap([City, Country]),
            'georss' : GeoRSSSitemap(feed_dict),
            }
