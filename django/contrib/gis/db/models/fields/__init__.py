from django.contrib.gis.db.backend import GeoBackendField # depends on the spatial database backend.
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.oldforms import WKTField
from django.utils.functional import curry

#TODO: Flesh out widgets.
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

        # setup for lazy-instantiated GEOSGeometry objects
        setattr(cls, self.attname, GeometryProxy(self))

        # Adding needed accessor functions
        setattr(cls, 'get_%s_geos' % self.name, curry(cls._get_GEOM_geos, field=self))
        setattr(cls, 'get_%s_ogr' % self.name, curry(cls._get_GEOM_ogr, field=self, srid=self._srid))
        setattr(cls, 'get_%s_srid' % self.name, curry(cls._get_GEOM_srid, srid=self._srid))
        setattr(cls, 'get_%s_srs' % self.name, curry(cls._get_GEOM_srs, srid=self._srid))
        setattr(cls, 'get_%s_wkt' % self.name, curry(cls._get_GEOM_wkt, field=self))
        setattr(cls, 'get_%s_centroid' % self.name, curry(cls._get_GEOM_centroid, field=self))
        setattr(cls, 'get_%s_area' % self.name, curry(cls._get_GEOM_area, field=self))
        
    def get_internal_type(self):
        return "NoField"
                                                                
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
