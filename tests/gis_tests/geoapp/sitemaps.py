from django.contrib.gis.sitemaps import KMLSitemap, KMZSitemap

from .models import City, Country

sitemaps = {
    'kml': KMLSitemap([City, Country]),
    'kmz': KMZSitemap([City, Country]),
}
