from django.db.backends.mysql.base import DatabaseOperations

from django.contrib.gis.db.backends.adapter import WKTAdapter
from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator


class MySQLOperations(DatabaseOperations, BaseSpatialOperations):

    compiler_module = 'django.contrib.gis.db.models.sql.compiler'
    mysql = True
    name = 'mysql'
    select = 'AsText(%s)'
    from_wkb = 'GeomFromWKB'
    from_text = 'GeomFromText'

    Adapter = WKTAdapter
    Adaptor = Adapter  # Backwards-compatibility alias.

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

    def geo_db_type(self, f):
        return f.geom_type

    def get_geom_placeholder(self, f, value):
        """
        The placeholder here has to include MySQL's WKT constructor.  Because
        MySQL does not support spatial transformations, there is no need to
        modify the placeholder based on the contents of the given value.
        """
        if hasattr(value, 'expression'):
            placeholder = self.get_expression_column(value)
        else:
            placeholder = '%s(%%s)' % self.from_text
        return placeholder
