# This module is meant to re-define the helper routines used by the
# django.db.models.query objects to be customized for PostGIS.
from copy import copy
from django.db import backend
from django.db.models.query import \
     LOOKUP_SEPARATOR, QUERY_TERMS, \
     find_field, FieldFound, get_where_clause
from django.utils.datastructures import SortedDict

# PostGIS-specific operators. The commented descriptions of these
# operators come from Section 6.2.2 of the official PostGIS documentation.
POSTGIS_OPERATORS = {
    # The "&<" operator returns true if A's bounding box overlaps or is to the left of B's bounding box.
    'overlapsleft' : '&< %s',
    # The "&>" operator returns true if A's bounding box overlaps or is to the right of B's bounding box.
    'overlapsright' : '&> %s',
    # The "<<" operator returns true if A's bounding box is strictly to the left of B's bounding box.
    'left' : '<< %s',
    # The ">>" operator returns true if A's bounding box is strictly to the right of B's bounding box.
    'right' : '>> %s',
    # The "&<|" operator returns true if A's bounding box overlaps or is below B's bounding box.
    'overlapsbelow' : '&<| %s',
    # The "|&>" operator returns true if A's bounding box overlaps or is above B's bounding box.
    'overlapsabove' : '|&> %s',
    # The "<<|" operator returns true if A's bounding box is strictly below B's bounding box.
    'strictlybelow' : '<<| %s',
    # The "|>>" operator returns true if A's bounding box is strictly above B's bounding box.
    'strictlyabove' : '|>> %s',
    # The "~=" operator is the "same as" operator. It tests actual geometric equality of two features. So if
    # A and B are the same feature, vertex-by-vertex, the operator returns true.
    'sameas' : '~= %s',
    # The "@" operator returns true if A's bounding box is completely contained by B's bounding box.
    'contained' : '@ %s',
    # The "~" operator returns true if A's bounding box completely contains B's bounding box.
    'bbcontains' : '~ %s',
    # The "&&" operator is the "overlaps" operator. If A's bounding boux overlaps B's bounding box the
    # operator returns true.
    'bboverlaps' : '&& %s',
    }

# PostGIS Geometry Functions -- most of these use GEOS.
POSTGIS_GEOMETRY_FUNCTIONS = {
    'distance' : 'Distance',
    'equals' : 'Equals',
    'disjoint' : 'Disjoint',
    'intersects' : 'Intersects',
    'touches' : 'Touches',
    'crosses' : 'Crosses',
    'within' : 'Within',
    'overlaps' : 'Overlaps',
    'contains' : 'Contains',
    'intersects' : 'Intersects',
    'relate' : 'Relate',
    }

# These are the PostGIS-customized QUERY_TERMS, combines both the operators
# and the geometry functions.
POSTGIS_TERMS = list(POSTGIS_OPERATORS.keys()) # Getting the operators first
POSTGIS_TERMS.extend(list(POSTGIS_GEOMETRY_FUNCTIONS.keys())) # Adding on the Geometry Functions

def get_geo_where_clause(lookup_type, table_prefix, field_name, value):
    if table_prefix.endswith('.'):
        table_prefix = backend.quote_name(table_prefix[:-1])+'.'
    field_name = backend.quote_name(field_name)

    # See if a PostGIS operator matches the lookup type first
    try:
        return '%s%s %s' % (table_prefix, field_name, (POSTGIS_OPERATORS[lookup_type] % '%s'))
    except KeyError:
        pass

    # See if a PostGIS Geometry function matches the lookup type next
    try:
        return '%s(%s%s, %%s)' % (POSTGIS_GEOMETRY_FUNCTIONS[lookup_type], table_prefix, field_name)
    except KeyError:
        pass

    # For any other lookup type
    if lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))

    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def geo_parse_lookup(kwarg_items, opts):
    # Helper function that handles converting API kwargs
    # (e.g. "name__exact": "tom") to SQL.
    # Returns a tuple of (tables, joins, where, params).

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
        elif len(path) == 0 or lookup_type not in POSTGIS_TERMS:
            path.append(lookup_type)
            lookup_type = 'exact'

        if len(path) < 1:
            raise TypeError, "Cannot parse keyword query %r" % kwarg

        if value is None:
            # Interpret '__exact=None' as the sql '= NULL'; otherwise, reject
            # all uses of None as a query value.
            if lookup_type != 'exact':
                raise ValueError, "Cannot use None as a query value"

        joins2, where2, params2 = lookup_inner(path, lookup_type, value, opts, opts.db_table, None)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)
    return joins, where, params

def lookup_inner(path, lookup_type, value, opts, table, column):
    qn = backend.quote_name
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
        raise TypeError, "Cannot resolve keyword '%s' into field" % name

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

        # If the field is a geometry field, then the WHERE clause will need to be obtained
        # with the get_geo_where_clause()
        if hasattr(field, '_geom'):
            where.append(get_geo_where_clause(lookup_type, current_table + '.', column, value))
        else:
            raise TypeError, 'Field "%s" (%s) is not a Geometry Field.' % (column, field.__class__.__name__)
        params.extend(field.get_db_prep_lookup(lookup_type, value))

    return joins, where, params

