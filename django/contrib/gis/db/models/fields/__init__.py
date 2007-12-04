from decimal import Decimal
from django.conf import settings
from django.db import connection
from django.contrib.gis.db.backend import GeoBackendField # these depend on the spatial database backend.
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.gis.measure import Distance
from django.contrib.gis.oldforms import WKTField

# Attempting to get the spatial reference system.
try:
    from django.contrib.gis.models import SpatialRefSys
except NotImplementedError:
    SpatialRefSys = None

#TODO: Flesh out widgets; consider adding support for OGR Geometry proxies.
class GeometryField(GeoBackendField):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    def __init__(self, srid=4326, spatial_index=True, dim=2, **kwargs):
        """
        The initialization function for geometry fields.  Takes the following
        as keyword arguments:

        srid:
         The spatial reference system identifier, an OGC standard.
         Defaults to 4326 (WGS84).

        spatial_index:
         Indicates whether to create a spatial index.  Defaults to True.
         Set this instead of 'db_index' for geographic fields since index
         creation is different for geometry columns.
                  
        dim:
         The number of dimensions for this geometry.  Defaults to 2.
        """

        # Backward-compatibility notice, this will disappear in future revisions.
        if 'index' in kwargs:
            from warnings import warn
            warn('The `index` keyword has been deprecated, please use the `spatial_index` keyword instead.')
            self._index = kwargs['index']
        else:
            self._index = spatial_index

        # Setting the SRID and getting the units.
        self._srid = srid
        if SpatialRefSys:
            # This doesn't work when we actually use: SpatialRefSys.objects.get(srid=srid)
            # Why?  `syncdb` fails to recognize installed geographic models when there's
            # an ORM query instantiated within a model field.  No matter, this works fine
            # too.
            cur = connection.cursor()
            qn = connection.ops.quote_name
            stmt = 'SELECT %(table)s.%(wkt_col)s FROM %(table)s WHERE (%(table)s.%(srid_col)s = %(srid)s)'
            stmt = stmt % {'table' : qn(SpatialRefSys._meta.db_table),
                           'wkt_col' : qn(SpatialRefSys.wkt_col()),
                           'srid_col' : qn('srid'),
                           'srid' : srid,
                           }
            cur.execute(stmt)
            row = cur.fetchone()
            self._unit, self._unit_name = SpatialRefSys.get_units(row[0])
            
        # Setting the dimension of the geometry field.
        self._dim = dim
        super(GeometryField, self).__init__(**kwargs) # Calling the parent initializtion function

    ### Routines specific to GeometryField ###
    def get_distance(self, dist):
        if isinstance(dist, Distance):
            return getattr(dist, Distance.unit_attname(self._unit_name))
        elif isinstance(dist, (int, float, Decimal)):
            # Assuming the distance is in the units of the field.
            return dist

    def get_geometry(self, value):
        """
        Retrieves the geometry, setting the default SRID from the given
        lookup parameters.
        """
        if isinstance(value, tuple): 
            geom = value[0]
        else:
            geom = value

        # When the input is not a GEOS geometry, attempt to construct one
        # from the given string input.
        if isinstance(geom, GEOSGeometry):
            pass
        elif isinstance(geom, basestring):
            try:
                geom = GEOSGeometry(geom)
            except GEOSException:
                raise ValueError('Could not create geometry from lookup value: %s' % str(value))
        else:
            raise TypeError('Cannot use parameter of `%s` type as lookup parameter.' % type(value))

        # Assigning the SRID value.
        geom.srid = self.get_srid(geom)
        
        return geom

    def get_srid(self, geom):
        """
        Has logic for retrieving the default SRID taking into account 
        the SRID of the field.
        """
        if geom.srid is None or (geom.srid == -1 and self._srid != -1):
            return self._srid
        else:
            return geom.srid

    ### Routines overloaded from Field ###
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
