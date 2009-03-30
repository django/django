"""
 This module contains the spatial lookup types, and the get_geo_where_clause()
 routine for SpatiaLite.
"""
import re
from decimal import Decimal
from django.db import connection
from django.contrib.gis.measure import Distance
from django.contrib.gis.db.backend.util import SpatialOperation, SpatialFunction
qn = connection.ops.quote_name

GEOM_SELECT = 'AsText(%s)'

# Dummy func, in case we need it later:
def get_func(str):
    return str

# Functions used by the GeoManager & GeoQuerySet
AREA = get_func('Area')
CENTROID = get_func('Centroid')
CONTAINED = get_func('MbrWithin')
DIFFERENCE = get_func('Difference')
DISTANCE = get_func('Distance')
ENVELOPE = get_func('Envelope')
GEOM_FROM_TEXT = get_func('GeomFromText')
GEOM_FROM_WKB = get_func('GeomFromWKB')
INTERSECTION = get_func('Intersection')
LENGTH = get_func('GLength') # OpenGis defines Length, but this conflicts with an SQLite reserved keyword
NUM_GEOM = get_func('NumGeometries')
NUM_POINTS = get_func('NumPoints')
POINT_ON_SURFACE = get_func('PointOnSurface')
SCALE = get_func('ScaleCoords')
SYM_DIFFERENCE = get_func('SymDifference')
TRANSFORM = get_func('Transform')
TRANSLATE = get_func('ShiftCoords')
UNION = 'GUnion'# OpenGis defines Union, but this conflicts with an SQLite reserved keyword
UNIONAGG = 'GUnion'

#### Classes used in constructing SpatiaLite spatial SQL ####
class SpatiaLiteOperator(SpatialOperation):
    "For SpatiaLite operators (e.g. `&&`, `~`)."
    def __init__(self, operator):
        super(SpatiaLiteOperator, self).__init__(operator=operator, beg_subst='%s %s %%s')

class SpatiaLiteFunction(SpatialFunction):
    "For SpatiaLite function calls."
    def __init__(self, function, **kwargs):
        super(SpatiaLiteFunction, self).__init__(get_func(function), **kwargs)

class SpatiaLiteFunctionParam(SpatiaLiteFunction):
    "For SpatiaLite functions that take another parameter."
    def __init__(self, func):
        super(SpatiaLiteFunctionParam, self).__init__(func, end_subst=', %%s)')

class SpatiaLiteDistance(SpatiaLiteFunction):
    "For SpatiaLite distance operations."
    dist_func = 'Distance'
    def __init__(self, operator):
        super(SpatiaLiteDistance, self).__init__(self.dist_func, end_subst=') %s %s', 
                                              operator=operator, result='%%s')
                                                    
class SpatiaLiteRelate(SpatiaLiteFunctionParam):
    "For SpatiaLite Relate(<geom>, <pattern>) calls."
    pattern_regex = re.compile(r'^[012TF\*]{9}$')
    def __init__(self, pattern):
        if not self.pattern_regex.match(pattern):
            raise ValueError('Invalid intersection matrix pattern "%s".' % pattern)
        super(SpatiaLiteRelate, self).__init__('Relate')


SPATIALITE_GEOMETRY_FUNCTIONS = {
    'equals' : SpatiaLiteFunction('Equals'),
    'disjoint' : SpatiaLiteFunction('Disjoint'),
    'touches' : SpatiaLiteFunction('Touches'),
    'crosses' : SpatiaLiteFunction('Crosses'),
    'within' : SpatiaLiteFunction('Within'),
    'overlaps' : SpatiaLiteFunction('Overlaps'),
    'contains' : SpatiaLiteFunction('Contains'),
    'intersects' : SpatiaLiteFunction('Intersects'),
    'relate' : (SpatiaLiteRelate, basestring),
    # Retruns true if B's bounding box completely contains A's bounding box.
    'contained' : SpatiaLiteFunction('MbrWithin'),
    # Returns true if A's bounding box completely contains B's bounding box.
    'bbcontains' : SpatiaLiteFunction('MbrContains'),
    # Returns true if A's bounding box overlaps B's bounding box.
    'bboverlaps' : SpatiaLiteFunction('MbrOverlaps'),
    # These are implemented here as synonyms for Equals
    'same_as' : SpatiaLiteFunction('Equals'),
    'exact' : SpatiaLiteFunction('Equals'),
    }

# Valid distance types and substitutions
dtypes = (Decimal, Distance, float, int, long)
def get_dist_ops(operator):
    "Returns operations for regular distances; spherical distances are not currently supported."
    return (SpatiaLiteDistance(operator),)
DISTANCE_FUNCTIONS = {
    'distance_gt' : (get_dist_ops('>'), dtypes),
    'distance_gte' : (get_dist_ops('>='), dtypes),
    'distance_lt' : (get_dist_ops('<'), dtypes),
    'distance_lte' : (get_dist_ops('<='), dtypes),
    }

# Distance functions are a part of SpatiaLite geometry functions.
SPATIALITE_GEOMETRY_FUNCTIONS.update(DISTANCE_FUNCTIONS)

# Any other lookup types that do not require a mapping.
MISC_TERMS = ['isnull']

# These are the SpatiaLite-customized QUERY_TERMS -- a list of the lookup types
# allowed for geographic queries.
SPATIALITE_TERMS = SPATIALITE_GEOMETRY_FUNCTIONS.keys() # Getting the Geometry Functions
SPATIALITE_TERMS += MISC_TERMS # Adding any other miscellaneous terms (e.g., 'isnull')
SPATIALITE_TERMS = dict((term, None) for term in SPATIALITE_TERMS) # Making a dictionary for fast lookups

#### The `get_geo_where_clause` function for SpatiaLite. ####
def get_geo_where_clause(table_alias, name, lookup_type, geo_annot):
    "Returns the SQL WHERE clause for use in SpatiaLite SQL construction."
    # Getting the quoted field as `geo_col`.
    geo_col = '%s.%s' % (qn(table_alias), qn(name))
    if lookup_type in SPATIALITE_GEOMETRY_FUNCTIONS:
        # See if a SpatiaLite geometry function matches the lookup type.
        tmp = SPATIALITE_GEOMETRY_FUNCTIONS[lookup_type]

        # Lookup types that are tuples take tuple arguments, e.g., 'relate' and 
        # distance lookups.
        if isinstance(tmp, tuple):
            # First element of tuple is the SpatiaLiteOperation instance, and the
            # second element is either the type or a tuple of acceptable types
            # that may passed in as further parameters for the lookup type.
            op, arg_type = tmp

            # Ensuring that a tuple _value_ was passed in from the user
            if not isinstance(geo_annot.value, (tuple, list)): 
                raise TypeError('Tuple required for `%s` lookup type.' % lookup_type)
           
            # Number of valid tuple parameters depends on the lookup type.
            if len(geo_annot.value) != 2:
                raise ValueError('Incorrect number of parameters given for `%s` lookup type.' % lookup_type)
            
            # Ensuring the argument type matches what we expect.
            if not isinstance(geo_annot.value[1], arg_type):
                raise TypeError('Argument type should be %s, got %s instead.' % (arg_type, type(geo_annot.value[1])))

            # For lookup type `relate`, the op instance is not yet created (has
            # to be instantiated here to check the pattern parameter).
            if lookup_type == 'relate': 
                op = op(geo_annot.value[1])
            elif lookup_type in DISTANCE_FUNCTIONS:
                op = op[0]
        else:
            op = tmp
        # Calling the `as_sql` function on the operation instance.
        return op.as_sql(geo_col)
    elif lookup_type == 'isnull':
        # Handling 'isnull' lookup type
        return "%s IS %sNULL" % (geo_col, (not geo_annot.value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))
