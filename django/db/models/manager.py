import copy
from django.db import router
from django.db.models.query import QuerySet, insert_query, RawQuerySet
from django.db.models import signals
from django.db.models.fields import FieldDoesNotExist
from django.utils import six
from django.utils.deprecation import RenameMethodsBase

def ensure_default_manager(sender, **kwargs):
    """
    Ensures that a Model subclass contains a default manager  and sets the
    _default_manager attribute on the class. Also sets up the _base_manager
    points to a plain Manager instance (which could be the same as
    _default_manager if it's not a subclass of Manager).
    """
    cls = sender
    if cls._meta.abstract:
        setattr(cls, 'objects', AbstractManagerDescriptor(cls))
        return
    elif cls._meta.swapped:
        setattr(cls, 'objects', SwappedManagerDescriptor(cls))
        return
    if not getattr(cls, '_default_manager', None):
        # Create the default manager, if needed.
        try:
            cls._meta.get_field('objects')
            raise ValueError("Model %s must specify a custom Manager, because it has a field named 'objects'" % cls.__name__)
        except FieldDoesNotExist:
            pass
        cls.add_to_class('objects', Manager())
        cls._base_manager = cls.objects
    elif not getattr(cls, '_base_manager', None):
        default_mgr = cls._default_manager.__class__
        if (default_mgr is Manager or
                getattr(default_mgr, "use_for_related_fields", False)):
            cls._base_manager = cls._default_manager
        else:
            # Default manager isn't a plain Manager class, or a suitable
            # replacement, so we walk up the base class hierarchy until we hit
            # something appropriate.
            for base_class in default_mgr.mro()[1:]:
                if (base_class is Manager or
                        getattr(base_class, "use_for_related_fields", False)):
                    cls.add_to_class('_base_manager', base_class())
                    return
            raise AssertionError("Should never get here. Please report a bug, including your model and model manager setup.")

signals.class_prepared.connect(ensure_default_manager)


class RenameManagerMethods(RenameMethodsBase):
    renamed_methods = (
        ('get_query_set', 'get_queryset', PendingDeprecationWarning),
        ('get_prefetch_query_set', 'get_prefetch_queryset', PendingDeprecationWarning),
    )


class Manager(six.with_metaclass(RenameManagerMethods)):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self):
        super(Manager, self).__init__()
        self._set_creation_counter()
        self.model = None
        self._inherited = False
        self._db = None

    def contribute_to_class(self, model, name):
        # TODO: Use weakref because of possible memory leak / circular reference.
        self.model = model
        # Only contribute the manager if the model is concrete
        if model._meta.abstract:
            setattr(model, name, AbstractManagerDescriptor(model))
        elif model._meta.swapped:
            setattr(model, name, SwappedManagerDescriptor(model))
        else:
        # if not model._meta.abstract and not model._meta.swapped:
            setattr(model, name, ManagerDescriptor(self))
        if not getattr(model, '_default_manager', None) or self.creation_counter < model._default_manager.creation_counter:
            model._default_manager = self
        if model._meta.abstract or (self._inherited and not self.model._meta.proxy):
            model._meta.abstract_managers.append((self.creation_counter, name,
                    self))
        else:
            model._meta.concrete_managers.append((self.creation_counter, name,
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

    def db_manager(self, using):
        obj = copy.copy(self)
        obj._db = using
        return obj

    @property
    def db(self):
        return self._db or router.db_for_read(self.model)

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def get_queryset(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        return QuerySet(self.model, using=self._db)

    def none(self):
        return self.get_queryset().none()

    def all(self):
        return self.get_queryset()

    def count(self):
        return self.get_queryset().count()

    def dates(self, *args, **kwargs):
        return self.get_queryset().dates(*args, **kwargs)

    def datetimes(self, *args, **kwargs):
        return self.get_queryset().datetimes(*args, **kwargs)

    def distinct(self, *args, **kwargs):
        return self.get_queryset().distinct(*args, **kwargs)

    def extra(self, *args, **kwargs):
        return self.get_queryset().extra(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.get_queryset().get(*args, **kwargs)

    def get_or_create(self, **kwargs):
        return self.get_queryset().get_or_create(**kwargs)

    def create(self, **kwargs):
        return self.get_queryset().create(**kwargs)

    def bulk_create(self, *args, **kwargs):
        return self.get_queryset().bulk_create(*args, **kwargs)

    def filter(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        return self.get_queryset().aggregate(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        return self.get_queryset().annotate(*args, **kwargs)

    def complex_filter(self, *args, **kwargs):
        return self.get_queryset().complex_filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        return self.get_queryset().exclude(*args, **kwargs)

    def in_bulk(self, *args, **kwargs):
        return self.get_queryset().in_bulk(*args, **kwargs)

    def iterator(self, *args, **kwargs):
        return self.get_queryset().iterator(*args, **kwargs)

    def earliest(self, *args, **kwargs):
        return self.get_queryset().earliest(*args, **kwargs)

    def latest(self, *args, **kwargs):
        return self.get_queryset().latest(*args, **kwargs)

    def first(self):
        return self.get_queryset().first()

    def last(self):
        return self.get_queryset().last()

    def order_by(self, *args, **kwargs):
        return self.get_queryset().order_by(*args, **kwargs)

    def select_for_update(self, *args, **kwargs):
        return self.get_queryset().select_for_update(*args, **kwargs)

    def select_related(self, *args, **kwargs):
        return self.get_queryset().select_related(*args, **kwargs)

    def prefetch_related(self, *args, **kwargs):
        return self.get_queryset().prefetch_related(*args, **kwargs)

    def values(self, *args, **kwargs):
        return self.get_queryset().values(*args, **kwargs)

    def values_list(self, *args, **kwargs):
        return self.get_queryset().values_list(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self.get_queryset().update(*args, **kwargs)

    def reverse(self, *args, **kwargs):
        return self.get_queryset().reverse(*args, **kwargs)

    def defer(self, *args, **kwargs):
        return self.get_queryset().defer(*args, **kwargs)

    def only(self, *args, **kwargs):
        return self.get_queryset().only(*args, **kwargs)

    def using(self, *args, **kwargs):
        return self.get_queryset().using(*args, **kwargs)

    def exists(self, *args, **kwargs):
        return self.get_queryset().exists(*args, **kwargs)

    def _insert(self, objs, fields, **kwargs):
        return insert_query(self.model, objs, fields, **kwargs)

    def _update(self, values, **kwargs):
        return self.get_queryset()._update(values, **kwargs)

    def raw(self, raw_query, params=None, *args, **kwargs):
        return RawQuerySet(raw_query=raw_query, model=self.model, params=params, using=self._db, *args, **kwargs)


class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError("Manager isn't accessible via %s instances" % type.__name__)
        return self.manager


class AbstractManagerDescriptor(object):
    # This class provides a better error message when you try to access a
    # manager on an abstract model.
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, type=None):
        raise AttributeError("Manager isn't available; %s is abstract" % (
            self.model._meta.object_name,
        ))


class SwappedManagerDescriptor(object):
    # This class provides a better error message when you try to access a
    # manager on a swapped model.
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, type=None):
        raise AttributeError("Manager isn't available; %s has been swapped for '%s'" % (
            self.model._meta.object_name, self.model._meta.swapped
        ))


class EmptyManager(Manager):
    def __init__(self, model):
        super(EmptyManager, self).__init__()
        self.model = model

    def get_queryset(self):
        return super(EmptyManager, self).get_queryset().none()
