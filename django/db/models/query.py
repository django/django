from django.db import backend, connection
from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
import copy

LOOKUP_SEPARATOR = '__'

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

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

class QuerySet(object):
    "Represents a lazy database lookup for a set of objects"
    # Sub classes need to provide 'opts' member for this class
    # to be able to function.
    def __init__(self):
        self._filter = Q()
        self._order_by = ()
        self._select_related = False
        self._distinct = True
        self._result_cache = None
        self._params = None
        self._select = None
        self._where = None
        self._tables = None
        self._offset = None
        self._limit = None
        self._use_cache = False

    def filter(self, **kwargs):
        """Returns a new query instance with the query arguments
        ANDed to the existing set"""
        clone = self._clone()
        clone._filter = self._filter & Q(**kwargs)
        return clone

    def unique(self, true_or_false):
        """Returns a new query instance with the 'unique' qualifier modified"""
        return self._clone(_distinct=true_or_false)

    def order_by(self, *field_names):
        """Returns a new query instance with the ordering changed."""
        return self._clone(_order_by=field_names)

    def select_related(self, true_or_false):
        """Returns a new query instance with the 'related' qualifier modified"""
        return self._clone(_related=true_or_false)

    def count(self):
        counter = self._clone()
        counter._order_by = []

        # TODO - do we change these or not?
        # e.g. if someone does objects[0:10].count()
        # (which
        #counter._offset = None
        #counter._limit = None
        counter._select_related = False
        _, sql, params = counter._get_sql_clause(True)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*)" + sql, params)
        return cursor.fetchone()[0]

    # Convenience function for subclasses
    def _set_core_filter(self, **kwargs):
        """Sets the filters that should always be applied to queries"""
        self._filter = Q(**kwargs)

    def _clone(self, **kwargs):
        """Gets a clone of the object, with optional kwargs to alter the clone"""
        # Don't clone (even temporarily) the cache
        _result_cache_save = self._result_cache
        self._result_cache = None
        # Must ensure we get fully deep copies of all the query objects
        clone = copy.deepcopy(self)
        # apply changes to clone
        clone.__dict__.update(kwargs)
        # restore cache
        self._result_cache = _result_cache_save
        return clone

    def _ensure_compatible(self, other):
        if self._distinct != other._distinct:
            raise ValueException, "Can't combine a unique query with a non-unique query"

    def _combine(self, other):
        self._ensure_compatible(other)
        # get a deepcopy of 'other's order by
        #  (so that A.filter(args1) & A.filter(args2) does the same as
        #   A.filter(args1).filter(args2)
        combined = other._clone()
        # If 'self' is ordered and 'other' isn't, propagate 'self's ordering
        if len(self._order_by) > 0 and len(combined._order_by == 0):
            combined._order_by = copy.deepcopy(self._order_by)
        return combined

    def extras(self, params=None, select=None, where=None, tables=None):
        return self._clone(_params=params, _select=select, _where=where, _tables=tables)

    def __and__(self, other):
        combined = self._combine(other)
        combined._filter = self._filter & other._filter
        return combined

    def __or__(self, other):
        combined = self._combine(other)
        combined._filter = self._filter | other._filter
        return combined

    # TODO - allow_joins - do we need it?
    def _get_sql_clause(self, allow_joins):
        def quote_only_if_word(word):
            if ' ' in word:
                return word
            else:
                return backend.quote_name(word)

        # This is defined by sub-classes
        # TODO - define a better accessor
        opts = self.klass._meta

        # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
        select = ["%s.%s" % (backend.quote_name(opts.db_table), backend.quote_name(f.column)) for f in opts.fields]

        tables = [quote_only_if_word(t) for t in (self._tables or [])]
        joins = SortedDict()
        where = self._where or []
        params = self._params or []

        # Convert the Q object into SQL.
        tables2, joins2, where2, params2 = self._filter.get_sql(opts)

        tables.extend(tables2)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)

        # Add additional tables and WHERE clauses based on select_related.
        if self._select_related is True:
            fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])

        # Add any additional SELECTs.
        if self._select:
            select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in self._select ])

        # Start composing the body of the SQL statement.
        sql = [" FROM", backend.quote_name(opts.db_table)]

        # Check if extra tables are allowed. If not, throw an error
        if (tables or joins) and not allow_joins:
            raise TypeError, "Joins are not allowed in this type of query"

        # Compose the join dictionary into SQL describing the joins.
        if joins:
            sql.append(" ".join(["%s %s AS %s ON %s" % (join_type, table, alias, condition)
                            for (alias, (table, join_type, condition)) in joins.items()]))

        # Compose the tables clause into SQL.
        if tables:
            sql.append(", " + ", ".join(tables))

        # Compose the where clause into SQL.
        if where:
            sql.append(where and "WHERE " + " AND ".join(where))

        # ORDER BY clause
        order_by = []
        for f in handle_legacy_orderlist(self._order_by):
            if f == '?': # Special case.
                order_by.append(backend.get_random_function_sql())
            else:
                if f.startswith('-'):
                    col_name = f[1:]
                    order = "DESC"
                else:
                    col_name = f
                    order = "ASC"
                if "." in col_name:
                    table_prefix, col_name = col_name.split('.', 1)
                    table_prefix = backend.quote_name(table_prefix) + '.'
                else:
                    # Use the database table as a column prefix if it wasn't given,
                    # and if the requested column isn't a custom SELECT.
                    if "." not in col_name and col_name not in [k[0] for k in (self._select or []) ]:
                        table_prefix = backend.quote_name(opts.db_table) + '.'
                    else:
                        table_prefix = ''
                order_by.append('%s%s %s' % (table_prefix, backend.quote_name(orderfield2column(col_name, opts)), order))
        if order_by:
            sql.append("ORDER BY " + ", ".join(order_by))

        # LIMIT and OFFSET clauses
        if self._limit is not None:
            sql.append("%s " % backend.get_limit_offset_sql(self._limit, self._offset))
        else:
            assert self._offset is None, "'offset' is not allowed without 'limit'"

        return select, " ".join(sql), params

    def _fetch_data(self):
        if self._use_cache:
            if self._result_cache is None:
                self._result_cache = list(self.get_iterator())
            return self._result_cache
        else:
            return list(self.get_iterator())

    def __iter__(self):
        """Gets an iterator for the data"""
        # Fetch the data or use get_iterator?  If not, we can't
        # do sequence operations - or doing so will require re-fetching
        # Also, lots of things in current template system break if we
        # don't get it all.
        return iter(self._fetch_data())

    def __len__(self):
        return len(self._fetch_data())

    def __getitem__(self, k):
        """Retrieve an item or slice from the set of results"""
        # getitem can't return query instances, because  .filter()
        # and .order_by() methods on the result would break badly.
        # This means we don't have to worry about arithmetic with
        # self._limit or self._offset - they will both be None
        # at this point
        if isinstance(k, slice):
            # Get a new query if we haven't already got data from db
            if self._result_cache is None:
                # slice.stop and slice.start
                clone = self._clone(_offset=k.start, _limit=k.stop)
                return list(clone)[::k.step]
                # TODO - we are throwing away this retrieved data.
                # We could cache it if we had some kind of sparse
                # list structure we could put it in.
            else:
                return self._result_cache[k]

        else:
            # TODO: possibly use a new query which just gets one item
            # if we haven't already got them all?
            return self._fetch_data()[k]

    def get_iterator(self):
        # self._select is a dictionary, and dictionaries' key order is
        # undefined, so we convert it to a list of tuples.
        _extra_select = (self._select or {}).items()

        cursor = connection.cursor()
        select, sql, params = self._get_sql_clause(True)
        cursor.execute("SELECT " + (self._distinct and "DISTINCT " or "") + ",".join(select) + sql, params)
        fill_cache = self._select_related
        index_end = len(self.klass._meta.fields)
        while 1:
            rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
            if not rows:
                raise StopIteration
            for row in rows:
                if fill_cache:
                    obj, index_end = get_cached_row(self.klass, row, 0)
                else:
                    obj = self.klass(*row[:index_end])
                for i, k in enumerate(_extra_select):
                    setattr(obj, k[0], row[index_end+i])
                yield obj

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
    "Encapsulates queries as objects that can be combined logically."
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
        if value is None:
            pass
        else:
            path = kwarg.split(LOOKUP_SEPARATOR)
            # Extract the last elements of the kwarg.
            # The very-last is the clause (equals, like, etc).
            # The second-last is the table column on which the clause is
            # to be performed.
            # The exceptions to this are:
            # 1)  "pk", which is an implicit id__exact;
            #     if we find "pk", make the clause "exact', and insert
            #     a dummy name of None, which we will replace when
            #     we know which table column to grab as the primary key.
            # 2)  If there is only one part, assume it to be an __exact
            clause = path.pop()
            if clause == 'pk':
                clause = 'exact'
                path.append(None)
            elif len(path) == 0:
                path.append(clause)
                clause = 'exact'

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

def find_field(name, field_list, use_accessor=False):
    """
    Finds a field with a specific name in a list of field instances.
    Returns None if there are no matches, or several matches.
    """

    if use_accessor:
        matches = [f for f in field_list if f.OLD_get_accessor_name() == name]
    else:
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

            raise FieldFound

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

            raise FieldFound

        # Does the name belong to a one-to-many field?
        field = find_field(name, current_opts.get_all_related_objects(), True)
        if field:
            new_table = table + LOOKUP_SEPARATOR + name
            new_opts = field.opts
            new_column = field.field.column
            join_column = opts.pk.column

            # 1-N fields MUST be joined, regardless of any other conditions.
            join_required = True

            raise FieldFound

        # Does the name belong to a one-to-one, many-to-one, or regular field?
        field = find_field(name, current_opts.fields)
        if field:
            if field.rel: # One-to-One/Many-to-one field
                new_table = current_table + LOOKUP_SEPARATOR + name
                new_opts = field.rel.to._meta
                new_column = new_opts.pk.column
                join_column = field.column

            raise FieldFound

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
