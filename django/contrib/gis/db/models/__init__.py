# Want to get everything from the 'normal' models package.
from django.db.models import *

# The GeoManager class.
from django.contrib.gis.db.models.manager import GeoManager

# The various PostGIS/OpenGIS enabled fields.
from django.contrib.gis.db.models.fields import \
     GeometryField, PointField, LineString, PolygonField, \
     MultiPointField, MultiLineStringField, MultiPolygonField, \
     GeometryCollectionField

