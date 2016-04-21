from django.contrib.gis import forms
from django.contrib.gis.db.models.lookups import (
    RasterBandTransform, gis_lookups,
)
from django.contrib.gis.db.models.proxy import SpatialProxy
from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geometry.backend import Geometry, GeometryException
from django.core.exceptions import ImproperlyConfigured
from django.db.models.expressions import Expression
from django.db.models.fields import Field
from django.utils import six
from django.utils.translation import ugettext_lazy as _

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

    if connection.alias not in _srid_cache:
        # Initialize SRID dictionary for database if it doesn't exist.
        _srid_cache[connection.alias] = {}

    if srid not in _srid_cache[connection.alias]:
        # Use `SpatialRefSys` model to query for spatial reference info.
        sr = SpatialRefSys.objects.using(connection.alias).get(srid=srid)
        units, units_name = sr.units
        spheroid = SpatialRefSys.get_spheroid(sr.wkt)
        _srid_cache[connection.alias][srid] = (units, units_name, spheroid)

    return _srid_cache[connection.alias][srid]


class GeoSelectFormatMixin(object):
    def select_format(self, compiler, sql, params):
        """
        Returns the selection format string, depending on the requirements
        of the spatial backend.  For example, Oracle and MySQL require custom
        selection formats in order to retrieve geometries in OGC WKT. For all
        other fields a simple '%s' format string is returned.
        """
        connection = compiler.connection
        srid = compiler.query.get_context('transformed_srid')
        if srid:
            sel_fmt = '%s(%%s, %s)' % (connection.ops.transform, srid)
        else:
            sel_fmt = '%s'
        if connection.ops.select:
            # This allows operations to be done on fields in the SELECT,
            # overriding their values -- used by the Oracle and MySQL
            # spatial backends to get database values as WKT, and by the
            # `transform` method.
            sel_fmt = connection.ops.select % sel_fmt
        return sel_fmt % sql, params


class BaseSpatialField(Field):
    """
    The Base GIS Field.

    It's used as a base class for GeometryField and RasterField. Defines
    properties that are common to all GIS fields such as the characteristics
    of the spatial reference system of the field.
    """
    description = _("The base GIS field.")
    # Geodetic units.
    geodetic_units = ('decimal degree', 'degree')

    def __init__(self, verbose_name=None, srid=4326, spatial_index=True, **kwargs):
        """
        The initialization function for base spatial fields. Takes the following
        as keyword arguments:

        srid:
         The spatial reference system identifier, an OGC standard.
         Defaults to 4326 (WGS84).

        spatial_index:
         Indicates whether to create a spatial index.  Defaults to True.
         Set this instead of 'db_index' for geographic fields since index
         creation is different for geometry columns.
        """

        # Setting the index flag with the value of the `spatial_index` keyword.
        self.spatial_index = spatial_index

        # Setting the SRID and getting the units.  Unit information must be
        # easily available in the field instance for distance queries.
        self.srid = srid

        # Setting the verbose_name keyword argument with the positional
        # first parameter, so this works like normal fields.
        kwargs['verbose_name'] = verbose_name

        super(BaseSpatialField, self).__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(BaseSpatialField, self).deconstruct()
        # Always include SRID for less fragility; include spatial index if it's
        # not the default value.
        kwargs['srid'] = self.srid
        if self.spatial_index is not True:
            kwargs['spatial_index'] = self.spatial_index
        return name, path, args, kwargs

    def db_type(self, connection):
        return connection.ops.geo_db_type(self)

    # The following functions are used to get the units, their name, and
    # the spheroid corresponding to the SRID of the BaseSpatialField.
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

    def geodetic(self, connection):
        """
        Returns true if this field's SRID corresponds with a coordinate
        system that uses non-projected units (e.g., latitude/longitude).
        """
        units_name = self.units_name(connection)
        # Some backends like MySQL cannot determine units name. In that case,
        # test if srid is 4326 (WGS84), even if this is over-simplification.
        return units_name.lower() in self.geodetic_units if units_name else self.srid == 4326

    def get_placeholder(self, value, compiler, connection):
        """
        Returns the placeholder for the spatial column for the
        given value.
        """
        return connection.ops.get_geom_placeholder(self, value, compiler)

    def get_srid(self, obj):
        """
        Return the default SRID for the given geometry or raster, taking into
        account the SRID set for the field. For example, if the input geometry
        or raster doesn't have an SRID, then the SRID of the field will be
        returned.
        """
        srid = obj.srid  # SRID of given geometry.
        if srid is None or self.srid == -1 or (srid == -1 and self.srid != -1):
            return self.srid
        else:
            return srid

    def get_db_prep_save(self, value, connection):
        """
        Prepare the value for saving in the database.
        """
        if not value:
            return None
        else:
            return connection.ops.Adapter(self.get_prep_value(value))

    def get_prep_value(self, value):
        """
        Spatial lookup values are either a parameter that is (or may be
        converted to) a geometry or raster, or a sequence of lookup values
        that begins with a geometry or raster. This routine sets up the
        geometry or raster value properly and preserves any other lookup
        parameters.
        """
        from django.contrib.gis.gdal import GDALRaster

        value = super(BaseSpatialField, self).get_prep_value(value)
        # For IsValid lookups, boolean values are allowed.
        if isinstance(value, (Expression, bool)):
            return value
        elif isinstance(value, (tuple, list)):
            obj = value[0]
            seq_value = True
        else:
            obj = value
            seq_value = False

        # When the input is not a geometry or raster, attempt to construct one
        # from the given string input.
        if isinstance(obj, (Geometry, GDALRaster)):
            pass
        elif isinstance(obj, (bytes, six.string_types)) or hasattr(obj, '__geo_interface__'):
            try:
                obj = Geometry(obj)
            except (GeometryException, GDALException):
                try:
                    obj = GDALRaster(obj)
                except GDALException:
                    raise ValueError("Couldn't create spatial object from lookup value '%s'." % obj)
        elif isinstance(obj, dict):
            try:
                obj = GDALRaster(obj)
            except GDALException:
                raise ValueError("Couldn't create spatial object from lookup value '%s'." % obj)
        else:
            raise ValueError('Cannot use object with type %s for a spatial lookup parameter.' % type(obj).__name__)

        # Assigning the SRID value.
        obj.srid = self.get_srid(obj)

        if seq_value:
            lookup_val = [obj]
            lookup_val.extend(value[1:])
            return tuple(lookup_val)
        else:
            return obj

for klass in gis_lookups.values():
    BaseSpatialField.register_lookup(klass)


class GeometryField(GeoSelectFormatMixin, BaseSpatialField):
    """
    The base Geometry field -- maps to the OpenGIS Specification Geometry type.
    """
    description = _("The base Geometry field -- maps to the OpenGIS Specification Geometry type.")
    form_class = forms.GeometryField
    # The OpenGIS Geometry name.
    geom_type = 'GEOMETRY'

    def __init__(self, verbose_name=None, dim=2, geography=False, **kwargs):
        """
        The initialization function for geometry fields. In addition to the
        parameters from BaseSpatialField, it takes the following as keyword
        arguments:

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
        # Setting the dimension of the geometry field.
        self.dim = dim

        # Is this a geography rather than a geometry column?
        self.geography = geography

        # Oracle-specific private attributes for creating the entry in
        # `USER_SDO_GEOM_METADATA`
        self._extent = kwargs.pop('extent', (-180.0, -90.0, 180.0, 90.0))
        self._tolerance = kwargs.pop('tolerance', 0.05)

        super(GeometryField, self).__init__(verbose_name=verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(GeometryField, self).deconstruct()
        # Include kwargs if they're not the default values.
        if self.dim != 2:
            kwargs['dim'] = self.dim
        if self.geography is not False:
            kwargs['geography'] = self.geography
        return name, path, args, kwargs

    # ### Routines specific to GeometryField ###
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
        from django.contrib.gis.gdal import GDALRaster

        value = super(GeometryField, self).get_prep_value(value)
        if isinstance(value, (Expression, bool)):
            return value
        elif isinstance(value, (tuple, list)):
            geom = value[0]
            seq_value = True
        else:
            geom = value
            seq_value = False

        # When the input is not a GEOS geometry, attempt to construct one
        # from the given string input.
        if isinstance(geom, (Geometry, GDALRaster)):
            pass
        elif isinstance(geom, (bytes, six.string_types)) or hasattr(geom, '__geo_interface__'):
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

    def from_db_value(self, value, expression, connection, context):
        if value:
            if not isinstance(value, Geometry):
                value = Geometry(value)
            srid = value.srid
            if not srid and self.srid != -1:
                value.srid = self.srid
        return value

    # ### Routines overloaded from Field ###
    def contribute_to_class(self, cls, name, **kwargs):
        super(GeometryField, self).contribute_to_class(cls, name, **kwargs)

        # Setup for lazy-instantiated Geometry object.
        setattr(cls, self.attname, SpatialProxy(Geometry, self))

    def formfield(self, **kwargs):
        defaults = {'form_class': self.form_class,
                    'geom_type': self.geom_type,
                    'srid': self.srid,
                    }
        defaults.update(kwargs)
        if (self.dim > 2 and 'widget' not in kwargs and
                not getattr(defaults['form_class'].widget, 'supports_3d', False)):
            defaults['widget'] = forms.Textarea
        return super(GeometryField, self).formfield(**defaults)

    def _get_db_prep_lookup(self, lookup_type, value, connection):
        """
        Prepare for the database lookup, and return any spatial parameters
        necessary for the query.  This includes wrapping any geometry
        parameters with a backend-specific adapter and formatting any distance
        parameters into the correct units for the coordinate system of the
        field.

        Only used by the deprecated GeoQuerySet and to be
        RemovedInDjango20Warning.
        """
        # Populating the parameters list, and wrapping the Geometry
        # with the Adapter of the spatial backend.
        if isinstance(value, (tuple, list)):
            params = [connection.ops.Adapter(value[0])]
            # Getting the distance parameter in the units of the field.
            params += self.get_distance(value[1:], lookup_type, connection)
        else:
            params = [connection.ops.Adapter(value)]
        return params


# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    geom_type = 'POINT'
    form_class = forms.PointField
    description = _("Point")


class LineStringField(GeometryField):
    geom_type = 'LINESTRING'
    form_class = forms.LineStringField
    description = _("Line string")


class PolygonField(GeometryField):
    geom_type = 'POLYGON'
    form_class = forms.PolygonField
    description = _("Polygon")


class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'
    form_class = forms.MultiPointField
    description = _("Multi-point")


class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'
    form_class = forms.MultiLineStringField
    description = _("Multi-line string")


class MultiPolygonField(GeometryField):
    geom_type = 'MULTIPOLYGON'
    form_class = forms.MultiPolygonField
    description = _("Multi polygon")


class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'
    form_class = forms.GeometryCollectionField
    description = _("Geometry collection")


class ExtentField(GeoSelectFormatMixin, Field):
    "Used as a return value from an extent aggregate"

    description = _("Extent Aggregate Field")

    def get_internal_type(self):
        return "ExtentField"


class RasterField(BaseSpatialField):
    """
    Raster field for GeoDjango -- evaluates into GDALRaster objects.
    """

    description = _("Raster Field")
    geom_type = 'RASTER'
    geography = False

    def __init__(self, *args, **kwargs):
        if not HAS_GDAL:
            raise ImproperlyConfigured('RasterField requires GDAL.')
        super(RasterField, self).__init__(*args, **kwargs)

    def _check_connection(self, connection):
        # Make sure raster fields are used only on backends with raster support.
        if not connection.features.gis_enabled or not connection.features.supports_raster:
            raise ImproperlyConfigured('Raster fields require backends with raster support.')

    def db_type(self, connection):
        self._check_connection(connection)
        return super(RasterField, self).db_type(connection)

    def from_db_value(self, value, expression, connection, context):
        return connection.ops.parse_raster(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        self._check_connection(connection)
        # Prepare raster for writing to database.
        if not prepared:
            value = connection.ops.deconstruct_raster(value)
        return super(RasterField, self).get_db_prep_value(value, connection, prepared)

    def contribute_to_class(self, cls, name, **kwargs):
        super(RasterField, self).contribute_to_class(cls, name, **kwargs)
        # Importing GDALRaster raises an exception on systems without gdal.
        from django.contrib.gis.gdal import GDALRaster
        # Setup for lazy-instantiated Raster object. For large querysets, the
        # instantiation of all GDALRasters can potentially be expensive. This
        # delays the instantiation of the objects to the moment of evaluation
        # of the raster attribute.
        setattr(cls, self.attname, SpatialProxy(GDALRaster, self))

    def get_transform(self, name):
        try:
            band_index = int(name)
            return type(
                'SpecificRasterBandTransform',
                (RasterBandTransform, ),
                {'band_index': band_index}
            )
        except ValueError:
            pass
        return super(RasterField, self).get_transform(name)
