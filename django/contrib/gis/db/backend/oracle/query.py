"""
 This module contains the spatial lookup types, and the get_geo_where_clause()
 routine for Oracle Spatial.
"""
from django.db import connection
qn = connection.ops.quote_name

ORACLE_GEOMETRY_FUNCTIONS = {
    'contains' : 'SDO_CONTAINS',
    'coveredby' : 'SDO_COVEREDBY',
    'covers' : 'SDO_COVERS',
    'disjoint' : 'SDO_DISJOINT',
    'dwithin' : ('SDO_WITHIN_DISTANCE', float),
    'intersects' : 'SDO_OVERLAPBDYINTERSECT', # TODO: Is this really the same as ST_Intersects()?
    'equals' : 'SDO_EQUAL',
    'exact' : 'SDO_EQUAL',
    'overlaps' : 'SDO_OVERLAPS',
    'same_as' : 'SDO_EQUAL',
    #'relate' : ('SDO_RELATE', str), # Oracle uses a different syntax, e.g., 'mask=inside+touch'
    'touches' : 'SDO_TOUCH',
    'within' : 'SDO_INSIDE',
    }

# This lookup type does not require a mapping.
MISC_TERMS = ['isnull']

# Assacceptable lookup types for Oracle spatial.
ORACLE_SPATIAL_TERMS  = ORACLE_GEOMETRY_FUNCTIONS.keys()
ORACLE_SPATIAL_TERMS += MISC_TERMS
ORACLE_SPATIAL_TERMS = tuple(ORACLE_SPATIAL_TERMS) # Making immutable

def get_geo_where_clause(lookup_type, table_prefix, field_name, value):
    "Returns the SQL WHERE clause for use in Oracle spatial SQL construction."
    if table_prefix.endswith('.'):
        table_prefix = qn(table_prefix[:-1])+'.'
    field_name = qn(field_name)

    # See if a Oracle Geometry function matches the lookup type next
    lookup_info = ORACLE_GEOMETRY_FUNCTIONS.get(lookup_type, False)
    if lookup_info:
        # Lookup types that are tuples take tuple arguments, e.g., 'relate' and 
        #  'dwithin' lookup types.
        if isinstance(lookup_info, tuple):
            # First element of tuple is lookup type, second element is the type
            #  of the expected argument (e.g., str, float)
            func, arg_type = lookup_info

            # Ensuring that a tuple _value_ was passed in from the user
            if not isinstance(value, tuple) or len(value) != 2: 
                raise TypeError('2-element tuple required for %s lookup type.' % lookup_type)
            
            # Ensuring the argument type matches what we expect.
            if not isinstance(value[1], arg_type):
                raise TypeError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))

            if func == 'dwithin':
                # TODO: test and consider adding different distance options.
                return "%s(%s, %%s, 'distance=%s')" % (func, table_prefix + field_name, value[1])
            else:
                return "%s(%s, %%s, %%s) = 'TRUE'" % (func, table_prefix + field_name)
        else:
            # Returning the SQL necessary for the geometry function call. For example: 
            #  SDO_CONTAINS("geoapp_country"."poly", SDO_GEOMTRY('POINT(5 23)', 4326)) = 'TRUE'
            return "%s(%s, %%s) = 'TRUE'" % (lookup_info, table_prefix + field_name)
    
    # Handling 'isnull' lookup type
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

ASGML = 'SDO_UTIL.TO_GMLGEOMETRY'
UNION = 'SDO_AGGR_UNION'
TRANSFORM = 'SDO_CS.TRANSFORM'

# Want to get SDO Geometries as WKT (much easier to instantiate GEOS proxies
# from WKT than SDO_GEOMETRY(...) strings ;)
GEOM_SELECT = 'SDO_UTIL.TO_WKTGEOMETRY(%s)'
