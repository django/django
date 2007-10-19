"""
 This module provides the backend for spatial SQL construction with Django.

 Specifically, this module will import the correct routines and modules
 needed for GeoDjango.
 
 (1) GeoBackEndField, a base class needed for GeometryField.
 (2) GeometryProxy, for lazy-instantiated geometries from the 
     database output.
 (3) GIS_TERMS, a list of acceptable geographic lookup types for 
     the backend.
 (4) The `parse_lookup` function, used for spatial SQL construction by
     the GeoQuerySet.
 (5) The `create_spatial_db`, and `get_geo_where_clause`
     routines (needed by `parse_lookup`).

 Currently only PostGIS is supported, but someday backends will be added for
 additional spatial databases (e.g., Oracle, DB2).
"""
from types import StringType, UnicodeType
from django.conf import settings
from django.db import connection
from django.db.models.query import field_choices, find_field, get_where_clause, \
    FieldFound, LOOKUP_SEPARATOR, QUERY_TERMS
from django.utils.datastructures import SortedDict
from django.contrib.gis.geos import GEOSGeometry

# These routines (needed by GeoManager), default to False.
ASGML, ASKML, TRANSFORM, UNION= (False, False, False, False)

if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    # PostGIS is the spatial database, getting the rquired modules, 
    # renaming as necessary.
    from django.contrib.gis.db.backend.postgis import \
        PostGISField as GeoBackendField, POSTGIS_TERMS as GIS_TERMS, \
        create_spatial_db, get_geo_where_clause, gqn, \
        ASGML, ASKML, GEOM_SELECT, TRANSFORM, UNION
    SPATIAL_BACKEND = 'postgis'
elif settings.DATABASE_ENGINE == 'oracle':
    from django.contrib.gis.db.backend.oracle import \
         OracleSpatialField as GeoBackendField, \
         ORACLE_SPATIAL_TERMS as GIS_TERMS, \
         create_spatial_db, get_geo_where_clause, gqn, \
         ASGML, GEOM_SELECT, TRANSFORM, UNION
    SPATIAL_BACKEND = 'oracle'
elif settings.DATABASE_ENGINE == 'mysql':
    from django.contrib.gis.db.backend.mysql import \
        MySQLGeoField as GeoBackendField, \
        MYSQL_GIS_TERMS as GIS_TERMS, \
        create_spatial_db, get_geo_where_clause, gqn, \
        GEOM_SELECT
    SPATIAL_BACKEND = 'mysql'
else:
    raise NotImplementedError('No Geographic Backend exists for %s' % settings.DATABASE_ENGINE)

def geo_quotename(value):
    """
    Returns the quotation used on a given Geometry value using the geometry
    quoting from the backend (the `gqn` function).
    """
    if isinstance(value, (StringType, UnicodeType)): return gqn(value)
    else: return str(value)

####    query.py overloaded functions    ####
# parse_lookup() and lookup_inner() are modified from their django/db/models/query.py
#  counterparts to support constructing SQL for geographic queries.
#
# Status: Synced with r5982.
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
            # Do we have multiple arguments, e.g., `relate`, `dwithin` lookup types
            # need more than argument.
            multiple_args = isinstance(value, tuple)

            # Getting the preparation SQL object from the field.
            if multiple_args:
                geo_prep = field.get_db_prep_lookup(lookup_type, value[0])
            else:
                geo_prep = field.get_db_prep_lookup(lookup_type, value)

            # Getting the adapted geometry from the field.
            gwc = get_geo_where_clause(lookup_type, current_table + '.', column, value)
            
            # A GeoFieldSQL object is returned by `get_db_prep_lookup` -- 
            # getting the substitution list and the geographic parameters.
            subst_list = geo_prep.where
            if multiple_args: subst_list += map(geo_quotename, value[1:])
            gwc = gwc % tuple(subst_list)
            
            # Finally, appending onto the WHERE clause, and extending with
            # the additional parameters.
            where.append(gwc)
            params.extend(geo_prep.params)
        else:
            where.append(get_where_clause(lookup_type, current_table + '.', column, value, db_type))
            params.extend(field.get_db_prep_lookup(lookup_type, value))

    return joins, where, params
