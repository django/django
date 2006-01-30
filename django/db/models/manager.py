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

    def contribute_to_class(self, klass, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.klass = klass
        dispatcher.connect(self._prepare, signal=signals.class_prepared, sender=klass)
        setattr(klass, name, ManagerDescriptor(self))
        if not hasattr(klass, '_default_manager') or self.creation_counter < klass._default_manager.creation_counter:
            klass._default_manager = self

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

class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError, "Manager isn't accessible via %s instances" % type.__name__
        return self.manager
