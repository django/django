"""
Various data structures used in query construction.

Factored out from django.db.models.query to avoid making the main module very
large and/or so that they can be used by other modules without getting into
circular import difficulties.
"""
import copy
import functools
import inspect
from collections import namedtuple

from django.db.models.constants import LOOKUP_SEP
from django.utils import tree

# PathInfo is used when converting lookups (fk__somecol). The contents
# describe the relation in Model terms (model Options and Fields for both
# sides of the relation. The join_field is the field backing the relation.
PathInfo = namedtuple('PathInfo', 'from_opts to_opts target_fields join_field m2m direct')


class InvalidQuery(Exception):
    """The query passed to raw() isn't a safe query to use with raw()."""
    pass


def subclasses(cls):
    yield cls
    for subclass in cls.__subclasses__():
        yield from subclasses(subclass)


class QueryWrapper:
    """
    A type that indicates the contents are an SQL fragment and the associate
    parameters. Can be used to pass opaque data to a where-clause, for example.
    """
    contains_aggregate = False

    def __init__(self, sql, params):
        self.data = sql, list(params)

    def as_sql(self, compiler=None, connection=None):
        return self.data


class Q(tree.Node):
    """
    Encapsulate filters as objects that can then be combined logically (using
    `&` and `|`).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, **kwargs):
        connector = kwargs.pop('_connector', None)
        negated = kwargs.pop('_negated', False)
        super().__init__(children=list(args) + list(kwargs.items()), connector=connector, negated=negated)

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise TypeError(other)

        # If the other Q() is empty, ignore it and just use `self`.
        if not other:
            return copy.deepcopy(self)
        # Or if this Q is empty, ignore it and just use `other`.
        elif not self:
            return copy.deepcopy(other)

        obj = type(self)()
        obj.connector = conn
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = type(self)()
        obj.add(self, self.AND)
        obj.negate()
        return obj

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # We must promote any new joins to left outer joins so that when Q is
        # used as an expression, rows aren't filtered due to joins.
        clause, joins = query._add_q(self, reuse, allow_joins=allow_joins, split_subq=False)
        query.promote_joins(joins)
        return clause

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        args, kwargs = (), {}
        if len(self.children) == 1 and not isinstance(self.children[0], Q):
            child = self.children[0]
            kwargs = {child[0]: child[1]}
        else:
            args = tuple(self.children)
            kwargs = {'_connector': self.connector}
        if self.negated:
            kwargs['_negated'] = True
        return path, args, kwargs


class DeferredAttribute:
    """
    A wrapper for a deferred-loading field. When the value is read from this
    object the first time, the query is executed.
    """
    def __init__(self, field_name, model):
        self.field_name = field_name

    def __get__(self, instance, cls=None):
        """
        Retrieve and caches the value from the datastore on the first lookup.
        Return the cached value.
        """
        if instance is None:
            return self
        data = instance.__dict__
        if data.get(self.field_name, self) is self:
            # Let's see if the field is part of the parent chain. If so we
            # might be able to reuse the already loaded value. Refs #18343.
            val = self._check_parent_chain(instance, self.field_name)
            if val is None:
                instance.refresh_from_db(fields=[self.field_name])
                val = getattr(instance, self.field_name)
            data[self.field_name] = val
        return data[self.field_name]

    def _check_parent_chain(self, instance, name):
        """
        Check if the field value can be fetched from a parent field already
        loaded in the instance. This can be done if the to-be fetched
        field is a primary key field.
        """
        opts = instance._meta
        f = opts.get_field(name)
        link_field = opts.get_ancestor_link(f.model)
        if f.primary_key and f != link_field:
            return getattr(instance, link_field.attname)
        return None


class RegisterLookupMixin:

    @classmethod
    def _get_lookup(cls, lookup_name):
        return cls.get_lookups().get(lookup_name, None)

    @classmethod
    @functools.lru_cache(maxsize=None)
    def get_lookups(cls):
        class_lookups = [parent.__dict__.get('class_lookups', {}) for parent in inspect.getmro(cls)]
        return cls.merge_dicts(class_lookups)

    def get_lookup(self, lookup_name):
        from django.db.models.lookups import Lookup
        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, 'output_field'):
            return self.output_field.get_lookup(lookup_name)
        if found is not None and not issubclass(found, Lookup):
            return None
        return found

    def get_transform(self, lookup_name):
        from django.db.models.lookups import Transform
        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, 'output_field'):
            return self.output_field.get_transform(lookup_name)
        if found is not None and not issubclass(found, Transform):
            return None
        return found

    @staticmethod
    def merge_dicts(dicts):
        """
        Merge dicts in reverse to preference the order of the original list. e.g.,
        merge_dicts([a, b]) will preference the keys in 'a' over those in 'b'.
        """
        merged = {}
        for d in reversed(dicts):
            merged.update(d)
        return merged

    @classmethod
    def _clear_cached_lookups(cls):
        for subclass in subclasses(cls):
            subclass.get_lookups.cache_clear()

    @classmethod
    def register_lookup(cls, lookup, lookup_name=None):
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        if 'class_lookups' not in cls.__dict__:
            cls.class_lookups = {}
        cls.class_lookups[lookup_name] = lookup
        cls._clear_cached_lookups()
        return lookup

    @classmethod
    def _unregister_lookup(cls, lookup, lookup_name=None):
        """
        Remove given lookup from cls lookups. For use in tests only as it's
        not thread-safe.
        """
        if lookup_name is None:
            lookup_name = lookup.lookup_name
        del cls.class_lookups[lookup_name]


def select_related_descend(field, restricted, requested, load_fields, reverse=False):
    """
    Return True if this field should be used to descend deeper for
    select_related() purposes. Used by both the query construction code
    (sql.query.fill_related_selections()) and the model instance creation code
    (query.get_klass_info()).

    Arguments:
     * field - the field to be checked
     * restricted - a boolean field, indicating if the field list has been
       manually restricted using a requested clause)
     * requested - The select_related() dictionary.
     * load_fields - the set of fields to be loaded on this model
     * reverse - boolean, True if we are checking a reverse select related
    """
    if not field.remote_field:
        return False
    if field.remote_field.parent_link and not reverse:
        return False
    if restricted:
        if reverse and field.related_query_name() not in requested:
            return False
        if not reverse and field.name not in requested:
            return False
    if not restricted and field.null:
        return False
    if load_fields:
        if field.attname not in load_fields:
            if restricted and field.name in requested:
                raise InvalidQuery("Field %s.%s cannot be both deferred"
                                   " and traversed using select_related"
                                   " at the same time." %
                                   (field.model._meta.object_name, field.name))
    return True


def refs_expression(lookup_parts, annotations):
    """
    Check if the lookup_parts contains references to the given annotations set.
    Because the LOOKUP_SEP is contained in the default annotation names, check
    each prefix of the lookup_parts for a match.
    """
    for n in range(len(lookup_parts) + 1):
        level_n_lookup = LOOKUP_SEP.join(lookup_parts[0:n])
        if level_n_lookup in annotations and annotations[level_n_lookup]:
            return annotations[level_n_lookup], lookup_parts[n:]
    return False, ()


def check_rel_lookup_compatibility(model, target_opts, field):
    """
    Check that self.model is compatible with target_opts. Compatibility
    is OK if:
      1) model and opts match (where proxy inheritance is removed)
      2) model is parent of opts' model or the other way around
    """
    def check(opts):
        return (
            model._meta.concrete_model == opts.concrete_model or
            opts.concrete_model in model._meta.get_parent_list() or
            model in opts.get_parent_list()
        )
    # If the field is a primary key, then doing a query against the field's
    # model is ok, too. Consider the case:
    # class Restaurant(models.Model):
    #     place = OnetoOneField(Place, primary_key=True):
    # Restaurant.objects.filter(pk__in=Restaurant.objects.all()).
    # If we didn't have the primary key check, then pk__in (== place__in) would
    # give Place's opts as the target opts, but Restaurant isn't compatible
    # with that. This logic applies only to primary keys, as when doing __in=qs,
    # we are going to turn this into __in=qs.values('pk') later on.
    return (
        check(target_opts) or
        (getattr(field, 'primary_key', False) and check(field.model._meta))
    )
