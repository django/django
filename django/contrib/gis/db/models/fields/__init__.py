from django.conf import settings
from django.contrib.gis.db.backend import GeoBackendField, GeometryProxy # these depend on the spatial database backend.
from django.contrib.gis.oldforms import WKTField
from django.contrib.gis.geos import GEOSGeometry

#TODO: Flesh out widgets; consider adding support for OGR Geometry proxies.
class GeometryField(GeoBackendField):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    def __init__(self, srid=4326, index=True, dim=2, **kwargs):
        """The initialization function for geometry fields.  Takes the following
        as keyword arguments:

          srid  - The spatial reference system identifier.  An OGC standard.
                  Defaults to 4326 (WGS84)

          index - Indicates whether to create a GiST index.  Defaults to True.
                  Set this instead of 'db_index' for geographic fields since index
                  creation is different for geometry columns.
                  
          dim   - The number of dimensions for this geometry.  Defaults to 2.
        """
        self._index = index
        self._srid = srid
        self._dim = dim
        super(GeometryField, self).__init__(**kwargs) # Calling the parent initializtion function

    def contribute_to_class(self, cls, name):
        super(GeometryField, self).contribute_to_class(cls, name)

        # Setup for lazy-instantiated GEOSGeometry object.
        setattr(cls, self.attname, GeometryProxy(GEOSGeometry, self))
        
    def get_manipulator_field_objs(self):
        "Using the WKTField (defined above) to be our manipulator."
        return [WKTField]

# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    _geom = 'POINT'

class LineStringField(GeometryField):
    _geom = 'LINESTRING'

class PolygonField(GeometryField):
    _geom = 'POLYGON'

class MultiPointField(GeometryField):
    _geom = 'MULTIPOINT'

class MultiLineStringField(GeometryField):
    _geom = 'MULTILINESTRING'

class MultiPolygonField(GeometryField):
    _geom = 'MULTIPOLYGON'

class GeometryCollectionField(GeometryField):
    _geom = 'GEOMETRYCOLLECTION'
