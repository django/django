# Geo-enabled Sitemap classes.
from django.contrib.gis.sitemaps.georss import GeoRSSSitemap
from django.contrib.gis.sitemaps.kml import KMLSitemap, KMZSitemap

__all__ = ['GeoRSSSitemap', 'KMLSitemap', 'KMZSitemap']
