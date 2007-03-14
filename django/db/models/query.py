from django.db import backend, connection, get_query_module, transaction
from django.db.models.fields import DateField, FieldDoesNotExist
from django.db.models.fields.generic import GenericRelation
from django.db.models import signals
from django.dispatch import dispatcher
from django.utils.datastructures import SortedDict
from django.conf import settings
import datetime, operator, re

# For Python 2.3
if not hasattr(__builtins__, 'set'):
    from sets import Set as set

# The string constant used to separate query parts
LOOKUP_SEPARATOR = '__'

# The list of valid query types
QUERY_TERMS = (
    'exact', 'iexact', 'contains', 'icontains',
    'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith',
    'range', 'year', 'month', 'day', 'isnull', 'search',
)

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

class EmptyResultSet(Exception):
    pass

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

def quote_only_if_word(word):
    if re.search('\W', word): # Don't quote if there are spaces or non-word chars.
        return word
    else:
        return backend.quote_name(word)

class _QuerySet(object):
    "Represents a lazy database lookup for a set of objects"
    def __init__(self, model=None):
        self.model = model
        self._filters = Q()
        self._order_by = None        # Ordering, e.g. ('date', '-name'). If None, use model's ordering.
        self._select_related = False # Whether to fill cache for related objects.
        self._max_related_depth = 0  # Maximum "depth" for select_related
        self._distinct = False       # Whether the query should use SELECT DISTINCT.
        self._select = {}            # Dictionary of attname -> SQL.
        self._where = []             # List of extra WHERE clauses to use.
        self._params = []            # List of params to use for extra WHERE clauses.
        self._tables = []            # List of extra tables to use.
        self._offset = None          # OFFSET clause.
        self._limit = None           # LIMIT clause.
        self._result_cache = None

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __repr__(self):
        return repr(self._get_data())

    def __len__(self):
        return len(self._get_data())

    def __iter__(self):
        return iter(self._get_data())

    def __getitem__(self, k):
        "Retrieve an item or slice from the set of results."
        assert (not isinstance(k, slice) and (k >= 0)) \
            or (isinstance(k, slice) and (k.start is None or k.start >= 0) and (k.stop is None or k.stop >= 0)), \
            "Negative indexing is not supported."
        if self._result_cache is None:
            if isinstance(k, slice):
                # Offset:
                if self._offset is None:
                    offset = k.start
                elif k.start is None:
                    offset = self._offset
                else:
                    offset = self._offset + k.start
                # Now adjust offset to the bounds of any existing limit:
                if self._limit is not None and k.start is not None:
                    limit = self._limit - k.start
                else:
                    limit = self._limit

                # Limit:
                if k.stop is not None and k.start is not None:
                    if limit is None:
                        limit = k.stop - k.start
                    else:
                        limit = min((k.stop - k.start), limit)
                else:
                    if limit is None:
                        limit = k.stop
                    else:
                        if k.stop is not None:
                            limit = min(k.stop, limit)

                if k.step is None:
                    return self._clone(_offset=offset, _limit=limit)
                else:
                    return list(self._clone(_offset=offset, _limit=limit))[::k.step]
            else:
                try:
                    return list(self._clone(_offset=k, _limit=1))[0]
                except self.model.DoesNotExist, e:
                    raise IndexError, e.args
        else:
            return self._result_cache[k]

    def __and__(self, other):
        combined = self._combine(other)
        combined._filters = self._filters & other._filters
        return combined

    def __or__(self, other):
        combined = self._combine(other)
        combined._filters = self._filters | other._filters
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def iterator(self):
        "Performs the SELECT database lookup of this QuerySet."
        try:
            select, sql, params, full_query = self._get_sql_clause()
        except EmptyResultSet:
            raise StopIteration

        # self._select is a dictionary, and dictionaries' key order is
        # undefined, so we convert it to a list of tuples.
        extra_select = self._select.items()

        cursor = connection.cursor()
        cursor.execute("SELECT " + (self._distinct and "DISTINCT " or "") + ",".join(select) + sql, params)

        fill_cache = self._select_related
        index_end = len(self.model._meta.fields)
        while 1:
            rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
            if not rows:
                raise StopIteration
            for row in rows:
                if fill_cache:
                    obj, index_end = get_cached_row(klass=self.model, row=row,
                                                    index_start=0, max_depth=self._max_related_depth)
                else:
                    obj = self.model(*row[:index_end])
                for i, k in enumerate(extra_select):
                    setattr(obj, k[0], row[index_end+i])
                yield obj

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the queryset is already cached (i.e. self._result_cache is set) this
        simply returns the length of the cached results set to avoid multiple
        SELECT COUNT(*) calls.
        """
        if self._result_cache is not None:
            return len(self._result_cache)

        counter = self._clone()
        counter._order_by = ()
        counter._select_related = False

        offset = counter._offset
        limit = counter._limit
        counter._offset = None
        counter._limit = None

        try:
            select, sql, params, full_query = counter._get_sql_clause()
        except EmptyResultSet:
            return 0

        cursor = connection.cursor()
        if self._distinct:
            id_col = "%s.%s" % (backend.quote_name(self.model._meta.db_table),
                    backend.quote_name(self.model._meta.pk.column))
            cursor.execute("SELECT COUNT(DISTINCT(%s))" % id_col + sql, params)
        else:
            cursor.execute("SELECT COUNT(*)" + sql, params)
        count = cursor.fetchone()[0]

        # Apply any offset and limit constraints manually, since using LIMIT or
        # OFFSET in SQL doesn't change the output of COUNT.
        if offset:
            count = max(0, count - offset)
        if limit:
            count = min(limit, count)

        return count

    def get(self, *args, **kwargs):
        "Performs the SELECT and returns a single object matching the given keyword arguments."
        clone = self.filter(*args, **kwargs)
        # clean up SQL by removing unneeded ORDER BY
        if not clone._order_by:
            clone._order_by = ()
        obj_list = list(clone)
        if len(obj_list) < 1:
            raise self.model.DoesNotExist, "%s matching query does not exist." % self.model._meta.object_name
        assert len(obj_list) == 1, "get() returned more than one %s -- it returned %s! Lookup parameters were %s" % (self.model._meta.object_name, len(obj_list), kwargs)
        return obj_list[0]

    def create(self, **kwargs):
        """
        Create a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save()
        return obj

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert len(kwargs), 'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
            params.update(defaults)
            obj = self.model(**params)
            obj.save()
            return obj, True

    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        latest_by = field_name or self.model._meta.get_latest_by
        assert bool(latest_by), "latest() requires either a field_name parameter or 'get_latest_by' in the model"
        assert self._limit is None and self._offset is None, \
                "Cannot change a query once a slice has been taken."
        return self._clone(_limit=1, _order_by=('-'+latest_by,)).get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        assert self._limit is None and self._offset is None, \
                "Cannot use 'limit' or 'offset' with in_bulk"
        assert isinstance(id_list, (tuple,  list)), "in_bulk() must be provided with a list of IDs."
        id_list = list(id_list)
        if id_list == []:
            return {}
        qs = self._clone()
        qs._where.append("%s.%s IN (%s)" % (backend.quote_name(self.model._meta.db_table), backend.quote_name(self.model._meta.pk.column), ",".join(['%s'] * len(id_list))))
        qs._params.extend(id_list)
        return dict([(obj._get_pk_val(), obj) for obj in qs.iterator()])

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        assert self._limit is None and self._offset is None, \
            "Cannot use 'limit' or 'offset' with delete."

        del_query = self._clone()

        # disable non-supported fields
        del_query._select_related = False
        del_query._order_by = []

        # Delete objects in chunks to prevent an the list of
        # related objects from becoming too long
        more_objects = True
        while more_objects:
            # Collect all the objects to be deleted in this chunk, and all the objects
            # that are related to the objects that are to be deleted
            seen_objs = SortedDict()
            more_objects = False
            for object in del_query[0:GET_ITERATOR_CHUNK_SIZE]:
                more_objects = True
                object._collect_sub_objects(seen_objs)

            # If one or more objects were found, delete them.
            # Otherwise, stop looping.
            if more_objects:
                delete_objects(seen_objs)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
    delete.alters_data = True

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        return self._clone(klass=ValuesQuerySet, _fields=fields)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates
        for the given field_name, scoped to 'kind'.
        """
        assert kind in ("month", "year", "day"), "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), "'order' must be either 'ASC' or 'DESC'."
        # Let the FieldDoesNotExist exception propagate.
        field = self.model._meta.get_field(field_name, many_to_many=False)
        assert isinstance(field, DateField), "%r isn't a DateField." % field_name
        return self._clone(klass=DateQuerySet, _field=field, _kind=kind, _order=order)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def filter(self, *args, **kwargs):
        "Returns a new QuerySet instance with the args ANDed to the existing set."
        return self._filter_or_exclude(None, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        "Returns a new QuerySet instance with NOT (args) ANDed to the existing set."
        return self._filter_or_exclude(QNot, *args, **kwargs)

    def _filter_or_exclude(self, mapper, *args, **kwargs):
        # mapper is a callable used to transform Q objects,
        # or None for identity transform
        if mapper is None:
            mapper = lambda x: x
        if len(args) > 0 or len(kwargs) > 0:
            assert self._limit is None and self._offset is None, \
                "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if len(kwargs) > 0:
            clone._filters = clone._filters & mapper(Q(**kwargs))
        if len(args) > 0:
            clone._filters = clone._filters & reduce(operator.and_, map(mapper, args))
        return clone

    def complex_filter(self, filter_obj):
        """Returns a new QuerySet instance with filter_obj added to the filters.
        filter_obj can be a Q object (has 'get_sql' method) or a dictionary of
        keyword lookup arguments."""
        # This exists to support framework features such as 'limit_choices_to',
        # and usually it will be more natural to use other methods.
        if hasattr(filter_obj, 'get_sql'):
            return self._filter_or_exclude(None, filter_obj)
        else:
            return self._filter_or_exclude(None, **filter_obj)

    def select_related(self, true_or_false=True, depth=0):
        "Returns a new QuerySet instance with '_select_related' modified."
        return self._clone(_select_related=true_or_false, _max_related_depth=depth)

    def order_by(self, *field_names):
        "Returns a new QuerySet instance with the ordering changed."
        assert self._limit is None and self._offset is None, \
                "Cannot reorder a query once a slice has been taken."
        return self._clone(_order_by=field_names)

    def distinct(self, true_or_false=True):
        "Returns a new QuerySet instance with '_distinct' modified."
        return self._clone(_distinct=true_or_false)

    def extra(self, select=None, where=None, params=None, tables=None):
        assert self._limit is None and self._offset is None, \
                "Cannot change a query once a slice has been taken"
        clone = self._clone()
        if select: clone._select.update(select)
        if where: clone._where.extend(where)
        if params: clone._params.extend(params)
        if tables: clone._tables.extend(tables)
        return clone

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None, **kwargs):
        if klass is None:
            klass = self.__class__
        c = klass()
        c.model = self.model
        c._filters = self._filters
        c._order_by = self._order_by
        c._select_related = self._select_related
        c._max_related_depth = self._max_related_depth
        c._distinct = self._distinct
        c._select = self._select.copy()
        c._where = self._where[:]
        c._params = self._params[:]
        c._tables = self._tables[:]
        c._offset = self._offset
        c._limit = self._limit
        c.__dict__.update(kwargs)
        return c

    def _combine(self, other):
        assert self._limit is None and self._offset is None \
            and other._limit is None and other._offset is None, \
            "Cannot combine queries once a slice has been taken."
        assert self._distinct == other._distinct, \
            "Cannot combine a unique query with a non-unique query"
        #  use 'other's order by
        #  (so that A.filter(args1) & A.filter(args2) does the same as
        #   A.filter(args1).filter(args2)
        combined = other._clone()
        if self._select: combined._select.update(self._select)
        if self._where: combined._where.extend(self._where)
        if self._params: combined._params.extend(self._params)
        if self._tables: combined._tables.extend(self._tables)
        # If 'self' is ordered and 'other' isn't, propagate 'self's ordering
        if (self._order_by is not None and len(self._order_by) > 0) and \
           (combined._order_by is None or len(combined._order_by) == 0):
            combined._order_by = self._order_by
        return combined

    def _get_data(self):
        if self._result_cache is None:
            self._result_cache = list(self.iterator())
        return self._result_cache

    def _get_sql_clause(self):
        opts = self.model._meta

        # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
        select = ["%s.%s" % (backend.quote_name(opts.db_table), backend.quote_name(f.column)) for f in opts.fields]
        tables = [quote_only_if_word(t) for t in self._tables]
        joins = SortedDict()
        where = self._where[:]
        params = self._params[:]

        # Convert self._filters into SQL.
        joins2, where2, params2 = self._filters.get_sql(opts)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)

        # Add additional tables and WHERE clauses based on select_related.
        if self._select_related:
            fill_table_cache(opts, select, tables, where,
                             old_prefix=opts.db_table,
                             cache_tables_seen=[opts.db_table],
                             max_depth=self._max_related_depth)

        # Add any additional SELECTs.
        if self._select:
            select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in self._select.items()])

        # Start composing the body of the SQL statement.
        sql = [" FROM", backend.quote_name(opts.db_table)]

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
        if self._order_by is not None:
            ordering_to_use = self._order_by
        else:
            ordering_to_use = opts.ordering
        for f in handle_legacy_orderlist(ordering_to_use):
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
                    if "." not in col_name and col_name not in (self._select or ()):
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

        return select, " ".join(sql), params, None

# Use the backend's QuerySet class if it defines one, otherwise use _QuerySet.
backend_query_module = get_query_module()
if hasattr(backend_query_module, 'get_query_set_class'):
    QuerySet = backend_query_module.get_query_set_class(_QuerySet)
else:
    QuerySet = _QuerySet

class ValuesQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super(ValuesQuerySet, self).__init__(*args, **kwargs)
        # select_related and select aren't supported in values().
        self._select_related = False
        self._select = {}

    def iterator(self):
        try:
            select, sql, params, full_query = self._get_sql_clause()
        except EmptyResultSet:
            raise StopIteration

        # self._fields is a list of field names to fetch.
        if self._fields:
            columns = [self.model._meta.get_field(f, many_to_many=False).column for f in self._fields]
            field_names = self._fields
        else: # Default to all fields.
            columns = [f.column for f in self.model._meta.fields]
            field_names = [f.attname for f in self.model._meta.fields]

        select = ['%s.%s' % (backend.quote_name(self.model._meta.db_table), backend.quote_name(c)) for c in columns]
        cursor = connection.cursor()
        cursor.execute("SELECT " + (self._distinct and "DISTINCT " or "") + ",".join(select) + sql, params)
        while 1:
            rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
            if not rows:
                raise StopIteration
            for row in rows:
                yield dict(zip(field_names, row))

    def _clone(self, klass=None, **kwargs):
        c = super(ValuesQuerySet, self)._clone(klass, **kwargs)
        c._fields = self._fields[:]
        return c

class DateQuerySet(QuerySet):
    def iterator(self):
        from django.db.backends.util import typecast_timestamp
        self._order_by = () # Clear this because it'll mess things up otherwise.
        if self._field.null:
            self._where.append('%s.%s IS NOT NULL' % \
                (backend.quote_name(self.model._meta.db_table), backend.quote_name(self._field.column)))
        try:
            select, sql, params, full_query = self._get_sql_clause()
        except EmptyResultSet:
            raise StopIteration

        table_name = backend.quote_name(self.model._meta.db_table)
        field_name = backend.quote_name(self._field.column)

        if backend.allows_group_by_ordinal:
            group_by = '1'
        else:
            group_by = backend.get_date_trunc_sql(self._kind,
                                                  '%s.%s' % (table_name, field_name))

        sql = 'SELECT %s %s GROUP BY %s ORDER BY 1 %s' % \
            (backend.get_date_trunc_sql(self._kind, '%s.%s' % (backend.quote_name(self.model._meta.db_table),
            backend.quote_name(self._field.column))), sql, group_by, self._order)
        cursor = connection.cursor()
        cursor.execute(sql, params)
        if backend.needs_datetime_string_cast:
            return [typecast_timestamp(str(row[0])) for row in cursor.fetchall()]
        else:
            return [row[0] for row in cursor.fetchall()]

    def _clone(self, klass=None, **kwargs):
        c = super(DateQuerySet, self)._clone(klass, **kwargs)
        c._field = self._field
        c._kind = self._kind
        c._order = self._order
        return c

class EmptyQuerySet(QuerySet):
    def __init__(self, model=None):
        super(EmptyQuerySet, self).__init__(model)
        self._result_cache = []

    def count(self):
        return 0

    def delete(self):
        pass

    def _clone(self, klass=None, **kwargs):
        c = super(EmptyQuerySet, self)._clone(klass, **kwargs)
        c._result_cache = []
        return c

    def _get_sql_clause(self):
        raise EmptyResultSet

class QOperator(object):
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.args = args

    def get_sql(self, opts):
        joins, where, params = SortedDict(), [], []
        for val in self.args:
            try:
                joins2, where2, params2 = val.get_sql(opts)
                joins.update(joins2)
                where.extend(where2)
                params.extend(params2)
            except EmptyResultSet:
                if not isinstance(self, QOr):
                    raise EmptyResultSet
        if where:
            return joins, ['(%s)' % self.operator.join(where)], params
        return joins, [], params

class QAnd(QOperator):
    "Encapsulates a combined query that uses 'AND'."
    operator = ' AND '
    def __or__(self, other):
        return QOr(self, other)

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
        return QAnd(self, other)

    def __or__(self, other):
        if isinstance(other, QOr):
            return QOr(*(self.args+other.args))
        elif isinstance(other, (Q, QAnd)):
            return QOr(*(self.args+(other,)))
        else:
            raise TypeError, other

class Q(object):
    "Encapsulates queries as objects that can be combined logically."
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)

    def get_sql(self, opts):
        return parse_lookup(self.kwargs.items(), opts)

class QNot(Q):
    "Encapsulates NOT (...) queries as objects"
    def __init__(self, q):
        "Creates a negation of the q object passed in."
        self.q = q

    def get_sql(self, opts):
        try:
            joins, where, params = self.q.get_sql(opts)
            where2 = ['(NOT (%s))' % " AND ".join(where)]
        except EmptyResultSet:
            return SortedDict(), [], []
        return joins, where2, params

def get_where_clause(lookup_type, table_prefix, field_name, value):
    if table_prefix.endswith('.'):
        table_prefix = backend.quote_name(table_prefix[:-1])+'.'
    field_name = backend.quote_name(field_name)
    if type(value) == datetime.datetime and backend.get_datetime_cast_sql():
        cast_sql = backend.get_datetime_cast_sql()
    else:
        cast_sql = '%s'
    try:
        return '%s%s %s' % (table_prefix, field_name,
                            backend.OPERATOR_MAPPING[lookup_type] % cast_sql)
    except KeyError:
        pass
    if lookup_type == 'in':
        in_string = ','.join(['%s' for id in value])
        if in_string:
            if value:
                value_set = ','.join(['%s' for v in value])
            else:
                value_set = 'NULL'
            return '%s%s IN (%s)' % (table_prefix, field_name, value_set)
        else:
            raise EmptyResultSet
    elif lookup_type in ('range', 'year'):
        return '%s%s BETWEEN %%s AND %%s' % (table_prefix, field_name)
    elif lookup_type in ('month', 'day'):
        return "%s = %%s" % backend.get_date_extract_sql(lookup_type, table_prefix + field_name)
    elif lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))
    elif lookup_type == 'search':
        return backend.get_fulltext_search_sql(table_prefix + field_name)
    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def get_cached_row(klass, row, index_start, max_depth=0, cur_depth=0):
    """Helper function that recursively returns an object with cache filled"""

    # If we've got a max_depth set and we've exceeded that depth, bail now.
    if max_depth and cur_depth > max_depth:
        return None

    index_end = index_start + len(klass._meta.fields)
    obj = klass(*row[index_start:index_end])
    for f in klass._meta.fields:
        if f.rel and not f.null:
            cached_row = get_cached_row(f.rel.to, row, index_end, max_depth, cur_depth+1)
            if cached_row:
                rel_obj, index_end = cached_row
                setattr(obj, f.get_cache_name(), rel_obj)
    return obj, index_end

def fill_table_cache(opts, select, tables, where, old_prefix, cache_tables_seen, max_depth=0, cur_depth=0):
    """
    Helper function that recursively populates the select, tables and where (in
    place) for select_related queries.
    """

    # If we've got a max_depth set and we've exceeded that depth, bail now.
    if max_depth and cur_depth > max_depth:
        return None

    qn = backend.quote_name
    for f in opts.fields:
        if f.rel and not f.null:
            db_table = f.rel.to._meta.db_table
            if db_table not in cache_tables_seen:
                tables.append(qn(db_table))
            else: # The table was already seen, so give it a table alias.
                new_prefix = '%s%s' % (db_table, len(cache_tables_seen))
                tables.append('%s %s' % (qn(db_table), qn(new_prefix)))
                db_table = new_prefix
            cache_tables_seen.append(db_table)
            where.append('%s.%s = %s.%s' % \
                (qn(old_prefix), qn(f.column), qn(db_table), qn(f.rel.get_related_field().column)))
            select.extend(['%s.%s' % (backend.quote_name(db_table), backend.quote_name(f2.column)) for f2 in f.rel.to._meta.fields])
            fill_table_cache(f.rel.to._meta, select, tables, where, db_table, cache_tables_seen, max_depth, cur_depth+1)

def parse_lookup(kwarg_items, opts):
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
        elif len(path) == 0 or lookup_type not in QUERY_TERMS:
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

class FieldFound(Exception):
    "Exception used to short circuit field-finding operations."
    pass

def find_field(name, field_list, related_query):
    """
    Finds a field with a specific name in a list of field instances.
    Returns None if there are no matches, or several matches.
    """
    if related_query:
        matches = [f for f in field_list if f.field.related_query_name() == name]
    else:
        matches = [f for f in field_list if f.name == name]
    if len(matches) != 1:
        return None
    return matches[0]

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

        where.append(get_where_clause(lookup_type, current_table + '.', column, value))
        params.extend(field.get_db_prep_lookup(lookup_type, value))

    return joins, where, params

def delete_objects(seen_objs):
    "Iterate through a list of seen classes, and remove any instances that are referred to"
    qn = backend.quote_name
    ordered_classes = seen_objs.keys()
    ordered_classes.reverse()

    cursor = connection.cursor()

    for cls in ordered_classes:
        seen_objs[cls] = seen_objs[cls].items()
        seen_objs[cls].sort()

        # Pre notify all instances to be deleted
        for pk_val, instance in seen_objs[cls]:
            dispatcher.send(signal=signals.pre_delete, sender=cls, instance=instance)

        pk_list = [pk for pk,instance in seen_objs[cls]]
        for related in cls._meta.get_all_related_many_to_many_objects():
            if not isinstance(related.field, GenericRelation):
                for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                    cursor.execute("DELETE FROM %s WHERE %s IN (%s)" % \
                        (qn(related.field.m2m_db_table()),
                            qn(related.field.m2m_reverse_name()),
                            ','.join(['%s' for pk in pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE]])),
                        pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE])
        for f in cls._meta.many_to_many:
            if isinstance(f, GenericRelation):
                from django.contrib.contenttypes.models import ContentType
                query_extra = 'AND %s=%%s' % f.rel.to._meta.get_field(f.content_type_field_name).column
                args_extra = [ContentType.objects.get_for_model(cls).id]
            else:
                query_extra = ''
                args_extra = []
            for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                cursor.execute(("DELETE FROM %s WHERE %s IN (%s)" % \
                    (qn(f.m2m_db_table()), qn(f.m2m_column_name()),
                    ','.join(['%s' for pk in pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE]]))) + query_extra,
                    pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE] + args_extra)
        for field in cls._meta.fields:
            if field.rel and field.null and field.rel.to in seen_objs:
                for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                    cursor.execute("UPDATE %s SET %s=NULL WHERE %s IN (%s)" % \
                        (qn(cls._meta.db_table), qn(field.column), qn(cls._meta.pk.column),
                            ','.join(['%s' for pk in pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE]])),
                        pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE])

    # Now delete the actual data
    for cls in ordered_classes:
        seen_objs[cls].reverse()
        pk_list = [pk for pk,instance in seen_objs[cls]]
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            cursor.execute("DELETE FROM %s WHERE %s IN (%s)" % \
                (qn(cls._meta.db_table), qn(cls._meta.pk.column),
                ','.join(['%s' for pk in pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE]])),
                pk_list[offset:offset+GET_ITERATOR_CHUNK_SIZE])

        # Last cleanup; set NULLs where there once was a reference to the object,
        # NULL the primary key of the found objects, and perform post-notification.
        for pk_val, instance in seen_objs[cls]:
            for field in cls._meta.fields:
                if field.rel and field.null and field.rel.to in seen_objs:
                    setattr(instance, field.attname, None)

            setattr(instance, cls._meta.pk.attname, None)
            dispatcher.send(signal=signals.post_delete, sender=cls, instance=instance)

    transaction.commit_unless_managed()
