"""
 This module provides the backend for spatial SQL construction with Django.

 Specifically, this module will import the correct routines and modules
 needed for GeoDjango.
 
 (1) GeoBackEndField, a base class needed for GeometryField.
 (2) GIS_TERMS, a list of acceptable geographic lookup types for 
     the backend.
 (3) The `parse_lookup` function, used for spatial SQL construction by
     the GeoQuerySet.
 (4) The `create_spatial_db`, and `get_geo_where_clause` 
     (needed by `parse_lookup`) functions.
 (5) The `SpatialBackend` object, which contains information specific
     to the spatial backend.
"""
from django.conf import settings
from django.db import connection
from django.db.models.query import field_choices, find_field, get_where_clause, \
    FieldFound, LOOKUP_SEPARATOR, QUERY_TERMS
from django.utils.datastructures import SortedDict
from django.contrib.gis.db.backend.util import gqn

# These routines (needed by GeoManager), default to False.
ASGML, ASKML, DISTANCE, DISTANCE_SPHEROID, EXTENT, TRANSFORM, UNION, VERSION = tuple(False for i in range(8))

# Lookup types in which the rest of the parameters are not 
# needed to be substitute in the WHERE SQL (e.g., the 'relate'
# operation on Oracle does not need the mask substituted back
# into the query SQL.).
LIMITED_WHERE = []

# Retrieving the necessary settings from the backend.
if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    from django.contrib.gis.db.backend.postgis.adaptor import \
        PostGISAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.postgis.field import \
        PostGISField as GeoBackendField
    from django.contrib.gis.db.backend.postgis.creation import create_spatial_db
    from django.contrib.gis.db.backend.postgis.query import \
        get_geo_where_clause, POSTGIS_TERMS as GIS_TERMS, \
        ASGML, ASKML, DISTANCE, DISTANCE_SPHEROID, DISTANCE_FUNCTIONS, \
        EXTENT, GEOM_SELECT, TRANSFORM, UNION, \
        MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2
    # PostGIS version info is needed to determine calling order of some
    # stored procedures (e.g., AsGML()).
    VERSION = (MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2)
    SPATIAL_BACKEND = 'postgis'
elif settings.DATABASE_ENGINE == 'oracle':
    from django.contrib.gis.db.backend.oracle.adaptor import \
        OracleSpatialAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.oracle.field import \
        OracleSpatialField as GeoBackendField
    from django.contrib.gis.db.backend.oracle.creation import create_spatial_db
    from django.contrib.gis.db.backend.oracle.query import \
        get_geo_where_clause, ORACLE_SPATIAL_TERMS as GIS_TERMS, \
        ASGML, DISTANCE, DISTANCE_FUNCTIONS, GEOM_SELECT, TRANSFORM, UNION
    SPATIAL_BACKEND = 'oracle'
    LIMITED_WHERE = ['relate']
elif settings.DATABASE_ENGINE == 'mysql':
    from django.contrib.gis.db.backend.mysql.adaptor import \
        MySQLAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.mysql.field import \
        MySQLGeoField as GeoBackendField
    from django.contrib.gis.db.backend.mysql.creation import create_spatial_db
    from django.contrib.gis.db.backend.mysql.query import \
        get_geo_where_clause, MYSQL_GIS_TERMS as GIS_TERMS, GEOM_SELECT
    DISTANCE_FUNCTIONS = {}
    SPATIAL_BACKEND = 'mysql'
else:
    raise NotImplementedError('No Geographic Backend exists for %s' % settings.DATABASE_ENGINE)

class SpatialBackend(object):
    "A container for properties of the SpatialBackend."
    # Stored procedure names used by the `GeoManager`.
    as_kml = ASKML
    as_gml = ASGML
    distance = DISTANCE
    distance_spheroid = DISTANCE_SPHEROID
    extent = EXTENT
    name = SPATIAL_BACKEND
    select = GEOM_SELECT
    transform = TRANSFORM
    union = UNION
    
    # Version information, if defined.
    version = VERSION
    
    # All valid GIS lookup terms, and distance functions.
    gis_terms = GIS_TERMS
    distance_functions = DISTANCE_FUNCTIONS
    
    # Lookup types where additional WHERE parameters are excluded.
    limited_where = LIMITED_WHERE

    # Class for the backend field.
    Field = GeoBackendField

    # Adaptor class used for quoting GEOS geometries in the database.
    Adaptor = GeoAdaptor

####    query.py overloaded functions    ####
# parse_lookup() and lookup_inner() are modified from their django/db/models/query.py
#  counterparts to support constructing SQL for geographic queries.
#
# Status: Synced with r7098.
#
def parse_lookup(kwarg_items, opts):
    # Helper function that handles converting API kwargs
    # (e.g. "name__exact": "tom") to SQL.
    # Returns a tuple of (joins, where, params).

    # 'joins' is a sorted dictionary describing the tables that must be joined
    # to complete the query. The dictionary is sorted because creation order
    # is significant; it is a dictionary to ensure uniqueness of alias names.
    #
    # Each key-value pair follows the form
    #   alias: (table, join_type, condition)
    # where
    #   alias is the AS alias for the joined table
    #   table is the actual table name to be joined
    #   join_type is the type of join (INNER JOIN, LEFT OUTER JOIN, etc)
    #   condition is the where-like statement over which narrows the join.
    #   alias will be derived from the lookup list name.
    #
    # At present, this method only every returns INNER JOINs; the option is
    # there for others to implement custom Q()s, etc that return other join
    # types.
    joins, where, params = SortedDict(), [], []

    for kwarg, value in kwarg_items:
        path = kwarg.split(LOOKUP_SEPARATOR)
        # Extract the last elements of the kwarg.
        # The very-last is the lookup_type (equals, like, etc).
        # The second-last is the table column on which the lookup_type is
        # to be performed. If this name is 'pk', it will be substituted with
        # the name of the primary key.
        # If there is only one part, or the last part is not a query
        # term, assume that the query is an __exact
        lookup_type = path.pop()
        if lookup_type == 'pk':
            lookup_type = 'exact'
            path.append(None)
        elif len(path) == 0 or not ((lookup_type in QUERY_TERMS) or (lookup_type in GIS_TERMS)):
            path.append(lookup_type)
            lookup_type = 'exact'

        if len(path) < 1:
            raise TypeError, "Cannot parse keyword query %r" % kwarg

        if value is None:
            # Interpret '__exact=None' as the sql '= NULL'; otherwise, reject
            # all uses of None as a query value.
            if lookup_type != 'exact':
                raise ValueError, "Cannot use None as a query value"
        elif callable(value):
            value = value()
        
        joins2, where2, params2 = lookup_inner(path, lookup_type, value, opts, opts.db_table, None)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)
    return joins, where, params

def lookup_inner(path, lookup_type, value, opts, table, column):
    qn = connection.ops.quote_name
    joins, where, params = SortedDict(), [], []
    current_opts = opts
    current_table = table
    current_column = column
    intermediate_table = None
    join_required = False

    name = path.pop(0)
    # Has the primary key been requested? If so, expand it out
    # to be the name of the current class' primary key
    if name is None or name == 'pk':
        name = current_opts.pk.name

    # Try to find the name in the fields associated with the current class
    try:
        # Does the name belong to a defined many-to-many field?
        field = find_field(name, current_opts.many_to_many, False)
        if field:
            new_table = current_table + '__' + name
            new_opts = field.rel.to._meta
            new_column = new_opts.pk.column

            # Need to create an intermediate table join over the m2m table
            # This process hijacks current_table/column to point to the
            # intermediate table.
            current_table = "m2m_" + new_table
            intermediate_table = field.m2m_db_table()
            join_column = field.m2m_reverse_name()
            intermediate_column = field.m2m_column_name()

            raise FieldFound

        # Does the name belong to a reverse defined many-to-many field?
        field = find_field(name, current_opts.get_all_related_many_to_many_objects(), True)
        if field:
            new_table = current_table + '__' + name
            new_opts = field.opts
            new_column = new_opts.pk.column

            # Need to create an intermediate table join over the m2m table.
            # This process hijacks current_table/column to point to the
            # intermediate table.
            current_table = "m2m_" + new_table
            intermediate_table = field.field.m2m_db_table()
            join_column = field.field.m2m_column_name()
            intermediate_column = field.field.m2m_reverse_name()

            raise FieldFound

        # Does the name belong to a one-to-many field?
        field = find_field(name, current_opts.get_all_related_objects(), True)
        if field:
            new_table = table + '__' + name
            new_opts = field.opts
            new_column = field.field.column
            join_column = opts.pk.column

            # 1-N fields MUST be joined, regardless of any other conditions.
            join_required = True

            raise FieldFound

        # Does the name belong to a one-to-one, many-to-one, or regular field?
        field = find_field(name, current_opts.fields, False)
        if field:
            if field.rel: # One-to-One/Many-to-one field
                new_table = current_table + '__' + name
                new_opts = field.rel.to._meta
                new_column = new_opts.pk.column
                join_column = field.column
                raise FieldFound
            elif path:
                # For regular fields, if there are still items on the path,
                # an error has been made. We munge "name" so that the error
                # properly identifies the cause of the problem.
                name += LOOKUP_SEPARATOR + path[0]
            else:
                raise FieldFound

    except FieldFound: # Match found, loop has been shortcut.
        pass
    else: # No match found.
        choices = field_choices(current_opts.many_to_many, False) + \
            field_choices(current_opts.get_all_related_many_to_many_objects(), True) + \
            field_choices(current_opts.get_all_related_objects(), True) + \
            field_choices(current_opts.fields, False)
        raise TypeError, "Cannot resolve keyword '%s' into field. Choices are: %s" % (name, ", ".join(choices))

    # Check whether an intermediate join is required between current_table
    # and new_table.
    if intermediate_table:
        joins[qn(current_table)] = (
            qn(intermediate_table), "LEFT OUTER JOIN",
            "%s.%s = %s.%s" % (qn(table), qn(current_opts.pk.column), qn(current_table), qn(intermediate_column))
        )

    if path:
        # There are elements left in the path. More joins are required.
        if len(path) == 1 and path[0] in (new_opts.pk.name, None) \
            and lookup_type in ('exact', 'isnull') and not join_required:
            # If the next and final name query is for a primary key,
            # and the search is for isnull/exact, then the current
            # (for N-1) or intermediate (for N-N) table can be used
            # for the search. No need to join an extra table just
            # to check the primary key.
            new_table = current_table
        else:
            # There are 1 or more name queries pending, and we have ruled out
            # any shortcuts; therefore, a join is required.
            joins[qn(new_table)] = (
                qn(new_opts.db_table), "INNER JOIN",
                "%s.%s = %s.%s" % (qn(current_table), qn(join_column), qn(new_table), qn(new_column))
            )
            # If we have made the join, we don't need to tell subsequent
            # recursive calls about the column name we joined on.
            join_column = None

        # There are name queries remaining. Recurse deeper.
        joins2, where2, params2 = lookup_inner(path, lookup_type, value, new_opts, new_table, join_column)

        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)
    else:
        # No elements left in path. Current element is the element on which
        # the search is being performed.
        db_type = None

        if join_required:
            # Last query term is a RelatedObject
            if field.field.rel.multiple:
                # RelatedObject is from a 1-N relation.
                # Join is required; query operates on joined table.
                column = new_opts.pk.name
                joins[qn(new_table)] = (
                    qn(new_opts.db_table), "INNER JOIN",
                    "%s.%s = %s.%s" % (qn(current_table), qn(join_column), qn(new_table), qn(new_column))
                )
                current_table = new_table
            else:
                # RelatedObject is from a 1-1 relation,
                # No need to join; get the pk value from the related object,
                # and compare using that.
                column = current_opts.pk.name
        elif intermediate_table:
            # Last query term is a related object from an N-N relation.
            # Join from intermediate table is sufficient.
            column = join_column
        elif name == current_opts.pk.name and lookup_type in ('exact', 'isnull') and current_column:
            # Last query term is for a primary key. If previous iterations
            # introduced a current/intermediate table that can be used to
            # optimize the query, then use that table and column name.
            column = current_column
        else:
            # Last query term was a normal field.
            column = field.column
            db_type = field.db_type()

        # If the field is a geometry field, then the WHERE clause will need to be obtained
        # with the get_geo_where_clause()
        if hasattr(field, '_geom'):
            # Getting additional SQL WHERE and params arrays associated with 
            # the geographic field.
            geo_where, geo_params = field.get_db_prep_lookup(lookup_type, value)
            
            # Getting the geographic WHERE clause.
            gwc = get_geo_where_clause(lookup_type, current_table, field, value)

            # Appending the geographic WHERE componnents and parameters onto
            # the where and params arrays. 
            where.append(gwc % tuple(geo_where))
            params.extend(geo_params)
        else:
            where.append(get_where_clause(lookup_type, current_table + '.', column, value, db_type))
            params.extend(field.get_db_prep_lookup(lookup_type, value))

    return joins, where, params
