"""
 This module contains the spatial lookup types, and the get_geo_where_clause()
 routine for MySQL
"""
from django.db import connection
qn = connection.ops.quote_name

# WARNING: MySQL is NOT compliant w/the OpenGIS specification and
# _every_ one of these lookup types is on the _bounding box_ only.
MYSQL_GIS_FUNCTIONS = {
    'bbcontains' : 'MBRContains', # For consistency w/PostGIS API
    'contained' : 'MBRWithin',    # (ditto)
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

# This lookup type does not require a mapping.
MISC_TERMS = ['isnull']

# Assacceptable lookup types for Oracle spatial.
MYSQL_GIS_TERMS  = MYSQL_GIS_FUNCTIONS.keys()
MYSQL_GIS_TERMS += MISC_TERMS
MYSQL_GIS_TERMS = tuple(MYSQL_GIS_TERMS) # Making immutable

def get_geo_where_clause(lookup_type, table_prefix, field_name, value):
    "Returns the SQL WHERE clause for use in MySQL spatial SQL construction."
    if table_prefix.endswith('.'):
        table_prefix = qn(table_prefix[:-1])+'.'
    field_name = qn(field_name)

    # See if a MySQL Geometry function matches the lookup type next
    lookup_info = MYSQL_GIS_FUNCTIONS.get(lookup_type, False)
    if lookup_info:
        return "%s(%s, %%s)" % (lookup_info, table_prefix + field_name)
    
    # Handling 'isnull' lookup type
    # TODO: Is this needed because MySQL cannot handle NULL
    # geometries in its spatial indices.
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

# To ease implementation, WKT is passed to/from MySQL.
GEOM_FROM_TEXT = 'GeomFromText'
GEOM_FROM_WKB = 'GeomFromWKB'
GEOM_SELECT = 'AsText(%s)'
