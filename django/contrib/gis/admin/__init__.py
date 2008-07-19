from django.contrib.gis.admin.options import GeoModelAdmin
from django.contrib.gis.admin.sites import GeoAdminSite, site
from django.contrib.gis.admin.widgets import OpenLayersWidget

try:
    from django.contrib.gis.admin.options import OSMGeoAdmin
    HAS_OSM = True
except ImportError:
    HAS_OSM = False
