from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.db.backends.base.operations import (
    BaseSpatialOperations,
)
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.prototypes.io import wkb_r
from django.contrib.gis.measure import Distance
from django.db.backends.mysql.operations import DatabaseOperations
from django.utils.functional import cached_property


class MySQLOperations(BaseSpatialOperations, DatabaseOperations):

    mysql = True
    name = 'mysql'

    Adapter = WKTAdapter

    @cached_property
    def geom_func_prefix(self):
        return '' if self.is_mysql_5_5 else 'ST_'

    @cached_property
    def is_mysql_5_5(self):
        return self.connection.mysql_version < (5, 6, 1)

    @cached_property
    def is_mysql_5_6(self):
        return self.connection.mysql_version < (5, 7, 6)

    @cached_property
    def select(self):
        return self.geom_func_prefix + 'AsBinary(%s)'

    @cached_property
    def from_text(self):
        return self.geom_func_prefix + 'GeomFromText'

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
        return {'Length': 'GLength'} if self.is_mysql_5_5 else {}

    disallowed_aggregates = (
        aggregates.Collect, aggregates.Extent, aggregates.Extent3D,
        aggregates.MakeLine, aggregates.Union,
    )

    @cached_property
    def unsupported_functions(self):
        unsupported = {
            'AsGML', 'AsKML', 'AsSVG', 'Azimuth', 'BoundingCircle', 'ForceRHR',
            'LineLocatePoint', 'MakeValid', 'MemSize', 'Perimeter',
            'PointOnSurface', 'Reverse', 'Scale', 'SnapToGrid', 'Transform',
            'Translate',
        }
        if self.connection.mysql_version < (5, 7, 5):
            unsupported.update({'AsGeoJSON', 'GeoHash', 'IsValid'})
        if self.is_mysql_5_5:
            unsupported.update({'Difference', 'Distance', 'Intersection', 'SymDifference', 'Union'})
        return unsupported

    def geo_db_type(self, f):
        return f.geom_type

    def get_distance(self, f, value, lookup_type):
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError(
                    'Only numeric values of degree units are allowed on '
                    'geodetic distance queries.'
                )
            dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]

    def get_geometry_converter(self, expression):
        read = wkb_r().read
        srid = expression.output_field.srid
        if srid == -1:
            srid = None

        def converter(value, expression, connection):
            return None if value is None else GEOSGeometry(read(memoryview(value)), srid)
        return converter
