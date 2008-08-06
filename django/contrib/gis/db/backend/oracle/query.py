"""
 This module contains the spatial lookup types, and the `get_geo_where_clause`
 routine for Oracle Spatial.

 Please note that WKT support is broken on the XE version, and thus
 this backend will not work on such platforms.  Specifically, XE lacks 
 support for an internal JVM, and Java libraries are required to use 
 the WKT constructors.
"""
import re
from decimal import Decimal
from django.db import connection
from django.contrib.gis.db.backend.util import SpatialFunction
from django.contrib.gis.measure import Distance
qn = connection.ops.quote_name

# The GML, distance, transform, and union procedures.
AREA = 'SDO_GEOM.SDO_AREA'
ASGML = 'SDO_UTIL.TO_GMLGEOMETRY'
CENTROID = 'SDO_GEOM.SDO_CENTROID'
DIFFERENCE = 'SDO_GEOM.SDO_DIFFERENCE'
DISTANCE = 'SDO_GEOM.SDO_DISTANCE'
EXTENT = 'SDO_AGGR_MBR'
INTERSECTION = 'SDO_GEOM.SDO_INTERSECTION'
LENGTH = 'SDO_GEOM.SDO_LENGTH'
NUM_GEOM = 'SDO_UTIL.GETNUMELEM'
NUM_POINTS = 'SDO_UTIL.GETNUMVERTICES'
POINT_ON_SURFACE = 'SDO_GEOM.SDO_POINTONSURFACE'
SYM_DIFFERENCE = 'SDO_GEOM.SDO_XOR'
TRANSFORM = 'SDO_CS.TRANSFORM'
UNION = 'SDO_GEOM.SDO_UNION'
UNIONAGG = 'SDO_AGGR_UNION'

# We want to get SDO Geometries as WKT because it is much easier to 
# instantiate GEOS proxies from WKT than SDO_GEOMETRY(...) strings.  
# However, this adversely affects performance (i.e., Java is called 
# to convert to WKT on every query).  If someone wishes to write a 
# SDO_GEOMETRY(...) parser in Python, let me know =)
GEOM_SELECT = 'SDO_UTIL.TO_WKTGEOMETRY(%s)'

#### Classes used in constructing Oracle spatial SQL ####
class SDOOperation(SpatialFunction):
    "Base class for SDO* Oracle operations."
    def __init__(self, func, **kwargs):
        kwargs.setdefault('operator', '=')
        kwargs.setdefault('result', 'TRUE')
        kwargs.setdefault('end_subst', ") %s '%s'")
        super(SDOOperation, self).__init__(func, **kwargs)

class SDODistance(SpatialFunction):
    "Class for Distance queries."
    def __init__(self, op, tolerance=0.05):
        super(SDODistance, self).__init__(DISTANCE, end_subst=', %s) %%s %%s' % tolerance, 
                                          operator=op, result='%%s')

class SDOGeomRelate(SpatialFunction):
    "Class for using SDO_GEOM.RELATE."
    def __init__(self, mask, tolerance=0.05):
        # SDO_GEOM.RELATE(...) has a peculiar argument order: column, mask, geom, tolerance.
        # Moreover, the runction result is the mask (e.g., 'DISJOINT' instead of 'TRUE').
        end_subst = "%s%s) %s '%s'" % (', %%s, ', tolerance, '=', mask)
        beg_subst = "%%s(%%s, '%s'" % mask 
        super(SDOGeomRelate, self).__init__('SDO_GEOM.RELATE', beg_subst=beg_subst, end_subst=end_subst)

class SDORelate(SpatialFunction):
    "Class for using SDO_RELATE."
    masks = 'TOUCH|OVERLAPBDYDISJOINT|OVERLAPBDYINTERSECT|EQUAL|INSIDE|COVEREDBY|CONTAINS|COVERS|ANYINTERACT|ON'
    mask_regex = re.compile(r'^(%s)(\+(%s))*$' % (masks, masks), re.I)
    def __init__(self, mask):
        func = 'SDO_RELATE'
        if not self.mask_regex.match(mask):
            raise ValueError('Invalid %s mask: "%s"' % (func, mask))
        super(SDORelate, self).__init__(func, end_subst=", 'mask=%s') = 'TRUE'" % mask)

#### Lookup type mapping dictionaries of Oracle spatial operations ####

# Valid distance types and substitutions
dtypes = (Decimal, Distance, float, int, long)
DISTANCE_FUNCTIONS = {
    'distance_gt' : (SDODistance('>'), dtypes),
    'distance_gte' : (SDODistance('>='), dtypes),
    'distance_lt' : (SDODistance('<'), dtypes),
    'distance_lte' : (SDODistance('<='), dtypes),
    'dwithin' : (SDOOperation('SDO_WITHIN_DISTANCE', 
                              beg_subst="%s(%s, %%s, 'distance=%%s'"), dtypes),
    }

ORACLE_GEOMETRY_FUNCTIONS = {
    'contains' : SDOOperation('SDO_CONTAINS'),
    'coveredby' : SDOOperation('SDO_COVEREDBY'),
    'covers' : SDOOperation('SDO_COVERS'),
    'disjoint' : SDOGeomRelate('DISJOINT'),
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

# Acceptable lookup types for Oracle spatial.
ORACLE_SPATIAL_TERMS  = ORACLE_GEOMETRY_FUNCTIONS.keys()
ORACLE_SPATIAL_TERMS += MISC_TERMS
ORACLE_SPATIAL_TERMS = dict((term, None) for term in ORACLE_SPATIAL_TERMS) # Making dictionary for fast lookups

#### The `get_geo_where_clause` function for Oracle ####
def get_geo_where_clause(table_alias, name, lookup_type, geo_annot):
    "Returns the SQL WHERE clause for use in Oracle spatial SQL construction."
    # Getting the quoted table name as `geo_col`.
    geo_col = '%s.%s' % (qn(table_alias), qn(name))

    # See if a Oracle Geometry function matches the lookup type next
    lookup_info = ORACLE_GEOMETRY_FUNCTIONS.get(lookup_type, False)
    if lookup_info:
        # Lookup types that are tuples take tuple arguments, e.g., 'relate' and 
        # 'dwithin' lookup types.
        if isinstance(lookup_info, tuple):
            # First element of tuple is lookup type, second element is the type
            # of the expected argument (e.g., str, float)
            sdo_op, arg_type = lookup_info

            # Ensuring that a tuple _value_ was passed in from the user
            if not isinstance(geo_annot.value, tuple):
                raise TypeError('Tuple required for `%s` lookup type.' % lookup_type)
            if len(geo_annot.value) != 2: 
                raise ValueError('2-element tuple required for %s lookup type.' % lookup_type)
            
            # Ensuring the argument type matches what we expect.
            if not isinstance(geo_annot.value[1], arg_type):
                raise TypeError('Argument type should be %s, got %s instead.' % (arg_type, type(geo_annot.value[1])))

            if lookup_type == 'relate':
                # The SDORelate class handles construction for these queries, 
                # and verifies the mask argument.
                return sdo_op(geo_annot.value[1]).as_sql(geo_col)
            else:
                # Otherwise, just call the `as_sql` method on the SDOOperation instance.
                return sdo_op.as_sql(geo_col)
        else:
            # Lookup info is a SDOOperation instance, whose `as_sql` method returns
            # the SQL necessary for the geometry function call. For example:  
            #  SDO_CONTAINS("geoapp_country"."poly", SDO_GEOMTRY('POINT(5 23)', 4326)) = 'TRUE'
            return lookup_info.as_sql(geo_col)
    elif lookup_type == 'isnull':
        # Handling 'isnull' lookup type
        return "%s IS %sNULL" % (geo_col, (not geo_annot.value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))
