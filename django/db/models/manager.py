import copy

from django.db.models.query import QuerySet, EmptyQuerySet, insert_query
from django.db.models import signals
from django.db.models.fields import FieldDoesNotExist

def ensure_default_manager(sender, **kwargs):
    cls = sender
    if not getattr(cls, '_default_manager', None) and not cls._meta.abstract:
        # Create the default manager, if needed.
        try:
            cls._meta.get_field('objects')
            raise ValueError, "Model %s must specify a custom Manager, because it has a field named 'objects'" % cls.__name__
        except FieldDoesNotExist:
            pass
        cls.add_to_class('objects', Manager())

signals.class_prepared.connect(ensure_default_manager)

class Manager(object):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self):
        super(Manager, self).__init__()
        self._set_creation_counter()
        self.model = None
        self._inherited = False

    def contribute_to_class(self, model, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.model = model
        setattr(model, name, ManagerDescriptor(self))
        if not getattr(model, '_default_manager', None) or self.creation_counter < model._default_manager.creation_counter:
            model._default_manager = self
        if model._meta.abstract or self._inherited:
            model._meta.abstract_managers.append((self.creation_counter, name,
                    self))

    def _set_creation_counter(self):
        """
        Sets the creation counter value for this instance and increments the
        class-level copy.
        """
        self.creation_counter = Manager.creation_counter
        Manager.creation_counter += 1

    def _copy_to_model(self, model):
        """
        Makes a copy of the manager and assigns it to 'model', which should be
        a child of the existing model (used when inheriting a manager from an
        abstract base class).
        """
        assert issubclass(model, self.model)
        mgr = copy.copy(self)
        mgr._set_creation_counter()
        mgr.model = model
        mgr._inherited = True
        return mgr

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def get_empty_query_set(self):
        return EmptyQuerySet(self.model)

    def get_query_set(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        return QuerySet(self.model)

    def none(self):
        return self.get_empty_query_set()

    def all(self):
        return self.get_query_set()

    def count(self):
        return self.get_query_set().count()

    def dates(self, *args, **kwargs):
        return self.get_query_set().dates(*args, **kwargs)

    def distinct(self, *args, **kwargs):
        return self.get_query_set().distinct(*args, **kwargs)

    def extra(self, *args, **kwargs):
        return self.get_query_set().extra(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.get_query_set().get(*args, **kwargs)

    def get_or_create(self, **kwargs):
        return self.get_query_set().get_or_create(**kwargs)

    def create(self, **kwargs):
        return self.get_query_set().create(**kwargs)

    def filter(self, *args, **kwargs):
        return self.get_query_set().filter(*args, **kwargs)

    def complex_filter(self, *args, **kwargs):
        return self.get_query_set().complex_filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        return self.get_query_set().exclude(*args, **kwargs)

    def in_bulk(self, *args, **kwargs):
        return self.get_query_set().in_bulk(*args, **kwargs)

    def iterator(self, *args, **kwargs):
        return self.get_query_set().iterator(*args, **kwargs)

    def latest(self, *args, **kwargs):
        return self.get_query_set().latest(*args, **kwargs)

    def order_by(self, *args, **kwargs):
        return self.get_query_set().order_by(*args, **kwargs)

    def select_related(self, *args, **kwargs):
        return self.get_query_set().select_related(*args, **kwargs)

    def values(self, *args, **kwargs):
        return self.get_query_set().values(*args, **kwargs)

    def values_list(self, *args, **kwargs):
        return self.get_query_set().values_list(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self.get_query_set().update(*args, **kwargs)

    def reverse(self, *args, **kwargs):
        return self.get_query_set().reverse(*args, **kwargs)

    def _insert(self, values, **kwargs):
        return insert_query(self.model, values, **kwargs)

    def _update(self, values, **kwargs):
        return self.get_query_set()._update(values, **kwargs)

class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError, "Manager isn't accessible via %s instances" % type.__name__
        return self.manager

class EmptyManager(Manager):
    def get_query_set(self):
        return self.get_empty_query_set()
