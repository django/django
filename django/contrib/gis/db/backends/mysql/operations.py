from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import GeometryField, aggregates
from django.db.backends.mysql.operations import DatabaseOperations
from django.utils.functional import cached_property


class MySQLOperations(BaseSpatialOperations, DatabaseOperations):

    mysql = True
    name = 'mysql'

    Adapter = WKTAdapter

    @cached_property
    def is_mysql_5_5(self):
        return self.connection.mysql_version < (5, 6, 1)

    @cached_property
    def is_mysql_5_6(self):
        return self.connection.mysql_version < (5, 7, 6)

    @cached_property
    def uses_invalid_empty_geometry_collection(self):
        return self.connection.mysql_version >= (5, 7, 5)

    @cached_property
    def select(self):
        if self.is_mysql_5_5:
            return 'AsText(%s)'
        return 'ST_AsText(%s)'

    @cached_property
    def from_wkb(self):
        if self.is_mysql_5_5:
            return 'GeomFromWKB'
        return 'ST_GeomFromWKB'

    @cached_property
    def from_text(self):
        if self.is_mysql_5_5:
            return 'GeomFromText'
        return 'ST_GeomFromText'

    @cached_property
    def gis_operators(self):
        MBREquals = 'MBREqual' if self.is_mysql_5_6 else 'MBREquals'
        return {
            'bbcontains': SpatialOperator(func='MBRContains'),  # For consistency w/PostGIS API
            'bboverlaps': SpatialOperator(func='MBROverlaps'),  # ...
            'contained': SpatialOperator(func='MBRWithin'),  # ...
            'contains': SpatialOperator(func='MBRContains'),
            'disjoint': SpatialOperator(func='MBRDisjoint'),
            'equals': SpatialOperator(func=MBREquals),
            'exact': SpatialOperator(func=MBREquals),
            'intersects': SpatialOperator(func='MBRIntersects'),
            'overlaps': SpatialOperator(func='MBROverlaps'),
            'same_as': SpatialOperator(func=MBREquals),
            'touches': SpatialOperator(func='MBRTouches'),
            'within': SpatialOperator(func='MBRWithin'),
        }

    @cached_property
    def function_names(self):
        return {
            'Area': 'Area' if self.is_mysql_5_5 else 'ST_Area',
            'Centroid': 'Centroid' if self.is_mysql_5_5 else 'ST_Centroid',
            'Difference': 'ST_Difference',
            'Distance': 'ST_Distance',
            'Envelope': 'Envelope' if self.is_mysql_5_5 else 'ST_Envelope',
            'Intersection': 'ST_Intersection',
            'Length': 'GLength' if self.is_mysql_5_5 else 'ST_Length',
            'NumGeometries': 'NumGeometries' if self.is_mysql_5_5 else 'ST_NumGeometries',
            'NumPoints': 'NumPoints' if self.is_mysql_5_5 else 'ST_NumPoints',
            'SymDifference': 'ST_SymDifference',
            'Union': 'ST_Union',
        }

    disallowed_aggregates = (
        aggregates.Collect, aggregates.Extent, aggregates.Extent3D,
        aggregates.MakeLine, aggregates.Union,
    )

    @cached_property
    def unsupported_functions(self):
        unsupported = {
            'AsGeoJSON', 'AsGML', 'AsKML', 'AsSVG', 'BoundingCircle',
            'ForceRHR', 'GeoHash', 'IsValid', 'MakeValid', 'MemSize',
            'Perimeter', 'PointOnSurface', 'Reverse', 'Scale', 'SnapToGrid',
            'Transform', 'Translate',
        }
        if self.is_mysql_5_5:
            unsupported.update({'Difference', 'Distance', 'Intersection', 'SymDifference', 'Union'})
        return unsupported

    def geo_db_type(self, f):
        return f.geom_type

    def get_geom_placeholder(self, f, value, compiler):
        """
        The placeholder here has to include MySQL's WKT constructor.  Because
        MySQL does not support spatial transformations, there is no need to
        modify the placeholder based on the contents of the given value.
        """
        if hasattr(value, 'as_sql'):
            placeholder, _ = compiler.compile(value)
        else:
            placeholder = '%s(%%s)' % self.from_text
        return placeholder

    def get_db_converters(self, expression):
        converters = super(MySQLOperations, self).get_db_converters(expression)
        if isinstance(expression.output_field, GeometryField) and self.uses_invalid_empty_geometry_collection:
            converters.append(self.convert_invalid_empty_geometry_collection)
        return converters

    # https://dev.mysql.com/doc/refman/en/spatial-function-argument-handling.html
    # MySQL 5.7.5 adds support for the empty geometry collections, but they are represented with invalid WKT.
    def convert_invalid_empty_geometry_collection(self, value, expression, connection, context):
        if value == b'GEOMETRYCOLLECTION()':
            return b'GEOMETRYCOLLECTION EMPTY'
        return value
