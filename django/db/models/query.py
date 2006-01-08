from django.db import backend, connection
from django.db.models.exceptions import *
from django.utils.datastructures import SortedDict

LOOKUP_SEPARATOR = '__'

####################
# HELPER FUNCTIONS #
####################

# Django currently supports two forms of ordering.
# Form 1 (deprecated) example:
#     order_by=(('pub_date', 'DESC'), ('headline', 'ASC'), (None, 'RANDOM'))
# Form 2 (new-style) example:
#     order_by=('-pub_date', 'headline', '?')
# Form 1 is deprecated and will no longer be supported for Django's first
# official release. The following code converts from Form 1 to Form 2.

LEGACY_ORDERING_MAPPING = {'ASC': '_', 'DESC': '-_', 'RANDOM': '?'}

def handle_legacy_orderlist(order_list):
    if not order_list or isinstance(order_list[0], basestring):
        return order_list
    else:
        import warnings
        new_order_list = [LEGACY_ORDERING_MAPPING[j.upper()].replace('_', str(i)) for i, j in order_list]
        warnings.warn("%r ordering syntax is deprecated. Use %r instead." % (order_list, new_order_list), DeprecationWarning)
        return new_order_list

def orderfield2column(f, opts):
    try:
        return opts.get_field(f, False).column
    except FieldDoesNotExist:
        return f

def orderlist2sql(order_list, opts, prefix=''):
    if prefix.endswith('.'):
        prefix = backend.quote_name(prefix[:-1]) + '.'
    output = []
    for f in handle_legacy_orderlist(order_list):
        if f.startswith('-'):
            output.append('%s%s DESC' % (prefix, backend.quote_name(orderfield2column(f[1:], opts))))
        elif f == '?':
            output.append(backend.get_random_function_sql())
        else:
            output.append('%s%s ASC' % (prefix, backend.quote_name(orderfield2column(f, opts))))
    return ', '.join(output)

class QOperator:
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return '(%s)' % self.operator.join([repr(el) for el in self.args])

    def get_sql(self, opts):
        tables, joins, where, params = [], {}, [], []
        for val in self.args:
            tables2, joins2, where2, params2 = val.get_sql(opts)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
        return tables, joins, ['(%s)' % self.operator.join(where)], params

class QAnd(QOperator):
    "Encapsulates a combined query that uses 'AND'."
    operator = ' AND '
    def __or__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def __and__(self, other):
        if isinstance(other, QAnd):
            return QAnd(*(self.args+other.args))
        elif isinstance(other, (Q, QOr)):
            return QAnd(*(self.args+(other,)))
        else:
            raise TypeError, other

class QOr(QOperator):
    "Encapsulates a combined query that uses 'OR'."
    operator = ' OR '
    def __and__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, QOr):
            return QOr(*(self.args+other.args))
        elif isinstance(other, (Q, QAnd)):
            return QOr(*(self.args+(other,)))
        else:
            raise TypeError, other

class Q:
    "Encapsulates queries for the 'complex' parameter to Django API functions."
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return 'Q%r' % self.kwargs

    def __and__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def get_sql(self, opts):
        return parse_lookup(self.kwargs.items(), opts)


def get_where_clause(lookup_type, table_prefix, field_name, value):
    if table_prefix.endswith('.'):
        table_prefix = backend.quote_name(table_prefix[:-1])+'.'
    field_name = backend.quote_name(field_name)
    try:
        return '%s%s %s' % (table_prefix, field_name, (backend.OPERATOR_MAPPING[lookup_type] % '%s'))
    except KeyError:
        pass
    if lookup_type == 'in':
        return '%s%s IN (%s)' % (table_prefix, field_name, ','.join(['%s' for v in value]))
    elif lookup_type in ('range', 'year'):
        return '%s%s BETWEEN %%s AND %%s' % (table_prefix, field_name)
    elif lookup_type in ('month', 'day'):
        return "%s = %%s" % backend.get_date_extract_sql(lookup_type, table_prefix + field_name)
    elif lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))
    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def get_cached_row(klass, row, index_start):
    "Helper function that recursively returns an object with cache filled"
    index_end = index_start + len(klass._meta.fields)
    obj = klass(*row[index_start:index_end])
    for f in klass._meta.fields:
        if f.rel and not f.null:
            rel_obj, index_end = get_cached_row(f.rel.to, row, index_end)
            setattr(obj, f.get_cache_name(), rel_obj)
    return obj, index_end

def fill_table_cache(opts, select, tables, where, old_prefix, cache_tables_seen):
    """
    Helper function that recursively populates the select, tables and where (in
    place) for fill-cache queries.
    """
    for f in opts.fields:
        if f.rel and not f.null:
            db_table = f.rel.to._meta.db_table
            if db_table not in cache_tables_seen:
                tables.append(backend.quote_name(db_table))
            else: # The table was already seen, so give it a table alias.
                new_prefix = '%s%s' % (db_table, len(cache_tables_seen))
                tables.append('%s %s' % (backend.quote_name(db_table), backend.quote_name(new_prefix)))
                db_table = new_prefix
            cache_tables_seen.append(db_table)
            where.append('%s.%s = %s.%s' % \
                (backend.quote_name(old_prefix), backend.quote_name(f.column),
                backend.quote_name(db_table), backend.quote_name(f.rel.get_related_field().column)))
            select.extend(['%s.%s' % (backend.quote_name(db_table), backend.quote_name(f2.column)) for f2 in f.rel.to._meta.fields])
            fill_table_cache(f.rel.to._meta, select, tables, where, db_table, cache_tables_seen)

def parse_lookup(kwarg_items, opts):
    # Helper function that handles converting API kwargs
    # (e.g. "name__exact": "tom") to SQL.

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
    tables, joins, where, params = [], SortedDict(), [], []
    for kwarg, value in kwarg_items:
        if kwarg in ('order_by', 'limit', 'offset', 'select_related', 'distinct', 'select', 'tables', 'where', 'params'):
            pass
        elif value is None:
            pass
        elif kwarg == 'complex':
            tables2, joins2, where2, params2 = value.get_sql(opts)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
        elif kwarg == '_or':
            for val in value:
                tables2, joins2, where2, params2 = parse_lookup(val, opts)
                tables.extend(tables2)
                joins.update(joins2)
                where.append('(%s)' % ' OR '.join(where2))
                params.extend(params2)
        else: # Must be a search parameter.
            path = kwarg.split(LOOKUP_SEPARATOR)

            # Extract the last elements of the kwarg.
            # The very-last is the clause (equals, like, etc).
            # The second-last is the table column on which the clause is
            # to be performed.
            # The only exception to this is "pk", which is an implicit
            # id__exact; if we find "pk", make the clause "exact', and
            # insert a dummy name of None, which we will replace when
            # we know which table column to grab as the primary key.
            clause = path.pop()
            if clause == 'pk':
                clause = 'exact'
                path.append(None)
            if len(path) < 1:
                raise TypeError, "Cannot parse keyword query %r" % kwarg

            tables2, joins2, where2, params2 = lookup_inner(path, clause, value, opts, opts.db_table, None)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
    return tables, joins, where, params

class FieldFound(Exception):
    "Exception used to short circuit field-finding operations."
    pass

def find_field(name, field_list):
    """
    Finds a field with a specific name in a list of field instances.
    Returns None if there are no matches, or several matches.
    """
    matches = [f for f in field_list if f.name == name]
    if len(matches) != 1:
        return None
    return matches[0]

def lookup_inner(path, clause, value, opts, table, column):
    tables, joins, where, params = [], SortedDict(), [], []
    current_opts = opts
    current_table = table
    current_column = column
    intermediate_table = None
    join_required = False

    name = path.pop(0)
    # Has the primary key been requested? If so, expand it out
    # to be the name of the current class' primary key
    if name is None:
        name = current_opts.pk.name

    # Try to find the name in the fields associated with the current class
    try:
        # Does the name belong to a defined many-to-many field?
        field = find_field(name, current_opts.many_to_many)
        if field:
            new_table = current_table + LOOKUP_SEPARATOR + name
            new_opts = field.rel.to._meta
            new_column = new_opts.pk.column

            # Need to create an intermediate table join over the m2m table
            # This process hijacks current_table/column to point to the
            # intermediate table.
            current_table = "m2m_" + new_table
            join_column = new_opts.object_name.lower() + '_id'
            intermediate_table = field.get_m2m_db_table(current_opts)

            raise FieldFound()

        # Does the name belong to a reverse defined many-to-many field?
        field = find_field(name, current_opts.get_all_related_many_to_many_objects())
        if field:
            new_table = current_table + LOOKUP_SEPARATOR + name
            new_opts = field.opts
            new_column = new_opts.pk.column

            # Need to create an intermediate table join over the m2m table.
            # This process hijacks current_table/column to point to the
            # intermediate table.
            current_table = "m2m_" + new_table
            join_column = new_opts.object_name.lower() + '_id'
            intermediate_table = field.field.get_m2m_db_table(new_opts)

            raise FieldFound()

        # Does the name belong to a one-to-many field?
        field = find_field(name, opts.get_all_related_objects())
        if field:
            new_table = table + LOOKUP_SEPARATOR + name
            new_opts = field.opts
            new_column = field.field.column
            join_column = opts.pk.column

            # 1-N fields MUST be joined, regardless of any other conditions.
            join_required = True

            raise FieldFound()

        # Does the name belong to a one-to-one, many-to-one, or regular field?
        field = find_field(name, current_opts.fields)
        if field:
            if field.rel: # One-to-One/Many-to-one field
                new_table = current_table + LOOKUP_SEPARATOR + name
                new_opts = field.rel.to._meta
                new_column = new_opts.pk.column
                join_column = field.column

            raise FieldFound()

    except FieldFound: # Match found, loop has been shortcut.
        pass
    except: # Any other exception; rethrow
        raise
    else: # No match found.
        raise TypeError, "Cannot resolve keyword '%s' into field" % name

    # Check to see if an intermediate join is required between current_table
    # and new_table.
    if intermediate_table:
        joins[backend.quote_name(current_table)] = (
            backend.quote_name(intermediate_table),
            "INNER JOIN",
            "%s.%s = %s.%s" % \
                (backend.quote_name(table),
                backend.quote_name(current_opts.pk.column),
                backend.quote_name(current_table),
                backend.quote_name(current_opts.object_name.lower() + '_id'))
        )

    if path:
        if len(path) == 1 and path[0] in (new_opts.pk.name, None) \
            and clause in ('exact', 'isnull') and not join_required:
            # If the last name query is for a key, and the search is for
            # isnull/exact, then the current (for N-1) or intermediate
            # (for N-N) table can be used for the search - no need to join an
            # extra table just to check the primary key.
            new_table = current_table
        else:
            # There are 1 or more name queries pending, and we have ruled out
            # any shortcuts; therefore, a join is required.
            joins[backend.quote_name(new_table)] = (
                backend.quote_name(new_opts.db_table),
                "INNER JOIN",
                "%s.%s = %s.%s" %
                    (backend.quote_name(current_table),
                    backend.quote_name(join_column),
                    backend.quote_name(new_table),
                    backend.quote_name(new_column))
            )
            # If we have made the join, we don't need to tell subsequent
            # recursive calls about the column name we joined on.
            join_column = None

        # There are name queries remaining. Recurse deeper.
        tables2, joins2, where2, params2 = lookup_inner(path, clause, value, new_opts, new_table, join_column)

        tables.extend(tables2)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)
    else:
        # Evaluate clause on current table.
        if name in (current_opts.pk.name, None) and clause in ('exact', 'isnull') and current_column:
            # If this is an exact/isnull key search, and the last pass
            # found/introduced a current/intermediate table that we can use to
            # optimize the query, then use that column name.
            column = current_column
        else:
            column = field.column

        where.append(get_where_clause(clause, current_table + '.', column, value))
        params.extend(field.get_db_prep_lookup(clause, value))

    return tables, joins, where, params
