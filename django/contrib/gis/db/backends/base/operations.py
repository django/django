from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import (
    Area as AreaMeasure, Distance as DistanceMeasure,
)
from django.db.utils import NotSupportedError
from django.utils.functional import cached_property


class BaseSpatialOperations:
    # Quick booleans for the type of this spatial backend, and
    # an attribute for the spatial database version tuple (if applicable)
    postgis = False
    spatialite = False
    mysql = False
    oracle = False
    spatial_version = None

    # How the geometry column should be selected.
    select = '%s'

    @cached_property
    def select_extent(self):
        return self.select

    # Does the spatial database have a geometry or geography type?
    geography = False
    geometry = False

    # Aggregates
    disallowed_aggregates = ()

    geom_func_prefix = ''

    # Mapping between Django function names and backend names, when names do not
    # match; used in spatial_function_name().
    function_names = {}

    # Blacklist/set of known unsupported functions of the backend
    unsupported_functions = {
        'Area', 'AsGeoJSON', 'AsGML', 'AsKML', 'AsSVG', 'Azimuth',
        'BoundingCircle', 'Centroid', 'Difference', 'Distance', 'Envelope',
        'ForceRHR', 'GeoHash', 'Intersection', 'IsValid', 'Length',
        'LineLocatePoint', 'MakeValid', 'MemSize', 'NumGeometries',
        'NumPoints', 'Perimeter', 'PointOnSurface', 'Reverse', 'Scale',
        'SnapToGrid', 'SymDifference', 'Transform', 'Translate', 'Union',
    }

    # Constructors
    from_text = False

    # Default conversion functions for aggregates; will be overridden if implemented
    # for the spatial backend.
    def convert_extent(self, box, srid):
        raise NotImplementedError('Aggregate extent not implemented for this spatial backend.')

    def convert_extent3d(self, box, srid):
        raise NotImplementedError('Aggregate 3D extent not implemented for this spatial backend.')

    # For quoting column values, rather than columns.
    def geo_quote_name(self, name):
        return "'%s'" % name

    # GeometryField operations
    def geo_db_type(self, f):
        """
        Return the database column type for the geometry field on
        the spatial backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_type() method')

    def get_distance(self, f, value, lookup_type):
        """
        Return the distance parameters for the given geometry field,
        lookup value, and lookup type.
        """
        raise NotImplementedError('Distance operations not available on this spatial backend.')

    def get_geom_placeholder(self, f, value, compiler):
        """
        Return the placeholder for the given geometry field with the given
        value.  Depending on the spatial backend, the placeholder may contain a
        stored procedure call to the transformation function of the spatial
        backend.
        """
        def transform_value(value, field):
            return value is not None and value.srid != field.srid

        if hasattr(value, 'as_sql'):
            return (
                '%s(%%s, %s)' % (self.spatial_function_name('Transform'), f.srid)
                if transform_value(value.output_field, f)
                else '%s'
            )
        if transform_value(value, f):
            # Add Transform() to the SQL placeholder.
            return '%s(%s(%%s,%s), %s)' % (
                self.spatial_function_name('Transform'),
                self.from_text, value.srid, f.srid,
            )
        elif self.connection.features.has_spatialrefsys_table:
            return '%s(%%s,%s)' % (self.from_text, f.srid)
        else:
            # For backwards compatibility on MySQL (#27464).
            return '%s(%%s)' % self.from_text

    def check_expression_support(self, expression):
        if isinstance(expression, self.disallowed_aggregates):
            raise NotSupportedError(
                "%s spatial aggregation is not supported by this database backend." % expression.name
            )
        super().check_expression_support(expression)

    def spatial_aggregate_name(self, agg_name):
        raise NotImplementedError('Aggregate support not implemented for this spatial backend.')

    def spatial_function_name(self, func_name):
        if func_name in self.unsupported_functions:
            raise NotSupportedError("This backend doesn't support the %s function." % func_name)
        return self.function_names.get(func_name, self.geom_func_prefix + func_name)

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        raise NotImplementedError('Subclasses of BaseSpatialOperations must provide a geometry_columns() method.')

    def spatial_ref_sys(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide spatial_ref_sys() method')

    distance_expr_for_lookup = staticmethod(Distance)

    def get_db_converters(self, expression):
        converters = super().get_db_converters(expression)
        if isinstance(expression.output_field, GeometryField):
            converters.append(self.get_geometry_converter(expression))
        return converters

    def get_geometry_converter(self, expression):
        raise NotImplementedError(
            'Subclasses of BaseSpatialOperations must provide a '
            'get_geometry_converter() method.'
        )

    def get_area_att_for_field(self, field):
        if field.geodetic(self.connection):
            if self.connection.features.supports_area_geodetic:
                return 'sq_m'
            raise NotImplementedError('Area on geodetic coordinate systems not supported.')
        else:
            units_name = field.units_name(self.connection)
            if units_name:
                return AreaMeasure.unit_attname(units_name)

    def get_distance_att_for_field(self, field):
        dist_att = None
        if field.geodetic(self.connection):
            if self.connection.features.supports_distance_geodetic:
                dist_att = 'm'
        else:
            units = field.units_name(self.connection)
            if units:
                dist_att = DistanceMeasure.unit_attname(units)
        return dist_att
