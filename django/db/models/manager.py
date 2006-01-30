from django.db.models.fields import DateField
from django.utils.functional import curry
from django.db import backend, connection
from django.db.models.query import QuerySet
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
        cls.add_to_class('objects', Manager())
        cls.objects._prepare()

dispatcher.connect(ensure_default_manager, signal=signals.class_prepared)

# class OldSubmittedManager(QuerySet):
#     def in_bulk(self, id_list, **kwargs):
#         assert isinstance(id_list, list), "in_bulk() must be provided with a list of IDs."
#         assert id_list != [], "in_bulk() cannot be passed an empty ID list."
#         new_query = self    # we have to do a copy later, so this is OK
#         if kwargs:
#             new_query = self.filter(**kwargs)
#         new_query = new_query.extras(where=
#                                       ["%s.%s IN (%s)" % (backend.quote_name(self.klass._meta.db_table),
#                                                           backend.quote_name(self.klass._meta.pk.column),
#                                                           ",".join(['%s'] * len(id_list)))],
#                                      params=id_list)
#         obj_list = list(new_query)
#         return dict([(obj._get_pk_val(), obj) for obj in obj_list])
#
#     def delete(self, **kwargs):
#         # Remove the DELETE_ALL argument, if it exists.
#         delete_all = kwargs.pop('DELETE_ALL', False)
#
#         # Check for at least one query argument.
#         if not kwargs and not delete_all:
#             raise TypeError, "SAFETY MECHANISM: Specify DELETE_ALL=True if you actually want to delete all data."
#
#         if kwargs:
#             del_query = self.filter(**kwargs)
#         else:
#             del_query = self._clone()
#         # disable non-supported fields
#         del_query._select_related = False
#         del_query._select = {}
#         del_query._order_by = []
#         del_query._offset = None
#         del_query._limit = None
#
#         opts = self.klass._meta
#
#         # Perform the SQL delete
#         cursor = connection.cursor()
#         _, sql, params = del_query._get_sql_clause(False)
#         cursor.execute("DELETE " + sql, params)

class Manager(QuerySet):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self):
        super(Manager, self).__init__()
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
        setattr(klass, name, ManagerDescriptor(self))
        if not hasattr(klass, '_default_manager') or self.creation_counter < klass._default_manager.creation_counter:
            klass._default_manager = self

    def delete(self, *args, **kwargs):
        num_args = len(args) + len(kwargs)

        # Remove the DELETE_ALL argument, if it exists.
        delete_all = kwargs.pop('DELETE_ALL', False)

        # Check for at least one query argument.
        if num_args == 0 and not delete_all:
            raise TypeError, "SAFETY MECHANISM: Specify DELETE_ALL=True if you actually want to delete all data."

        # disable non-supported fields
        kwargs['select_related'] = False
        kwargs['select'] = {}
        kwargs['order_by'] = []
        kwargs['offset'] = None
        kwargs['limit'] = None

        opts = self.klass._meta

        # Perform the SQL delete
        cursor = connection.cursor()
        _, sql, params = self._get_sql_clause(False, *args, **kwargs)
        cursor.execute("DELETE " + sql, params)

    def in_bulk(self, id_list, *args, **kwargs):
        assert isinstance(id_list, list), "get_in_bulk() must be provided with a list of IDs."
        assert id_list != [], "get_in_bulk() cannot be passed an empty ID list."
        kwargs['where'] = ["%s.%s IN (%s)" % (backend.quote_name(self.klass._meta.db_table), backend.quote_name(self.klass._meta.pk.column), ",".join(['%s'] * len(id_list)))]
        kwargs['params'] = id_list
        obj_list = self.get_list(*args, **kwargs)
        return dict([(obj._get_pk_val(), obj) for obj in obj_list])

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
        _, sql, params = self._get_sql_clause(True, *args, **kwargs)
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
        select, sql, params = self._get_sql_clause(True, *args, **kwargs)
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
