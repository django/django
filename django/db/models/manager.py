from django.db.models.fields import DateField
from django.utils.functional import curry
from django.db import backend, connection
from django.db.models.query import Q, parse_lookup, fill_table_cache, get_cached_row
from django.db.models.query import handle_legacy_orderlist, orderlist2sql, orderfield2column
from django.dispatch import dispatcher
from django.db.models import signals
from django.utils.datastructures import SortedDict

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

def ensure_default_manager(sender):
    cls = sender
    if not hasattr(cls, '_default_manager'):
        # Create the default manager, if needed.
        if hasattr(cls, 'objects'):
            raise ValueError, "Model %s must specify a custom Manager, because it has a field named 'objects'" % name
        cls.add_to_class('objects',  Manager())
        cls.objects._prepare()

dispatcher.connect(ensure_default_manager, signal=signals.class_prepared)

class Manager(object):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self):
        # Increase the creation counter, and save our local copy.
        self.creation_counter = Manager.creation_counter
        Manager.creation_counter += 1
        self.klass = None

    def _prepare(self):
        if self.klass._meta.get_latest_by:
            self.get_latest = self.__get_latest
        for f in self.klass._meta.fields:
            if isinstance(f, DateField):
                setattr(self, 'get_%s_list' % f.name, curry(self.__get_date_list, f))

    def contribute_to_class(self, klass, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.klass = klass
        dispatcher.connect(self._prepare, signal=signals.class_prepared, sender=klass)
        setattr(klass,name, ManagerDescriptor(self))
        if not hasattr(klass, '_default_manager') or \
           self.creation_counter < klass._default_manager.creation_counter:
                klass._default_manager = self

    def _get_sql_clause(self, *args, **kwargs):
        def quote_only_if_word(word):
            if ' ' in word:
                return word
            else:
                return backend.quote_name(word)

        opts = self.klass._meta

        # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
        select = ["%s.%s" % (backend.quote_name(opts.db_table), backend.quote_name(f.column)) for f in opts.fields]
        tables = (kwargs.get('tables') and [quote_only_if_word(t) for t in kwargs['tables']] or [])
        joins = SortedDict()
        where = kwargs.get('where') and kwargs['where'][:] or []
        params = kwargs.get('params') and kwargs['params'][:] or []

        # Convert all the args into SQL.
        table_count = 0
        for arg in args:
            # check that the provided argument is a Query (i.e., it has a get_sql method)
            if not hasattr(arg, 'get_sql'):
                raise TypeError, "'%s' is not a valid query argument" % str(arg)

            tables2, joins2, where2, params2 = arg.get_sql(opts)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)


        # Convert the kwargs into SQL.
        tables2, joins2, where2, params2 = parse_lookup(kwargs.items(), opts)
        tables.extend(tables2)
        joins.update(joins2)
        where.extend(where2)
        params.extend(params2)

        # Add any additional constraints from the "where_constraints" parameter.
        where.extend(opts.where_constraints)

        # Add additional tables and WHERE clauses based on select_related.
        if kwargs.get('select_related') is True:
            fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])

        # Add any additional SELECTs passed in via kwargs.
        if kwargs.get('select'):
            select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in kwargs['select']])

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
        for f in handle_legacy_orderlist(kwargs.get('order_by', opts.ordering)):
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
                    if "." not in col_name and col_name not in [k[0] for k in kwargs.get('select', [])]:
                        table_prefix = backend.quote_name(opts.db_table) + '.'
                    else:
                        table_prefix = ''
                order_by.append('%s%s %s' % (table_prefix, backend.quote_name(orderfield2column(col_name, opts)), order))
        if order_by:
            sql.append("ORDER BY " + ", ".join(order_by))

        # LIMIT and OFFSET clauses
        if kwargs.get('limit') is not None:
            sql.append("%s " % backend.get_limit_offset_sql(kwargs['limit'], kwargs.get('offset')))
        else:
            assert kwargs.get('offset') is None, "'offset' is not allowed without 'limit'"

        return select, " ".join(sql), params

    def get_iterator(self, *args, **kwargs):
        # kwargs['select'] is a dictionary, and dictionaries' key order is
        # undefined, so we convert it to a list of tuples internally.
        kwargs['select'] = kwargs.get('select', {}).items()

        cursor = connection.cursor()
        select, sql, params = self._get_sql_clause(*args, **kwargs)
        cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
        fill_cache = kwargs.get('select_related')
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
                for i, k in enumerate(kwargs['select']):
                    setattr(obj, k[0], row[index_end+i])
                yield obj

    def get_list(self, *args, **kwargs):
        return list(self.get_iterator(*args, **kwargs))

    def get_count(self, *args, **kwargs):
        kwargs['order_by'] = []
        kwargs['offset'] = None
        kwargs['limit'] = None
        kwargs['select_related'] = False
        _, sql, params = self._get_sql_clause(*args, **kwargs)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*)" + sql, params)
        return cursor.fetchone()[0]

    def get_object(self, *args, **kwargs):
        obj_list = self.get_list(*args, **kwargs)
        if len(obj_list) < 1:
            raise self.klass.DoesNotExist, "%s does not exist for %s" % (self.klass._meta.object_name, kwargs)
        assert len(obj_list) == 1, "get_object() returned more than one %s -- it returned %s! Lookup parameters were %s" % (self.klass._meta.object_name, len(obj_list), kwargs)
        return obj_list[0]

    def get_in_bulk(self, id_list, *args, **kwargs):
        assert isinstance(id_list, list), "get_in_bulk() must be provided with a list of IDs."
        assert id_list != [], "get_in_bulk() cannot be passed an empty ID list."
        kwargs['where'] = ["%s.%s IN (%s)" % (backend.quote_name(self.klass._meta.db_table), backend.quote_name(self.klass._meta.pk.column), ",".join(['%s'] * len(id_list)))]
        kwargs['params'] = id_list
        obj_list = self.get_list(*args, **kwargs)
        return dict([(getattr(o, self.klass._meta.pk.attname), o) for o in obj_list])

    def get_values_iterator(self, *args, **kwargs):
        # select_related and select aren't supported in get_values().
        kwargs['select_related'] = False
        kwargs['select'] = {}

        # 'fields' is a list of field names to fetch.
        try:
            fields = [self.klass._meta.get_field(f).column for f in kwargs.pop('fields')]
        except KeyError: # Default to all fields.
            fields = [f.column for f in self.klass._meta.fields]

        cursor = connection.cursor()
        _, sql, params = self._get_sql_clause(*args, **kwargs)
        select = ['%s.%s' % (backend.quote_name(self.klass._meta.db_table), backend.quote_name(f)) for f in fields]
        cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
        while 1:
            rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
            if not rows:
                raise StopIteration
            for row in rows:
                yield dict(zip(fields, row))

    def get_values(self, *args, **kwargs):
        return list(self.get_values_iterator(*args, **kwargs))

    def __get_latest(self, *args, **kwargs):
        kwargs['order_by'] = ('-' + self.klass._meta.get_latest_by,)
        kwargs['limit'] = 1
        return self.get_object(*args, **kwargs)

    def __get_date_list(self, field, kind, *args, **kwargs):
        from django.db.backends.util import typecast_timestamp
        assert kind in ("month", "year", "day"), "'kind' must be one of 'year', 'month' or 'day'."
        order = 'ASC'
        if kwargs.has_key('order'):
            order = kwargs['order']
            del kwargs['order']
        assert order in ('ASC', 'DESC'), "'order' must be either 'ASC' or 'DESC'"
        kwargs['order_by'] = () # Clear this because it'll mess things up otherwise.
        if field.null:
            kwargs.setdefault('where', []).append('%s.%s IS NOT NULL' % \
                (backend.quote_name(self.klass._meta.db_table), backend.quote_name(field.column)))
        select, sql, params = self._get_sql_clause(*args, **kwargs)
        sql = 'SELECT %s %s GROUP BY 1 ORDER BY 1 %s' % \
            (backend.get_date_trunc_sql(kind, '%s.%s' % (backend.quote_name(self.klass._meta.db_table),
            backend.quote_name(field.column))), sql, order)
        cursor = connection.cursor()
        cursor.execute(sql, params)
        # We have to manually run typecast_timestamp(str()) on the results, because
        # MySQL doesn't automatically cast the result of date functions as datetime
        # objects -- MySQL returns the values as strings, instead.
        return [typecast_timestamp(str(row[0])) for row in cursor.fetchall()]

class ManagerDescriptor(object):
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError, "Manager isn't accessible via %s instances" % type.__name__
        return self.manager
