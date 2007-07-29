"""
  This module contains the spatial lookup types, and the get_geo_where_clause()
  routine for PostGIS.
"""
from django.db import backend
from management import postgis_lib_version

# Getting the PostGIS version
POSTGIS_VERSION = postgis_lib_version()
MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2 = map(int, POSTGIS_VERSION.split('.'))

# The supported PostGIS versions.
#  TODO: Confirm tests with PostGIS versions 1.1.x -- should work.  Versions <= 1.0.x didn't use GEOS C API.
if MAJOR_VERSION != 1 or MINOR_VERSION1 <= 1:
    raise Exception, 'PostGIS version %s not supported.' % POSTGIS_VERSION

# PostGIS-specific operators. The commented descriptions of these
# operators come from Section 6.2.2 of the official PostGIS documentation.
POSTGIS_OPERATORS = {
    # The "&<" operator returns true if A's bounding box overlaps or is to the left of B's bounding box.
    'overlaps_left' : '&<',
    # The "&>" operator returns true if A's bounding box overlaps or is to the right of B's bounding box.
    'overlaps_right' : '&>',
    # The "<<" operator returns true if A's bounding box is strictly to the left of B's bounding box.
    'left' : '<<',
    # The ">>" operator returns true if A's bounding box is strictly to the right of B's bounding box.
    'right' : '>>',
    # The "&<|" operator returns true if A's bounding box overlaps or is below B's bounding box.
    'overlaps_below' : '&<|',
    # The "|&>" operator returns true if A's bounding box overlaps or is above B's bounding box.
    'overlaps_above' : '|&>',
    # The "<<|" operator returns true if A's bounding box is strictly below B's bounding box.
    'strictly_below' : '<<|',
    # The "|>>" operator returns true if A's bounding box is strictly above B's bounding box.
    'strictly_above' : '|>>',
    # The "~=" operator is the "same as" operator. It tests actual geometric equality of two features. So if
    # A and B are the same feature, vertex-by-vertex, the operator returns true.
    'same_as' : '~=',
    'exact' : '~=',
    # The "@" operator returns true if A's bounding box is completely contained by B's bounding box.
    'contained' : '@',
    # The "~" operator returns true if A's bounding box completely contains B's bounding box.
    'bbcontains' : '~',
    # The "&&" operator is the "overlaps" operator. If A's bounding boux overlaps B's bounding box the
    # operator returns true.
    'bboverlaps' : '&&',
    }

# PostGIS Geometry Relationship Functions -- most of these use GEOS.
#
# For PostGIS >= 1.2.2 these routines will do a bounding box query first before calling
#  the more expensive GEOS routines (called 'inline index magic').
#
POSTGIS_GEOMETRY_FUNCTIONS = {
    'equals' : '%sEquals',
    'disjoint' : '%sDisjoint',
    'touches' : '%sTouches',
    'crosses' : '%sCrosses',
    'within' : '%sWithin',
    'overlaps' : '%sOverlaps',
    'contains' : '%sContains',
    'intersects' : '%sIntersects',
    'relate' : ('%sRelate', str),
    }

# Versions of PostGIS >= 1.2.2 changed their naming convention to be 'SQL-MM-centric'.
#  Practically, this means that 'ST_' is appended to geometry function names.
if MINOR_VERSION1 >= 2 and MINOR_VERSION2 >= 2:
    # The ST_DWithin, ST_CoveredBy, and ST_Covers routines become available in 1.2.2.
    POSTGIS_GEOMETRY_FUNCTIONS.update(
        {'dwithin' : ('%sDWithin', float),
         'coveredby' : '%sCoveredBy',
         'covers' : '%sCovers',
         }
        )
    GEOM_FUNC_PREFIX = 'ST_'
else:
    GEOM_FUNC_PREFIX = ''

# Updating with the geometry function prefix.
for k, v in POSTGIS_GEOMETRY_FUNCTIONS.items():
    if isinstance(v, tuple):
        v = list(v)
        v[0] = v[0] % GEOM_FUNC_PREFIX
        v = tuple(v)
    else:
        v = v % GEOM_FUNC_PREFIX
    POSTGIS_GEOMETRY_FUNCTIONS[k] = v

# Any other lookup types that do not require a mapping.
MISC_TERMS = ['isnull']

# The quotation used for postgis (uses single quotes).
def quotename(value, dbl=False):
    if dbl: return '"%s"' % value
    else: return "'%s'" % value

# These are the PostGIS-customized QUERY_TERMS -- a list of the lookup types
#  allowed for geographic queries.
POSTGIS_TERMS = list(POSTGIS_OPERATORS.keys()) # Getting the operators first
POSTGIS_TERMS += list(POSTGIS_GEOMETRY_FUNCTIONS.keys()) # Adding on the Geometry Functions
POSTGIS_TERMS += MISC_TERMS # Adding any other miscellaneous terms (e.g., 'isnull')
POSTGIS_TERMS = tuple(POSTGIS_TERMS) # Making immutable

def get_geo_where_clause(lookup_type, table_prefix, field_name, value):
    "Returns the SQL WHERE clause for use in PostGIS SQL construction."
    if table_prefix.endswith('.'):
        table_prefix = backend.quote_name(table_prefix[:-1])+'.'
    field_name = backend.quote_name(field_name)

    # See if a PostGIS operator matches the lookup type first
    try:
        return '%s%s %s %%s' % (table_prefix, field_name, POSTGIS_OPERATORS[lookup_type])
    except KeyError:
        pass

    # See if a PostGIS Geometry function matches the lookup type next
    try:
        return '%s(%s%s, %%s)' % (POSTGIS_GEOMETRY_FUNCTIONS[lookup_type], table_prefix, field_name)
    except KeyError:
        pass
    
    # Handling 'isnull' lookup type
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)
