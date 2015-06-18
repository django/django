import copy
import inspect
from importlib import import_module

from django.db import router
from django.db.models.query import QuerySet
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


def ensure_default_manager(cls):
    """
    Ensures that a Model subclass contains a default manager  and sets the
    _default_manager attribute on the class. Also sets up the _base_manager
    points to a plain Manager instance (which could be the same as
    _default_manager if it's not a subclass of Manager).
    """
    if cls._meta.abstract:
        setattr(cls, 'objects', AbstractManagerDescriptor(cls))
        return
    elif cls._meta.swapped:
        setattr(cls, 'objects', SwappedManagerDescriptor(cls))
        return
    if not getattr(cls, '_default_manager', None):
        if any(f.name == 'objects' for f in cls._meta.fields):
            raise ValueError(
                "Model %s must specify a custom Manager, because it has a "
                "field named 'objects'" % cls.__name__
            )
        # Create the default manager, if needed.
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
            raise AssertionError(
                "Should never get here. Please report a bug, including your "
                "model and model manager setup."
            )


@python_2_unicode_compatible
class BaseManager(object):
    # Tracks each time a Manager instance is created. Used to retain order.
    creation_counter = 0

    #: If set to True the manager will be serialized into migrations and will
    #: thus be available in e.g. RunPython operations
    use_in_migrations = False

    def __new__(cls, *args, **kwargs):
        # We capture the arguments to make returning them trivial
        obj = super(BaseManager, cls).__new__(cls)
        obj._constructor_args = (args, kwargs)
        return obj

    def __init__(self):
        super(BaseManager, self).__init__()
        self._set_creation_counter()
        self.model = None
        self.name = None
        self._inherited = False
        self._db = None
        self._hints = {}

    def __str__(self):
        """ Return "app_label.model_label.manager_name". """
        model = self.model
        app = model._meta.app_label
        return '%s.%s.%s' % (app, model._meta.object_name, self.name)

    def deconstruct(self):
        """
        Returns a 5-tuple of the form (as_manager (True), manager_class,
        queryset_class, args, kwargs).

        Raises a ValueError if the manager is dynamically generated.
        """
        qs_class = self._queryset_class
        if getattr(self, '_built_with_as_manager', False):
            # using MyQuerySet.as_manager()
            return (
                True,  # as_manager
                None,  # manager_class
                '%s.%s' % (qs_class.__module__, qs_class.__name__),  # qs_class
                None,  # args
                None,  # kwargs
            )
        else:
            module_name = self.__module__
            name = self.__class__.__name__
            # Make sure it's actually there and not an inner class
            module = import_module(module_name)
            if not hasattr(module, name):
                raise ValueError(
                    "Could not find manager %s in %s.\n"
                    "Please note that you need to inherit from managers you "
                    "dynamically generated with 'from_queryset()'."
                    % (name, module_name)
                )
            return (
                False,  # as_manager
                '%s.%s' % (module_name, name),  # manager_class
                None,  # qs_class
                self._constructor_args[0],  # args
                self._constructor_args[1],  # kwargs
            )

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
        if not self.name:
            self.name = name
        # Only contribute the manager if the model is concrete
        if model._meta.abstract:
            setattr(model, name, AbstractManagerDescriptor(model))
        elif model._meta.swapped:
            setattr(model, name, SwappedManagerDescriptor(model))
        else:
            # if not model._meta.abstract and not model._meta.swapped:
            setattr(model, name, ManagerDescriptor(self))
        if (not getattr(model, '_default_manager', None) or
                self.creation_counter < model._default_manager.creation_counter):
            model._default_manager = self

        abstract = False
        if model._meta.abstract or (self._inherited and not self.model._meta.proxy):
            abstract = True
        model._meta.managers.append((self.creation_counter, self, abstract))

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

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self._constructor_args == other._constructor_args
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return id(self)


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
