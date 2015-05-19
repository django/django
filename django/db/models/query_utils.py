"""
Various data structures used in query construction.

Factored out from django.db.models.query to avoid making the main module very
large and/or so that they can be used by other modules without getting into
circular import difficulties.
"""
from __future__ import unicode_literals

from collections import namedtuple

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db.backends import utils
from django.db.models.constants import LOOKUP_SEP
from django.utils import six, tree

# PathInfo is used when converting lookups (fk__somecol). The contents
# describe the relation in Model terms (model Options and Fields for both
# sides of the relation. The join_field is the field backing the relation.
PathInfo = namedtuple('PathInfo', 'from_opts to_opts target_fields join_field m2m direct')


class InvalidQuery(Exception):
    """
    The query passed to raw isn't a safe query to use with raw.
    """
    pass


class QueryWrapper(object):
    """
    A type that indicates the contents are an SQL fragment and the associate
    parameters. Can be used to pass opaque data to a where-clause, for example.
    """
    def __init__(self, sql, params):
        self.data = sql, list(params)

    def as_sql(self, compiler=None, connection=None):
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
        super(Q, self).__init__(children=list(args) + list(six.iteritems(kwargs)))

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise TypeError(other)
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

    def clone(self):
        clone = self.__class__._new_instance(
            children=[], connector=self.connector, negated=self.negated)
        for child in self.children:
            if hasattr(child, 'clone'):
                clone.children.append(child.clone())
            else:
                clone.children.append(child)
        return clone

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # We must promote any new joins to left outer joins so that when Q is
        # used as an expression, rows aren't filtered due to joins.
        joins_before = query.tables[:]
        clause, joins = query._add_q(self, reuse, allow_joins=allow_joins, split_subq=False)
        joins_to_promote = [j for j in joins if j not in joins_before]
        query.promote_joins(joins_to_promote)
        return clause

    @classmethod
    def _refs_aggregate(cls, obj, existing_aggregates):
        if not isinstance(obj, tree.Node):
            aggregate, aggregate_lookups = refs_aggregate(obj[0].split(LOOKUP_SEP), existing_aggregates)
            if not aggregate and hasattr(obj[1], 'refs_aggregate'):
                return obj[1].refs_aggregate(existing_aggregates)
            return aggregate, aggregate_lookups
        for c in obj.children:
            aggregate, aggregate_lookups = cls._refs_aggregate(c, existing_aggregates)
            if aggregate:
                return aggregate, aggregate_lookups
        return False, ()

    def refs_aggregate(self, existing_aggregates):
        if not existing_aggregates:
            return False

        return self._refs_aggregate(self, existing_aggregates)


class DeferredAttribute(object):
    """
    A wrapper for a deferred-loading field. When the value is read from this
    object the first time, the query is executed.
    """
    def __init__(self, field_name, model):
        self.field_name = field_name

    def __get__(self, instance, owner):
        """
        Retrieves and caches the value from the datastore on the first lookup.
        Returns the cached value.
        """
        non_deferred_model = instance._meta.proxy_for_model
        opts = non_deferred_model._meta

        assert instance is not None
        data = instance.__dict__
        if data.get(self.field_name, self) is self:
            # self.field_name is the attname of the field, but only() takes the
            # actual name, so we need to translate it here.
            try:
                f = opts.get_field(self.field_name)
            except FieldDoesNotExist:
                f = [f for f in opts.fields if f.attname == self.field_name][0]
            name = f.name
            # Let's see if the field is part of the parent chain. If so we
            # might be able to reuse the already loaded value. Refs #18343.
            val = self._check_parent_chain(instance, name)
            if val is None:
                instance.refresh_from_db(fields=[self.field_name])
                val = getattr(instance, self.field_name)
            data[self.field_name] = val
        return data[self.field_name]

    def __set__(self, instance, value):
        """
        Deferred loading attributes can be set normally (which means there will
        never be a database lookup involved.
        """
        instance.__dict__[self.field_name] = value

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


def select_related_descend(field, restricted, requested, load_fields, reverse=False):
    """
    Returns True if this field should be used to descend deeper for
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
    if not field.rel:
        return False
    if field.rel.parent_link and not reverse:
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
            return False
    return True


# This function is needed because data descriptors must be defined on a class
# object, not an instance, to have any effect.

def deferred_class_factory(model, attrs):
    """
    Returns a class object that is a copy of "model" with the specified "attrs"
    being replaced with DeferredAttribute objects. The "pk_value" ties the
    deferred attributes to a particular instance of the model.
    """
    if not attrs:
        return model
    # Never create deferred models based on deferred model
    if model._deferred:
        # Deferred models are proxies for the non-deferred model. We never
        # create chains of defers => proxy_for_model is the non-deferred
        # model.
        model = model._meta.proxy_for_model
    # The app registry wants a unique name for each model, otherwise the new
    # class won't be created (we get an exception). Therefore, we generate
    # the name using the passed in attrs. It's OK to reuse an existing class
    # object if the attrs are identical.
    name = "%s_Deferred_%s" % (model.__name__, '_'.join(sorted(list(attrs))))
    name = utils.truncate_name(name, 80, 32)

    try:
        return apps.get_model(model._meta.app_label, name)

    except LookupError:

        class Meta:
            proxy = True
            app_label = model._meta.app_label

        overrides = {attr: DeferredAttribute(attr, model) for attr in attrs}
        overrides["Meta"] = Meta
        overrides["__module__"] = model.__module__
        overrides["_deferred"] = True
        return type(str(name), (model,), overrides)


# The above function is also used to unpickle model instances with deferred
# fields.
deferred_class_factory.__safe_for_unpickling__ = True


def refs_aggregate(lookup_parts, aggregates):
    """
    A little helper method to check if the lookup_parts contains references
    to the given aggregates set. Because the LOOKUP_SEP is contained in the
    default annotation names we must check each prefix of the lookup_parts
    for a match.
    """
    for n in range(len(lookup_parts) + 1):
        level_n_lookup = LOOKUP_SEP.join(lookup_parts[0:n])
        if level_n_lookup in aggregates and aggregates[level_n_lookup].contains_aggregate:
            return aggregates[level_n_lookup], lookup_parts[n:]
    return False, ()
