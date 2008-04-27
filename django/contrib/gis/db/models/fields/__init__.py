from django.db import connection
# Getting the SpatialBackend container and the geographic quoting method.
from django.contrib.gis.db.backend import SpatialBackend, gqn
# GeometryProxy, GEOS, Distance, and oldforms imports.
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.gis.measure import Distance
from django.contrib.gis.oldforms import WKTField

# Attempting to get the spatial reference system.
try:
    from django.contrib.gis.models import SpatialRefSys
except ImportError:
    SpatialRefSys = None

#TODO: Flesh out widgets; consider adding support for OGR Geometry proxies.
class GeometryField(SpatialBackend.Field):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    # Geodetic units.
    geodetic_units = ('Decimal Degree', 'degree')

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

        # Setting the index flag with the value of the `spatial_index` keyword.
        self._index = spatial_index

        # Setting the SRID and getting the units.  Unit information must be 
        # easily available in the field instance for distance queries.
        self._srid = srid
        if SpatialRefSys:
            # Getting the spatial reference WKT associated with the SRID from the
            # `spatial_ref_sys` (or equivalent) spatial database table.
            #
            # The following doesn't work: SpatialRefSys.objects.get(srid=srid)
            # Why?  `syncdb` fails to recognize installed geographic models when there's
            # an ORM query instantiated within a model field.
            cur = connection.cursor()
            qn = connection.ops.quote_name
            stmt = 'SELECT %(table)s.%(wkt_col)s FROM %(table)s WHERE (%(table)s.%(srid_col)s = %(srid)s)'
            stmt = stmt % {'table' : qn(SpatialRefSys._meta.db_table),
                           'wkt_col' : qn(SpatialRefSys.wkt_col()),
                           'srid_col' : qn('srid'),
                           'srid' : srid,
                           }
            cur.execute(stmt)
            srs_wkt = cur.fetchone()[0]
            
            # Getting metadata associated with the spatial reference system identifier.
            # Specifically, getting the unit information and spheroid information 
            # (both required for distance queries).
            self._unit, self._unit_name = SpatialRefSys.get_units(srs_wkt)
            self._spheroid = SpatialRefSys.get_spheroid(srs_wkt)

        # Setting the dimension of the geometry field.
        self._dim = dim

        super(GeometryField, self).__init__(**kwargs) # Calling the parent initializtion function

    ### Routines specific to GeometryField ###
    @property
    def geodetic(self):
        return self._unit_name in self.geodetic_units

    def get_distance(self, dist, lookup_type):
        """
        Returns a distance number in units of the field.  For example, if 
        `D(km=1)` was passed in and the units of the field were in meters,
        then 1000 would be returned.
        """
        postgis = SpatialBackend.name == 'postgis'
        if isinstance(dist, Distance):
            if self.geodetic:
                # Won't allow Distance objects w/DWithin lookups on PostGIS.
                if postgis and lookup_type == 'dwithin':
                    raise TypeError('Only numeric values of degree units are allowed on geographic DWithin queries.')
                # Spherical distance calculation parameter should be in meters.
                dist_param = dist.m
            else:
                dist_param = getattr(dist, Distance.unit_attname(self._unit_name))
        else:
            # Assuming the distance is in the units of the field.
            dist_param = dist

        # Sphereical distance query; returning meters.
        if postgis and self.geodetic and lookup_type != 'dwithin':
            return [gqn(self._spheroid), dist_param]
        else:
            return [dist_param]

    def get_geometry(self, value):
        """
        Retrieves the geometry, setting the default SRID from the given
        lookup parameters.
        """
        if isinstance(value, (tuple, list)): 
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

    def get_db_prep_lookup(self, lookup_type, value):
        """
        Returns the spatial WHERE clause and associated parameters for the
        given lookup type and value.  The value will be prepared for database
        lookup (e.g., spatial transformation SQL will be added if necessary).
        """
        if lookup_type in SpatialBackend.gis_terms:
            # special case for isnull lookup
            if lookup_type == 'isnull': return [], []

            # Get the geometry with SRID; defaults SRID to that of the field
            # if it is None.
            geom = self.get_geometry(value)

            # Getting the WHERE clause list and the associated params list. The params 
            # list is populated with the Adaptor wrapping the GEOSGeometry for the 
            # backend.  The WHERE clause list contains the placeholder for the adaptor
            # (e.g. any transformation SQL).
            where = [self.get_placeholder(geom)]
            params = [SpatialBackend.Adaptor(geom)]

            if isinstance(value, (tuple, list)):
                if lookup_type in SpatialBackend.distance_functions:
                    # Getting the distance parameter in the units of the field.
                    where += self.get_distance(value[1], lookup_type)
                elif lookup_type in SpatialBackend.limited_where:
                    pass
                else:
                    # Otherwise, making sure any other parameters are properly quoted.
                    where += map(gqn, value[1:])
            return where, params
        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Prepares the value for saving in the database."
        if isinstance(value, GEOSGeometry):
            return SpatialBackend.Adaptor(value)
        elif value is None:
            return None
        else:
            raise TypeError('Geometry Proxy should only return GEOSGeometry objects or None.')

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
