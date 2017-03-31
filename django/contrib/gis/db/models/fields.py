from collections import defaultdict, namedtuple

from django.contrib.gis import forms, gdal
from django.contrib.gis.db.models.proxy import SpatialProxy
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geometry.backend import Geometry, GeometryException
from django.core.exceptions import ImproperlyConfigured
from django.db.models.expressions import Expression
from django.db.models.fields import Field
from django.utils.translation import gettext_lazy as _

# Local cache of the spatial_ref_sys table, which holds SRID data for each
# spatial database alias. This cache exists so that the database isn't queried
# for SRID info each time a distance query is constructed.
_srid_cache = defaultdict(dict)


SRIDCacheEntry = namedtuple('SRIDCacheEntry', ['units', 'units_name', 'spheroid', 'geodetic'])


def get_srid_info(srid, connection):
    """
    Return the units, unit name, and spheroid WKT associated with the
    given SRID from the `spatial_ref_sys` (or equivalent) spatial database
    table for the given database connection.  These results are cached.
    """
    from django.contrib.gis.gdal import SpatialReference
    global _srid_cache

    try:
        # The SpatialRefSys model for the spatial backend.
        SpatialRefSys = connection.ops.spatial_ref_sys()
    except NotImplementedError:
        SpatialRefSys = None

    alias, get_srs = (
        (connection.alias, lambda srid: SpatialRefSys.objects.using(connection.alias).get(srid=srid).srs)
        if SpatialRefSys else
        (None, SpatialReference)
    )
    if srid not in _srid_cache[alias]:
        srs = get_srs(srid)
        units, units_name = srs.units
        _srid_cache[alias][srid] = SRIDCacheEntry(
            units=units,
            units_name=units_name,
            spheroid='SPHEROID["%s",%s,%s]' % (srs['spheroid'], srs.semi_major, srs.inverse_flattening),
            geodetic=srs.geographic,
        )

    return _srid_cache[alias][srid]


class GeoSelectFormatMixin:
    def select_format(self, compiler, sql, params):
        """
        Return the selection format string, depending on the requirements
        of the spatial backend.  For example, Oracle and MySQL require custom
        selection formats in order to retrieve geometries in OGC WKT. For all
        other fields, return a simple '%s' format string.
        """
        connection = compiler.connection
        if connection.ops.select:
            # This allows operations to be done on fields in the SELECT,
            # overriding their values -- used by the Oracle and MySQL
            # spatial backends to get database values as WKT.
            sql = connection.ops.select % sql
        return sql, params


class BaseSpatialField(Field):
    """
    The Base GIS Field.

    It's used as a base class for GeometryField and RasterField. Defines
    properties that are common to all GIS fields such as the characteristics
    of the spatial reference system of the field.
    """
    description = _("The base GIS field.")
    empty_strings_allowed = False

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

        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Always include SRID for less fragility; include spatial index if it's
        # not the default value.
        kwargs['srid'] = self.srid
        if self.spatial_index is not True:
            kwargs['spatial_index'] = self.spatial_index
        return name, path, args, kwargs

    def db_type(self, connection):
        return connection.ops.geo_db_type(self)

    def spheroid(self, connection):
        return get_srid_info(self.srid, connection).spheroid

    def units(self, connection):
        return get_srid_info(self.srid, connection).units

    def units_name(self, connection):
        return get_srid_info(self.srid, connection).units_name

    def geodetic(self, connection):
        """
        Return true if this field's SRID corresponds with a coordinate
        system that uses non-projected units (e.g., latitude/longitude).
        """
        return get_srid_info(self.srid, connection).geodetic

    def get_placeholder(self, value, compiler, connection):
        """
        Return the placeholder for the spatial column for the
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
        if isinstance(value, Geometry) or value:
            return connection.ops.Adapter(self.get_prep_value(value))
        else:
            return None

    def get_raster_prep_value(self, value, is_candidate):
        """
        Return a GDALRaster if conversion is successful, otherwise return None.
        """
        if isinstance(value, gdal.GDALRaster):
            return value
        elif is_candidate:
            try:
                return gdal.GDALRaster(value)
            except GDALException:
                pass
        elif isinstance(value, dict):
            try:
                return gdal.GDALRaster(value)
            except GDALException:
                raise ValueError("Couldn't create spatial object from lookup value '%s'." % value)

    def get_prep_value(self, value):
        """
        Spatial lookup values are either a parameter that is (or may be
        converted to) a geometry or raster, or a sequence of lookup values
        that begins with a geometry or raster. Set up the geometry or raster
        value properly and preserves any other lookup parameters.
        """
        value = super().get_prep_value(value)

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
        if isinstance(obj, Geometry):
            pass
        else:
            # Check if input is a candidate for conversion to raster or geometry.
            is_candidate = isinstance(obj, (bytes, str)) or hasattr(obj, '__geo_interface__')
            # Try to convert the input to raster.
            raster = self.get_raster_prep_value(obj, is_candidate)

            if raster:
                obj = raster
            elif is_candidate:
                try:
                    obj = Geometry(obj)
                except (GeometryException, GDALException):
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


class GeometryField(GeoSelectFormatMixin, BaseSpatialField):
    """
    The base Geometry field -- maps to the OpenGIS Specification Geometry type.
    """
    description = _("The base Geometry field -- maps to the OpenGIS Specification Geometry type.")
    form_class = forms.GeometryField
    # The OpenGIS Geometry name.
    geom_type = 'GEOMETRY'

    def __init__(self, verbose_name=None, dim=2, geography=False, *, extent=(-180.0, -90.0, 180.0, 90.0),
                 tolerance=0.05, **kwargs):
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
        self._extent = extent
        self._tolerance = tolerance

        super().__init__(verbose_name=verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Include kwargs if they're not the default values.
        if self.dim != 2:
            kwargs['dim'] = self.dim
        if self.geography is not False:
            kwargs['geography'] = self.geography
        return name, path, args, kwargs

    # ### Routines specific to GeometryField ###
    def get_distance(self, value, lookup_type, connection):
        """
        Return a distance number in units of the field.  For example, if
        `D(km=1)` was passed in and the units of the field were in meters,
        then 1000 would be returned.
        """
        return connection.ops.get_distance(self, value, lookup_type)

    def get_db_prep_value(self, value, connection, *args, **kwargs):
        return connection.ops.Adapter(
            super().get_db_prep_value(value, connection, *args, **kwargs),
            **({'geography': True} if self.geography else {})
        )

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
        super().contribute_to_class(cls, name, **kwargs)

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
        return super().formfield(**defaults)


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

    def _check_connection(self, connection):
        # Make sure raster fields are used only on backends with raster support.
        if not connection.features.gis_enabled or not connection.features.supports_raster:
            raise ImproperlyConfigured('Raster fields require backends with raster support.')

    def db_type(self, connection):
        self._check_connection(connection)
        return super().db_type(connection)

    def from_db_value(self, value, expression, connection, context):
        return connection.ops.parse_raster(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        self._check_connection(connection)
        # Prepare raster for writing to database.
        if not prepared:
            value = connection.ops.deconstruct_raster(value)
        return super().get_db_prep_value(value, connection, prepared)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        # Setup for lazy-instantiated Raster object. For large querysets, the
        # instantiation of all GDALRasters can potentially be expensive. This
        # delays the instantiation of the objects to the moment of evaluation
        # of the raster attribute.
        setattr(cls, self.attname, SpatialProxy(gdal.GDALRaster, self))

    def get_transform(self, name):
        from django.contrib.gis.db.models.lookups import RasterBandTransform
        try:
            band_index = int(name)
            return type(
                'SpecificRasterBandTransform',
                (RasterBandTransform, ),
                {'band_index': band_index}
            )
        except ValueError:
            pass
        return super().get_transform(name)
