from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import aggregates
from django.db.backends.mysql.operations import DatabaseOperations
from django.utils.functional import cached_property


class MySQLOperations(BaseSpatialOperations, DatabaseOperations):

    mysql = True
    name = 'mysql'
    select = 'ST_AsText(%s)'
    from_wkb = 'ST_GeomFromWKB'
    from_text = 'ST_GeomFromText'

    Adapter = WKTAdapter

    gis_operators = {
        'bbcontains': SpatialOperator(func='MBRContains'),  # For consistency w/PostGIS API
        'bboverlaps': SpatialOperator(func='MBROverlaps'),  # .. ..
        'contained': SpatialOperator(func='MBRWithin'),    # .. ..
        'contains': SpatialOperator(func='MBRContains'),
        'disjoint': SpatialOperator(func='MBRDisjoint'),
        'equals': SpatialOperator(func='MBREqual'),
        'exact': SpatialOperator(func='MBREqual'),
        'intersects': SpatialOperator(func='MBRIntersects'),
        'overlaps': SpatialOperator(func='MBROverlaps'),
        'same_as': SpatialOperator(func='MBREqual'),
        'touches': SpatialOperator(func='MBRTouches'),
        'within': SpatialOperator(func='MBRWithin'),
    }

    function_names = {
        'Difference': 'ST_Difference',
        'Distance': 'ST_Distance',
        'Intersection': 'ST_Intersection',
        'Length': 'ST_Length',
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
            'ForceRHR', 'GeoHash', 'MemSize',
            'Perimeter', 'PointOnSurface', 'Reverse', 'Scale', 'SnapToGrid',
            'Transform', 'Translate',
        }
        if self.connection.mysql_version < (5, 6, 1):
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
