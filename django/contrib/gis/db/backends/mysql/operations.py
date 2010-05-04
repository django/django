from django.db.backends.mysql.base import DatabaseOperations

from django.contrib.gis.db.backends.adapter import WKTAdapter
from django.contrib.gis.db.backends.base import BaseSpatialOperations

class MySQLOperations(DatabaseOperations, BaseSpatialOperations):

    compiler_module = 'django.contrib.gis.db.models.sql.compiler'
    mysql = True
    name = 'mysql'
    select = 'AsText(%s)'
    from_wkb = 'GeomFromWKB'
    from_text = 'GeomFromText'

    Adapter = WKTAdapter
    Adaptor = Adapter # Backwards-compatibility alias.

    geometry_functions = {
        'bbcontains' : 'MBRContains', # For consistency w/PostGIS API
        'bboverlaps' : 'MBROverlaps', # .. ..
        'contained' : 'MBRWithin',    # .. ..
        'contains' : 'MBRContains',
        'disjoint' : 'MBRDisjoint',
        'equals' : 'MBREqual',
        'exact' : 'MBREqual',
        'intersects' : 'MBRIntersects',
        'overlaps' : 'MBROverlaps',
        'same_as' : 'MBREqual',
        'touches' : 'MBRTouches',
        'within' : 'MBRWithin',
        }

    gis_terms = dict([(term, None) for term in geometry_functions.keys() + ['isnull']])

    def geo_db_type(self, f):
        return f.geom_type

    def get_geom_placeholder(self, value, srid):
        """
        The placeholder here has to include MySQL's WKT constructor.  Because
        MySQL does not support spatial transformations, there is no need to
        modify the placeholder based on the contents of the given value.
        """
        if hasattr(value, 'expression'):
            placeholder = '%s.%s' % tuple(map(self.quote_name, value.cols[value.expression]))
        else:
            placeholder = '%s(%%s)' % self.from_text
        return placeholder

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field, qn):
        alias, col, db_type = lvalue

        geo_col = '%s.%s' % (qn(alias), qn(col))

        lookup_info = self.geometry_functions.get(lookup_type, False)
        if lookup_info:
            return "%s(%s, %s)" % (lookup_info, geo_col,
                                   self.get_geom_placeholder(value, field.srid))

        # TODO: Is this really necessary? MySQL can't handle NULL geometries
        #  in its spatial indexes anyways.
        if lookup_type == 'isnull':
            return "%s IS %sNULL" % (geo_col, (not value and 'NOT ' or ''))

        raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))
