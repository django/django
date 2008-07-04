"""
 This module contains the spatial lookup types, and the `get_geo_where_clause`
 routine for MySQL.

 Please note that MySQL only supports bounding box queries, also
 known as MBRs (Minimum Bounding Rectangles).  Moreover, spatial
 indices may only be used on MyISAM tables -- if you need 
 transactions, take a look at PostGIS.
"""
from django.db import connection
qn = connection.ops.quote_name

# To ease implementation, WKT is passed to/from MySQL.
GEOM_FROM_TEXT = 'GeomFromText'
GEOM_FROM_WKB = 'GeomFromWKB'
GEOM_SELECT = 'AsText(%s)'

# WARNING: MySQL is NOT compliant w/the OpenGIS specification and
# _every_ one of these lookup types is on the _bounding box_ only.
MYSQL_GIS_FUNCTIONS = {
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

# This lookup type does not require a mapping.
MISC_TERMS = ['isnull']

# Assacceptable lookup types for Oracle spatial.
MYSQL_GIS_TERMS  = MYSQL_GIS_FUNCTIONS.keys()
MYSQL_GIS_TERMS += MISC_TERMS
MYSQL_GIS_TERMS = dict((term, None) for term in MYSQL_GIS_TERMS) # Making dictionary 

def get_geo_where_clause(table_alias, name, lookup_type, geo_annot):
    "Returns the SQL WHERE clause for use in MySQL spatial SQL construction."
    # Getting the quoted field as `geo_col`.
    geo_col = '%s.%s' % (qn(table_alias), qn(name))

    # See if a MySQL Geometry function matches the lookup type next
    lookup_info = MYSQL_GIS_FUNCTIONS.get(lookup_type, False)
    if lookup_info:
        return "%s(%s, %%s)" % (lookup_info, geo_col)
    
    # Handling 'isnull' lookup type
    # TODO: Is this needed because MySQL cannot handle NULL
    # geometries in its spatial indices.
    if lookup_type == 'isnull':
        return "%s IS %sNULL" % (geo_col, (not geo_annot.value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))
