from django.db.models.fields import Field
from django.db.models.sql.expressions import SQLEvaluator
from django.utils.translation import ugettext_lazy as _
from django.contrib.gis import forms
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.contrib.gis.geometry.backend import Geometry, GeometryException

# Local cache of the spatial_ref_sys table, which holds SRID data for each
# spatial database alias. This cache exists so that the database isn't queried
# for SRID info each time a distance query is constructed.
_srid_cache = {}

def get_srid_info(srid, connection):
    """
    Returns the units, unit name, and spheroid WKT associated with the
    given SRID from the `spatial_ref_sys` (or equivalent) spatial database
    table for the given database connection.  These results are cached.
    """
    global _srid_cache

    try:
        # The SpatialRefSys model for the spatial backend.
        SpatialRefSys = connection.ops.spatial_ref_sys()
    except NotImplementedError:
        # No `spatial_ref_sys` table in spatial backend (e.g., MySQL).
        return None, None, None

    if not connection.alias in _srid_cache:
        # Initialize SRID dictionary for database if it doesn't exist.
        _srid_cache[connection.alias] = {}

    if not srid in _srid_cache[connection.alias]:
        # Use `SpatialRefSys` model to query for spatial reference info.
        sr = SpatialRefSys.objects.using(connection.alias).get(srid=srid)
        units, units_name = sr.units
        spheroid = SpatialRefSys.get_spheroid(sr.wkt)
        _srid_cache[connection.alias][srid] = (units, units_name, spheroid)

    return _srid_cache[connection.alias][srid]

class GeometryField(Field):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    geom_type = 'GEOMETRY'

    # Geodetic units.
    geodetic_units = ('Decimal Degree', 'degree')

    description = _("The base GIS field -- maps to the OpenGIS Specification Geometry type.")

    def __init__(self, verbose_name=None, srid=4326, spatial_index=True, dim=2,
                 geography=False, **kwargs):
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

        extent:
         Customize the extent, in a 4-tuple of WGS 84 coordinates, for the
         geometry field entry in the `USER_SDO_GEOM_METADATA` table.  Defaults
         to (-180.0, -90.0, 180.0, 90.0).

        tolerance:
         Define the tolerance, in meters, to use for the geometry field
         entry in the `USER_SDO_GEOM_METADATA` table.  Defaults to 0.05.
        """

        # Setting the index flag with the value of the `spatial_index` keyword.
        self.spatial_index = spatial_index

        # Setting the SRID and getting the units.  Unit information must be
        # easily available in the field instance for distance queries.
        self.srid = srid

        # Setting the dimension of the geometry field.
        self.dim = dim

        # Setting the verbose_name keyword argument with the positional
        # first parameter, so this works like normal fields.
        kwargs['verbose_name'] = verbose_name

        # Is this a geography rather than a geometry column?
        self.geography = geography

        # Oracle-specific private attributes for creating the entrie in
        # `USER_SDO_GEOM_METADATA`
        self._extent = kwargs.pop('extent', (-180.0, -90.0, 180.0, 90.0))
        self._tolerance = kwargs.pop('tolerance', 0.05)

        super(GeometryField, self).__init__(**kwargs)

    # The following functions are used to get the units, their name, and
    # the spheroid corresponding to the SRID of the GeometryField.
    def _get_srid_info(self, connection):
        # Get attributes from `get_srid_info`.
        self._units, self._units_name, self._spheroid = get_srid_info(self.srid, connection)

    def spheroid(self, connection):
        if not hasattr(self, '_spheroid'):
            self._get_srid_info(connection)
        return self._spheroid

    def units(self, connection):
        if not hasattr(self, '_units'):
            self._get_srid_info(connection)
        return self._units

    def units_name(self, connection):
        if not hasattr(self, '_units_name'):
            self._get_srid_info(connection)
        return self._units_name

    ### Routines specific to GeometryField ###
    def geodetic(self, connection):
        """
        Returns true if this field's SRID corresponds with a coordinate
        system that uses non-projected units (e.g., latitude/longitude).
        """
        return self.units_name(connection) in self.geodetic_units

    def get_distance(self, value, lookup_type, connection):
        """
        Returns a distance number in units of the field.  For example, if
        `D(km=1)` was passed in and the units of the field were in meters,
        then 1000 would be returned.
        """
        return connection.ops.get_distance(self, value, lookup_type)

    def get_prep_value(self, value):
        """
        Spatial lookup values are either a parameter that is (or may be
        converted to) a geometry, or a sequence of lookup values that
        begins with a geometry.  This routine will setup the geometry
        value properly, and preserve any other lookup parameters before
        returning to the caller.
        """
        if isinstance(value, SQLEvaluator):
            return value
        elif isinstance(value, (tuple, list)):
            geom = value[0]
            seq_value = True
        else:
            geom = value
            seq_value = False

        # When the input is not a GEOS geometry, attempt to construct one
        # from the given string input.
        if isinstance(geom, Geometry):
            pass
        elif isinstance(geom, basestring) or hasattr(geom, '__geo_interface__'):
            try:
                geom = Geometry(geom)
            except GeometryException:
                raise ValueError('Could not create geometry from lookup value.')
        else:
            raise ValueError('Cannot use object with type %s for a geometry lookup parameter.' % type(geom).__name__)

        # Assigning the SRID value.
        geom.srid = self.get_srid(geom)

        if seq_value:
            lookup_val = [geom]
            lookup_val.extend(value[1:])
            return tuple(lookup_val)
        else:
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
        setattr(cls, self.attname, GeometryProxy(Geometry, self))

    def db_type(self, connection):
        return connection.ops.geo_db_type(self)

    def formfield(self, **kwargs):
        defaults = {'form_class' : forms.GeometryField,
                    'null' : self.null,
                    'geom_type' : self.geom_type,
                    'srid' : self.srid,
                    }
        defaults.update(kwargs)
        return super(GeometryField, self).formfield(**defaults)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        """
        Prepare for the database lookup, and return any spatial parameters
        necessary for the query.  This includes wrapping any geometry
        parameters with a backend-specific adapter and formatting any distance
        parameters into the correct units for the coordinate system of the
        field.
        """
        if lookup_type in connection.ops.gis_terms:
            # special case for isnull lookup
            if lookup_type == 'isnull':
                return []

            # Populating the parameters list, and wrapping the Geometry
            # with the Adapter of the spatial backend.
            if isinstance(value, (tuple, list)):
                params = [connection.ops.Adapter(value[0])]
                if lookup_type in connection.ops.distance_functions:
                    # Getting the distance parameter in the units of the field.
                    params += self.get_distance(value[1:], lookup_type, connection)
                elif lookup_type in connection.ops.truncate_params:
                    # Lookup is one where SQL parameters aren't needed from the
                    # given lookup value.
                    pass
                else:
                    params += value[1:]
            elif isinstance(value, SQLEvaluator):
                params = []
            else:
                params = [connection.ops.Adapter(value)]

            return params
        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'isnull':
            return bool(value)
        else:
            return self.get_prep_value(value)

    def get_db_prep_save(self, value, connection):
        "Prepares the value for saving in the database."
        if value is None:
            return None
        else:
            return connection.ops.Adapter(self.get_prep_value(value))

    def get_placeholder(self, value, connection):
        """
        Returns the placeholder for the geometry column for the
        given value.
        """
        return connection.ops.get_geom_placeholder(self, value)

# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    geom_type = 'POINT'
    description = _("Point")

class LineStringField(GeometryField):
    geom_type = 'LINESTRING'
    description = _("Line string")

class PolygonField(GeometryField):
    geom_type = 'POLYGON'
    description = _("Polygon")

class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'
    description = _("Multi-point")

class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'
    description = _("Multi-line string")

class MultiPolygonField(GeometryField):
    geom_type = 'MULTIPOLYGON'
    description = _("Multi polygon")

class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'
    description = _("Geometry collection")
