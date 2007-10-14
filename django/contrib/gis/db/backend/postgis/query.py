"""
 This module contains the spatial lookup types, and the get_geo_where_clause()
 routine for PostGIS.
"""
from django.db import connection
from django.contrib.gis.db.backend.postgis.management import postgis_version_tuple
from types import StringType, UnicodeType
qn = connection.ops.quote_name

# Getting the PostGIS version information
POSTGIS_VERSION, MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2 = postgis_version_tuple()

# The supported PostGIS versions.
#  TODO: Confirm tests with PostGIS versions 1.1.x -- should work.  
#        Versions <= 1.0.x do not use GEOS C API, and will not be supported.
if MAJOR_VERSION != 1 or (MAJOR_VERSION == 1 and MINOR_VERSION1 < 1):
    raise Exception('PostGIS version %s not supported.' % POSTGIS_VERSION)

# PostGIS-specific operators. The commented descriptions of these
# operators come from Section 6.2.2 of the official PostGIS documentation.
POSTGIS_OPERATORS = {
    # The "&<" operator returns true if A's bounding box overlaps or
    #  is to the left of B's bounding box.
    'overlaps_left' : '&<',
    # The "&>" operator returns true if A's bounding box overlaps or
    #  is to the right of B's bounding box.
    'overlaps_right' : '&>',
    # The "<<" operator returns true if A's bounding box is strictly
    #  to the left of B's bounding box.
    'left' : '<<',
    # The ">>" operator returns true if A's bounding box is strictly
    #  to the right of B's bounding box.
    'right' : '>>',
    # The "&<|" operator returns true if A's bounding box overlaps or
    #  is below B's bounding box.
    'overlaps_below' : '&<|',
    # The "|&>" operator returns true if A's bounding box overlaps or
    #  is above B's bounding box.
    'overlaps_above' : '|&>',
    # The "<<|" operator returns true if A's bounding box is strictly
    #  below B's bounding box.
    'strictly_below' : '<<|',
    # The "|>>" operator returns true if A's bounding box is strictly
    # above B's bounding box.
    'strictly_above' : '|>>',
    # The "~=" operator is the "same as" operator. It tests actual
    #  geometric equality of two features. So if A and B are the same feature,
    #  vertex-by-vertex, the operator returns true.
    'same_as' : '~=',
    'exact' : '~=',
    # The "@" operator returns true if A's bounding box is completely contained
    #  by B's bounding box.
    'contained' : '@',
    # The "~" operator returns true if A's bounding box completely contains
    #  by B's bounding box.
    'bbcontains' : '~',
    # The "&&" operator returns true if A's bounding box overlaps
    #  B's bounding box.
    'bboverlaps' : '&&',
    }

# Versions of PostGIS >= 1.2.2 changed their naming convention to be
#  'SQL-MM-centric' to conform with the ISO standard. Practically, this 
#  means that 'ST_' is prefixes geometry function names.
if MAJOR_VERSION > 1 or (MAJOR_VERSION == 1 and (MINOR_VERSION1 > 2 or (MINOR_VERSION1 == 2 and MINOR_VERSION2 >= 2))):
    GEOM_FUNC_PREFIX = 'ST_'
else:
    GEOM_FUNC_PREFIX = ''

# For PostGIS >= 1.2.2 the following lookup types will do a bounding box query
#  first before calling the more computationally expensive GEOS routines (called
#  "inline index magic"):
#    'touches', 'crosses', 'contains', 'intersects', 'within', 'overlaps', and
#    'covers'.
POSTGIS_GEOMETRY_FUNCTIONS = {
    'equals' : 'Equals',
    'disjoint' : 'Disjoint',
    'touches' : 'Touches',
    'crosses' : 'Crosses',
    'within' : 'Within',
    'overlaps' : 'Overlaps',
    'contains' : 'Contains',
    'intersects' : 'Intersects',
    'relate' : ('Relate', str),
    }

if GEOM_FUNC_PREFIX == 'ST_':
    # Adding the GEOM_FUNC_PREFIX to the lookup functions.
    for lookup, func in POSTGIS_GEOMETRY_FUNCTIONS.items():
        if isinstance(func, tuple):
            POSTGIS_GEOMETRY_FUNCTIONS[lookup] = (GEOM_FUNC_PREFIX + func[0], func[1])
        else:
            POSTGIS_GEOMETRY_FUNCTIONS[lookup] = GEOM_FUNC_PREFIX + func

    # The ST_DWithin, ST_CoveredBy, and ST_Covers routines become available in 1.2.2+
    POSTGIS_GEOMETRY_FUNCTIONS.update(
        {'dwithin' : ('ST_DWithin', float),
         'coveredby' : 'ST_CoveredBy',
         'covers' : 'ST_Covers',
         }
        )

# Any other lookup types that do not require a mapping.
MISC_TERMS = ['isnull']

# These are the PostGIS-customized QUERY_TERMS -- a list of the lookup types
#  allowed for geographic queries.
POSTGIS_TERMS = list(POSTGIS_OPERATORS.keys()) # Getting the operators first
POSTGIS_TERMS += list(POSTGIS_GEOMETRY_FUNCTIONS.keys()) # Adding on the Geometry Functions
POSTGIS_TERMS += MISC_TERMS # Adding any other miscellaneous terms (e.g., 'isnull')
POSTGIS_TERMS = tuple(POSTGIS_TERMS) # Making immutable

### PostGIS-specific Methods ###
def get_geom_func(lookup_type):
    func_info = POSTGIS_GEOMETRY_FUNCTIONS[lookup_type]
    if isinstance(func_info, tuple):
        return func_info[0]
    else:
        return func_info

def get_geo_where_clause(lookup_type, table_prefix, field_name, value):
    "Returns the SQL WHERE clause for use in PostGIS SQL construction."
    if table_prefix.endswith('.'):
        table_prefix = qn(table_prefix[:-1])+'.'
    field_name = qn(field_name)

    # See if a PostGIS operator matches the lookup type first
    if lookup_type in POSTGIS_OPERATORS:
        return '%s%s %s %%s' % (table_prefix, field_name, POSTGIS_OPERATORS[lookup_type])

    # See if a PostGIS Geometry function matches the lookup type next
    if lookup_type in POSTGIS_GEOMETRY_FUNCTIONS:
        lookup_info = POSTGIS_GEOMETRY_FUNCTIONS[lookup_type]
        # Lookup types that are tuples take tuple arguments, e.g., 'relate' and 
        #  'dwithin' lookup types.
        if isinstance(lookup_info, tuple):
            # First element of tuple is lookup type, second element is the type
            #  of the expected argument (e.g., str, float)
            func, arg_type = lookup_info

            # Ensuring that a tuple _value_ was passed in from the user
            if not isinstance(value, tuple) or len(value) != 2: 
                raise TypeError('2-element tuple required for `%s` lookup type.' % lookup_type)
            
            # Ensuring the argument type matches what we expect.
            if not isinstance(value[1], arg_type):
                raise TypeError('Argument type should be %s, got %s instead.' % (arg_type, type(value[1])))
            
            return "%s(%s%s, %%s, %%s)" % (func, table_prefix, field_name)
        else:
            # Returning the SQL necessary for the geometry function call. For example: 
            #  ST_Contains("geoapp_country"."poly", ST_GeomFromWKB(..))
            return '%s(%s%s, %%s)' % (lookup_info, table_prefix, field_name)
    
    # Handling 'isnull' lookup type
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError("Got invalid lookup_type: %s" % repr(lookup_type))

# Functions that we define manually.
if MAJOR_VERSION == 1:
    if MINOR_VERSION1 == 3:
        # PostGIS versions 1.3.x
        ASKML = 'ST_AsKML'
        ASGML = 'ST_AsGML'
        GEOM_FROM_TEXT = 'ST_GeomFromText'
        GEOM_FROM_WKB = 'ST_GeomFromWKB'
        UNION = 'ST_Union'
        TRANSFORM = 'ST_Transform'
    elif MINOR_VERSION1 == 2 and MINOR_VERSION2 >= 1:
        # PostGIS versions 1.2.x
        ASKML = 'AsKML'
        ASGML = 'AsGML'
        GEOM_FROM_TEXT = 'GeomFromText'
        GEOM_FROM_WKB = 'GeomFromWKB'
        UNION = 'GeomUnion'
        TRANSFORM = 'Transform'
    elif MINOR_VERSION1 == 1 and MINOR_VERSION2 >= 0:
        # PostGIS versions 1.1.x
        ASKML = False
        ASGML = 'AsGML'
        GEOM_FROM_TEXT = 'GeomFromText'
        GEOM_FROM_WKB = 'GeomFromWKB'
        TRANSFORM = 'Transform'
        UNION = 'GeomUnion'

# Custom selection not needed for PostGIS since GEOS geometries may be
# instantiated directly from the HEXEWKB returned by default.  If
# WKT is needed for some reason in the future, this value may be changed,
# 'AsText(%s)'
GEOM_SELECT = None
