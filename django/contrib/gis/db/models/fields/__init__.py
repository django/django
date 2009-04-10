from django.contrib.gis import forms
# Getting the SpatialBackend container and the geographic quoting method.
from django.contrib.gis.db.backend import SpatialBackend, gqn
# GeometryProxy, GEOS, and Distance imports.
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.measure import Distance
# The `get_srid_info` function gets SRID information from the spatial
# reference system table w/o using the ORM.
from django.contrib.gis.models import get_srid_info

def deprecated_property(func):
    from warnings import warn
    warn('This attribute has been deprecated, please use "%s" instead.' % func.__name__[1:])
    return property(func)

# Local cache of the spatial_ref_sys table, which holds static data.
# This exists so that we don't have to hit the database each time.
SRID_CACHE = {}

class GeometryField(SpatialBackend.Field):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    geom_type = 'GEOMETRY'

    # Geodetic units.
    geodetic_units = ('Decimal Degree', 'degree')

    def __init__(self, verbose_name=None, srid=4326, spatial_index=True, dim=2, **kwargs):
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
        self.spatial_index = spatial_index

        # Setting the SRID and getting the units.  Unit information must be
        # easily available in the field instance for distance queries.
        self.srid = srid

        # units_cache, units_name_cache and _spheroid_cache are lazily loaded.
        self._units_cache = self._units_name_cache = self._spheroid_cache = None

        # Setting the dimension of the geometry field.
        self.dim = dim

        # Setting the verbose_name keyword argument with the positional
        # first parameter, so this works like normal fields.
        kwargs['verbose_name'] = verbose_name

        super(GeometryField, self).__init__(**kwargs) # Calling the parent initializtion function

    def _populate_srid_info(self):
        if self.srid not in SRID_CACHE:
            SRID_CACHE[self.srid] = get_srid_info(self.srid)
        self._units_cache, self._units_name_cache, self._spheroid_cache = SRID_CACHE[self.srid]

    def _get_units(self):
        if self._units_cache is None:
            self._populate_srid_info()
        return self._units_cache
    units = property(_get_units)

    def _get_units_name(self):
        if self._units_name_cache is None:
            self._populate_srid_info()
        return self._units_name_cache
    units_name = property(_get_units_name)

    def _get_spheroid(self):
        if self._spheroid_cache is None:
            self._populate_srid_info()
        return self._spheroid_cache
    _spheroid = property(_get_spheroid)

    # The following properties are for formerly private variables that are now
    # public for GeometryField.  Because of their use by third-party applications,
    # a deprecation warning is issued to notify them to use new attribute name.
    def _deprecated_warning(self, old_name, new_name):
        from warnings import warn
        warn('The `%s` attribute name is deprecated, please update your code to use `%s` instead.' %
             (old_name, new_name))

    @property
    def _geom(self):
        self._deprecated_warning('_geom', 'geom_type')
        return self.geom_type

    @property
    def _index(self):
        self._deprecated_warning('_index', 'spatial_index')
        return self.spatial_index

    @property
    def _srid(self):
        self._deprecated_warning('_srid', 'srid')
        return self.srid

    ### Routines specific to GeometryField ###
    @property
    def geodetic(self):
        """
        Returns true if this field's SRID corresponds with a coordinate
        system that uses non-projected units (e.g., latitude/longitude).
        """
        return self.units_name in self.geodetic_units

    def get_distance(self, dist_val, lookup_type):
        """
        Returns a distance number in units of the field.  For example, if
        `D(km=1)` was passed in and the units of the field were in meters,
        then 1000 would be returned.
        """
        # Getting the distance parameter and any options.
        if len(dist_val) == 1: dist, option = dist_val[0], None
        else: dist, option = dist_val

        if isinstance(dist, Distance):
            if self.geodetic:
                # Won't allow Distance objects w/DWithin lookups on PostGIS.
                if SpatialBackend.postgis and lookup_type == 'dwithin':
                    raise TypeError('Only numeric values of degree units are allowed on geographic DWithin queries.')
                # Spherical distance calculation parameter should be in meters.
                dist_param = dist.m
            else:
                dist_param = getattr(dist, Distance.unit_attname(self.units_name))
        else:
            # Assuming the distance is in the units of the field.
            dist_param = dist

        if SpatialBackend.postgis and self.geodetic and lookup_type != 'dwithin' and option == 'spheroid':
            # On PostGIS, by default `ST_distance_sphere` is used; but if the
            # accuracy of `ST_distance_spheroid` is needed than the spheroid
            # needs to be passed to the SQL stored procedure.
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
        if isinstance(geom, SpatialBackend.Geometry):
            pass
        elif isinstance(geom, basestring):
            try:
                geom = SpatialBackend.Geometry(geom)
            except SpatialBackend.GeometryException:
                raise ValueError('Could not create geometry from lookup value: %s' % str(value))
        else:
            raise TypeError('Cannot use parameter of `%s` type as lookup parameter.' % type(value))

        # Assigning the SRID value.
        geom.srid = self.get_srid(geom)

        return geom

    def get_srid(self, geom):
        """
        Returns the default SRID for the given geometry, taking into account
        the SRID set for the field.  For example, if the input geometry
        has no SRID, then that of the field will be returned.
        """
        gsrid = geom.srid # SRID of given geometry.
        if gsrid is None or self.srid == -1 or (gsrid == -1 and self.srid != -1):
            return self.srid
        else:
            return gsrid

    ### Routines overloaded from Field ###
    def contribute_to_class(self, cls, name):
        super(GeometryField, self).contribute_to_class(cls, name)

        # Setup for lazy-instantiated Geometry object.
        setattr(cls, self.attname, GeometryProxy(SpatialBackend.Geometry, self))

    def formfield(self, **kwargs):
        defaults = {'form_class' : forms.GeometryField,
                    'null' : self.null,
                    'geom_type' : self.geom_type,
                    'srid' : self.srid,
                    }
        defaults.update(kwargs)
        return super(GeometryField, self).formfield(**defaults)

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
            # list is populated with the Adaptor wrapping the Geometry for the
            # backend.  The WHERE clause list contains the placeholder for the adaptor
            # (e.g. any transformation SQL).
            where = [self.get_placeholder(geom)]
            params = [SpatialBackend.Adaptor(geom)]

            if isinstance(value, (tuple, list)):
                if lookup_type in SpatialBackend.distance_functions:
                    # Getting the distance parameter in the units of the field.
                    where += self.get_distance(value[1:], lookup_type)
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
        if value is None:
            return None
        else:
            return SpatialBackend.Adaptor(self.get_geometry(value))

# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    geom_type = 'POINT'

class LineStringField(GeometryField):
    geom_type = 'LINESTRING'

class PolygonField(GeometryField):
    geom_type = 'POLYGON'

class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'

class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'

class MultiPolygonField(GeometryField):
    geom_type = 'MULTIPOLYGON'

class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'
