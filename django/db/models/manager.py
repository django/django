import copy
import inspect

from django.db import router
from django.db.models.query import QuerySet
from django.db.models import signals
from django.db.models.fields import FieldDoesNotExist
from django.utils import six
from django.utils.deprecation import RenameMethodsBase, RemovedInDjango18Warning
from django.utils.encoding import python_2_unicode_compatible


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
        ('get_query_set', 'get_queryset', RemovedInDjango18Warning),
        ('get_prefetch_query_set', 'get_prefetch_queryset', RemovedInDjango18Warning),
    )


@python_2_unicode_compatible
class BaseManager(six.with_metaclass(RenameManagerMethods)):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self):
        super(BaseManager, self).__init__()
        self._set_creation_counter()
        self.model = None
        self._inherited = False
        self._db = None
        self._hints = {}

    def __str__(self):
        """ Return "app_label.model_label.manager_name". """
        model = self.model
        opts = model._meta
        app = model._meta.app_label
        manager_name = next(name for (_, name, manager)
            in opts.concrete_managers + opts.abstract_managers
            if manager == self)
        return '%s.%s.%s' % (app, model._meta.object_name, manager_name)

    def check(self, **kwargs):
        return []

    @classmethod
    def _get_queryset_methods(cls, queryset_class):
        def create_method(name, method):
            def manager_method(self, *args, **kwargs):
                return getattr(self.get_queryset(), name)(*args, **kwargs)
            manager_method.__name__ = method.__name__
            manager_method.__doc__ = method.__doc__
            return manager_method

        new_methods = {}
        # Refs http://bugs.python.org/issue1785.
        predicate = inspect.isfunction if six.PY3 else inspect.ismethod
        for name, method in inspect.getmembers(queryset_class, predicate=predicate):
            # Only copy missing methods.
            if hasattr(cls, name):
                continue
            # Only copy public methods or methods with the attribute `queryset_only=False`.
            queryset_only = getattr(method, 'queryset_only', None)
            if queryset_only or (queryset_only is None and name.startswith('_')):
                continue
            # Copy the method onto the manager.
            new_methods[name] = create_method(name, method)
        return new_methods

    @classmethod
    def from_queryset(cls, queryset_class, class_name=None):
        if class_name is None:
            class_name = '%sFrom%s' % (cls.__name__, queryset_class.__name__)
        class_dict = {
            '_queryset_class': queryset_class,
        }
        class_dict.update(cls._get_queryset_methods(queryset_class))
        return type(class_name, (cls,), class_dict)

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
        self.creation_counter = BaseManager.creation_counter
        BaseManager.creation_counter += 1

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

    def db_manager(self, using=None, hints=None):
        obj = copy.copy(self)
        obj._db = using or self._db
        obj._hints = hints or self._hints
        return obj

    @property
    def db(self):
        return self._db or router.db_for_read(self.model, **self._hints)

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def get_queryset(self):
        """
        Returns a new QuerySet object.  Subclasses can override this method to
        easily customize the behavior of the Manager.
        """
        return self._queryset_class(self.model, using=self._db, hints=self._hints)

    def all(self):
        # We can't proxy this method through the `QuerySet` like we do for the
        # rest of the `QuerySet` methods. This is because `QuerySet.all()`
        # works by creating a "copy" of the current queryset and in making said
        # copy, all the cached `prefetch_related` lookups are lost. See the
        # implementation of `RelatedManager.get_queryset()` for a better
        # understanding of how this comes into play.
        return self.get_queryset()


class Manager(BaseManager.from_queryset(QuerySet)):
    pass


class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
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
