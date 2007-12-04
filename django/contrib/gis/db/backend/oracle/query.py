"""
 This module contains the spatial lookup types, and the get_geo_where_clause()
 routine for Oracle Spatial.
"""
import re
from decimal import Decimal
from django.db import connection
from django.contrib.gis.measure import Distance
qn = connection.ops.quote_name

# The GML, distance, transform, and union procedures.
ASGML = 'SDO_UTIL.TO_GMLGEOMETRY'
DISTANCE = 'SDO_GEOM.SDO_DISTANCE'
TRANSFORM = 'SDO_CS.TRANSFORM'
UNION = 'SDO_AGGR_UNION'

class SDOOperation(object):
    "Base class for SDO* Oracle operations."

    def __init__(self, lookup, subst='', operator='=', result="'TRUE'",
                 beg_subst='%s(%s%s, %%s'):
        self.lookup = lookup
        self.subst = subst
        self.operator = operator
        self.result = result
        self.beg_subst = beg_subst
        self.end_subst = ') %s %s' % (self.operator, self.result)

    @property
    def sql_subst(self):
        return ''.join([self.beg_subst, self.subst, self.end_subst])

    def as_sql(self, table, field):
        return self.sql_subst % self.params(table, field)

    def params(self, table, field):
        return (self.lookup, table, field)

class SDODistance(SDOOperation):
    "Class for Distance queries."
    def __init__(self, op, tolerance=0.05):
        super(SDODistance, self).__init__(DISTANCE, subst=", %s", operator=op, result='%%s')
        self.tolerance = tolerance

    def params(self, table, field):
        return (self.lookup, table, field, self.tolerance)

class SDOGeomRelate(SDOOperation):
    "Class for using SDO_GEOM.RELATE."
    def __init__(self, mask, tolerance=0.05):
        super(SDOGeomRelate, self).__init__('SDO_GEOM.RELATE',  beg_subst="%s(%s%s, '%s'",
                                            subst=", %%s, %s", result="'%s'" % mask)
        self.mask = mask
        self.tolerance = tolerance

    def params(self, table, field):
        return (self.lookup, table, field, self.mask, self.tolerance)

class SDORelate(SDOOperation):
    "Class for using SDO_RELATE."
    masks = 'TOUCH|OVERLAPBDYDISJOINT|OVERLAPBDYINTERSECT|EQUAL|INSIDE|COVEREDBY|CONTAINS|COVERS|ANYINTERACT|ON'
    mask_regex = re.compile(r'^(%s)(\+(%s))*$' % (masks, masks), re.I)
    
    def __init__(self, mask, **kwargs):
        super(SDORelate, self).__init__('SDO_RELATE',  subst=", 'mask=%s'", **kwargs)
        if not self.mask_regex.match(mask):
            raise ValueError('Invalid %s mask: "%s"' % (self.lookup, mask))
        self.mask = mask

    def params(self, table, field):
        return (self.lookup, table, field, self.mask)

# Valid distance types and substitutions
dtypes = (Decimal, Distance, float, int)
DISTANCE_FUNCTIONS = {
    'distance_gt' : (SDODistance('>'), dtypes),
    'distance_gte' : (SDODistance('>='), dtypes),
    'distance_lt' : (SDODistance('<'), dtypes),
    'distance_lte' : (SDODistance('<='), dtypes),
    }

ORACLE_GEOMETRY_FUNCTIONS = {
    'contains' : SDOOperation('SDO_CONTAINS'),
    'coveredby' : SDOOperation('SDO_COVEREDBY'),
    'covers' : SDOOperation('SDO_COVERS'),
    'disjoint' : SDOGeomRelate('DISJOINT'),
    'dwithin' : (SDOOperation('SDO_WITHIN_DISTANCE', "%%s, 'distance=%%s'"), dtypes),
    'intersects' : SDOOperation('SDO_OVERLAPBDYINTERSECT'), # TODO: Is this really the same as ST_Intersects()?
    'equals' : SDOOperation('SDO_EQUAL'),
    'exact' : SDOOperation('SDO_EQUAL'),
    'overlaps' : SDOOperation('SDO_OVERLAPS'),
    'same_as' : SDOOperation('SDO_EQUAL'),
    'relate' : (SDORelate, basestring), # Oracle uses a different syntax, e.g., 'mask=inside+touch'
    'touches' : SDOOperation('SDO_TOUCH'),
    'within' : SDOOperation('SDO_INSIDE'),
    }
ORACLE_GEOMETRY_FUNCTIONS.update(DISTANCE_FUNCTIONS)

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
            sdo_op, arg_type = lookup_info

            # Ensuring that a tuple _value_ was passed in from the user
            if not isinstance(value, tuple):
                raise TypeError('Tuple required for `%s` lookup type.' % lookup_type)
            if len(value) != 2: 
                raise ValueError('2-element tuple required for %s lookup type.' % lookup_type)
            
            # Ensuring the argument type matches what we expect.
            if not isinstance(value[1], arg_type):
                raise TypeError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))

            if lookup_type == 'relate':
                # The SDORelate class handles construction for these queries, and verifies
                # the mask argument.
                return sdo_op(value[1]).as_sql(table_prefix, field_name)
            elif lookup_type in DISTANCE_FUNCTIONS:
                op = DISTANCE_FUNCTIONS[lookup_type][0]
                return op.as_sql(table_prefix, field_name)
                #    return '%s(%s%s, %%s) %s %%s' % (DISTANCE, table_prefix, field_name, op)
            else:
                return sdo_op.as_sql(table_prefix, field_name)
        else:
            # Lookup info is a SDOOperation instance, whos `as_sql` method returns
            # the SQL necessary for the geometry function call. For example:  
            #  SDO_CONTAINS("geoapp_country"."poly", SDO_GEOMTRY('POINT(5 23)', 4326)) = 'TRUE'
            return lookup_info.as_sql(table_prefix, field_name)
    
    # Handling 'isnull' lookup type
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

# Want to get SDO Geometries as WKT (much easier to instantiate GEOS proxies
# from WKT than SDO_GEOMETRY(...) strings ;)
GEOM_SELECT = 'SDO_UTIL.TO_WKTGEOMETRY(%s)'
