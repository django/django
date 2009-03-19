"""
Various data structures used in query construction.

Factored out from django.db.models.query to avoid making the main module very
large and/or so that they can be used by other modules without getting into
circular import difficulties.
"""

import weakref
from copy import deepcopy

from django.utils import tree
from django.utils.datastructures import SortedDict

try:
    sorted
except NameError:
    from django.utils.itercompat import sorted  # For Python 2.3.


class CyclicDependency(Exception):
    """
    An error when dealing with a collection of objects that have a cyclic
    dependency, i.e. when deleting multiple objects.
    """
    pass

class CollectedObjects(object):
    """
    A container that stores keys and lists of values along with remembering the
    parent objects for all the keys.

    This is used for the database object deletion routines so that we can
    calculate the 'leaf' objects which should be deleted first.
    """

    def __init__(self):
        self.data = {}
        self.children = {}

    def add(self, model, pk, obj, parent_model, nullable=False):
        """
        Adds an item to the container.

        Arguments:
        * model - the class of the object being added.
        * pk - the primary key.
        * obj - the object itself.
        * parent_model - the model of the parent object that this object was
          reached through.
        * nullable - should be True if this relation is nullable.

        Returns True if the item already existed in the structure and
        False otherwise.
        """
        d = self.data.setdefault(model, SortedDict())
        retval = pk in d
        d[pk] = obj
        # Nullable relationships can be ignored -- they are nulled out before
        # deleting, and therefore do not affect the order in which objects
        # have to be deleted.
        if parent_model is not None and not nullable:
            self.children.setdefault(parent_model, []).append(model)
        return retval

    def __contains__(self, key):
        return self.data.__contains__(key)

    def __getitem__(self, key):
        return self.data[key]

    def __nonzero__(self):
        return bool(self.data)

    def iteritems(self):
        for k in self.ordered_keys():
            yield k, self[k]

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return self.ordered_keys()

    def ordered_keys(self):
        """
        Returns the models in the order that they should be dealt with (i.e.
        models with no dependencies first).
        """
        dealt_with = SortedDict()
        # Start with items that have no children
        models = self.data.keys()
        while len(dealt_with) < len(models):
            found = False
            for model in models:
                if model in dealt_with:
                    continue
                children = self.children.setdefault(model, [])
                if len([c for c in children if c not in dealt_with]) == 0:
                    dealt_with[model] = None
                    found = True
            if not found:
                raise CyclicDependency(
                    "There is a cyclic dependency of items to be processed.")

        return dealt_with.keys()

    def unordered_keys(self):
        """
        Fallback for the case where is a cyclic dependency but we don't  care.
        """
        return self.data.keys()

class QueryWrapper(object):
    """
    A type that indicates the contents are an SQL fragment and the associate
    parameters. Can be used to pass opaque data to a where-clause, for example.
    """
    def __init__(self, sql, params):
        self.data = sql, params

    def as_sql(self, qn=None):
        return self.data

class Q(tree.Node):
    """
    Encapsulates filters as objects that can then be combined logically (using
    & and |).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, **kwargs):
        super(Q, self).__init__(children=list(args) + kwargs.items())

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise TypeError(other)
        obj = deepcopy(self)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = deepcopy(self)
        obj.negate()
        return obj

class DeferredAttribute(object):
    """
    A wrapper for a deferred-loading field. When the value is read from this
    object the first time, the query is executed.
    """
    def __init__(self, field_name, pk_value, model):
        self.field_name = field_name
        self.pk_value = pk_value
        self.model_ref = weakref.ref(model)
        self.loaded = False

    def __get__(self, instance, owner):
        """
        Retrieves and caches the value from the datastore on the first lookup.
        Returns the cached value.
        """
        assert instance is not None
        if not self.loaded:
            obj = self.model_ref()
            if obj is None:
                return
            self.value = list(obj._base_manager.filter(pk=self.pk_value).values_list(self.field_name, flat=True))[0]
            self.loaded = True
        return self.value

    def __set__(self, name, value):
        """
        Deferred loading attributes can be set normally (which means there will
        never be a database lookup involved.
        """
        self.value = value
        self.loaded = True

def select_related_descend(field, restricted, requested):
    """
    Returns True if this field should be used to descend deeper for
    select_related() purposes. Used by both the query construction code
    (sql.query.fill_related_selections()) and the model instance creation code
    (query.get_cached_row()).
    """
    if not field.rel:
        return False
    if field.rel.parent_link:
        return False
    if restricted and field.name not in requested:
        return False
    if not restricted and field.null:
        return False
    return True

# This function is needed because data descriptors must be defined on a class
# object, not an instance, to have any effect.

def deferred_class_factory(model, pk_value, attrs):
    """
    Returns a class object that is a copy of "model" with the specified "attrs"
    being replaced with DeferredAttribute objects. The "pk_value" ties the
    deferred attributes to a particular instance of the model.
    """
    class Meta:
        pass
    setattr(Meta, "proxy", True)
    setattr(Meta, "app_label", model._meta.app_label)

    # The app_cache wants a unique name for each model, otherwise the new class
    # won't be created (we get an old one back). Therefore, we generate the
    # name using the passed in attrs. It's OK to reuse an old case if the attrs
    # are identical.
    name = "%s_Deferred_%s" % (model.__name__, '_'.join(sorted(list(attrs))))

    overrides = dict([(attr, DeferredAttribute(attr, pk_value, model))
            for attr in attrs])
    overrides["Meta"] = Meta
    overrides["__module__"] = model.__module__
    overrides["_deferred"] = True
    return type(name, (model,), overrides)

# The above function is also used to unpickle model instances with deferred
# fields.
deferred_class_factory.__safe_for_unpickling__ = True

