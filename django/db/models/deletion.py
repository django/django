from operator import attrgetter

from django.db import connections, transaction, IntegrityError
from django.db.models import signals, sql
from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE
from django.utils.datastructures import SortedDict
from django.utils.functional import wraps


class ProtectedError(IntegrityError):
    def __init__(self, msg, protected_objects):
        self.protected_objects = protected_objects
        # TODO change this to use super() when we drop Python 2.4
        IntegrityError.__init__(self, msg, protected_objects)


def CASCADE(collector, field, sub_objs, using):
    collector.collect(sub_objs, source=field.rel.to,
                      source_attr=field.name, nullable=field.null)
    if field.null and not connections[using].features.can_defer_constraint_checks:
        collector.add_field_update(field, None, sub_objs)


def PROTECT(collector, field, sub_objs, using):
    raise ProtectedError("Cannot delete some instances of model '%s' because "
        "they are referenced through a protected foreign key: '%s.%s'" % (
            field.rel.to.__name__, sub_objs[0].__class__.__name__, field.name
        ),
        sub_objs
    )


def SET(value):
    if callable(value):
        def set_on_delete(collector, field, sub_objs, using):
            collector.add_field_update(field, value(), sub_objs)
    else:
        def set_on_delete(collector, field, sub_objs, using):
            collector.add_field_update(field, value, sub_objs)
    return set_on_delete


SET_NULL = SET(None)


def SET_DEFAULT(collector, field, sub_objs, using):
    collector.add_field_update(field, field.get_default(), sub_objs)


def DO_NOTHING(collector, field, sub_objs, using):
    pass


def force_managed(func):
    @wraps(func)
    def decorated(self, *args, **kwargs):
        if not transaction.is_managed(using=self.using):
            transaction.enter_transaction_management(using=self.using)
            forced_managed = True
        else:
            forced_managed = False
        try:
            func(self, *args, **kwargs)
            if forced_managed:
                transaction.commit(using=self.using)
            else:
                transaction.commit_unless_managed(using=self.using)
        finally:
            if forced_managed:
                transaction.leave_transaction_management(using=self.using)
    return decorated


class Collector(object):
    def __init__(self, using):
        self.using = using
        # Initially, {model: set([instances])}, later values become lists.
        self.data = {}
        self.batches = {} # {model: {field: set([instances])}}
        self.field_updates = {} # {model: {(field, value): set([instances])}}
        self.dependencies = {} # {model: set([models])}

    def add(self, objs, source=None, nullable=False, reverse_dependency=False):
        """
        Adds 'objs' to the collection of objects to be deleted.  If the call is
        the result of a cascade, 'source' should be the model that caused it,
        and 'nullable' should be set to True if the relation can be null.

        Returns a list of all objects that were not already collected.
        """
        if not objs:
            return []
        new_objs = []
        model = objs[0].__class__
        instances = self.data.setdefault(model, set())
        for obj in objs:
            if obj not in instances:
                new_objs.append(obj)
        instances.update(new_objs)
        # Nullable relationships can be ignored -- they are nulled out before
        # deleting, and therefore do not affect the order in which objects have
        # to be deleted.
        if source is not None and not nullable:
            if reverse_dependency:
                source, model = model, source
            self.dependencies.setdefault(source, set()).add(model)
        return new_objs

    def add_batch(self, model, field, objs):
        """
        Schedules a batch delete. Every instance of 'model' that is related to
        an instance of 'obj' through 'field' will be deleted.
        """
        self.batches.setdefault(model, {}).setdefault(field, set()).update(objs)

    def add_field_update(self, field, value, objs):
        """
        Schedules a field update. 'objs' must be a homogenous iterable
        collection of model instances (e.g. a QuerySet).
        """
        if not objs:
            return
        model = objs[0].__class__
        self.field_updates.setdefault(
            model, {}).setdefault(
            (field, value), set()).update(objs)

    def collect(self, objs, source=None, nullable=False, collect_related=True,
        source_attr=None, reverse_dependency=False):
        """
        Adds 'objs' to the collection of objects to be deleted as well as all
        parent instances.  'objs' must be a homogenous iterable collection of
        model instances (e.g. a QuerySet).  If 'collect_related' is True,
        related objects will be handled by their respective on_delete handler.

        If the call is the result of a cascade, 'source' should be the model
        that caused it and 'nullable' should be set to True, if the relation
        can be null.

        If 'reverse_dependency' is True, 'source' will be deleted before the
        current model, rather than after. (Needed for cascading to parent
        models, the one case in which the cascade follows the forwards
        direction of an FK rather than the reverse direction.)
        """
        new_objs = self.add(objs, source, nullable,
                            reverse_dependency=reverse_dependency)
        if not new_objs:
            return
        model = new_objs[0].__class__

        # Recursively collect parent models, but not their related objects.
        # These will be found by meta.get_all_related_objects()
        for parent_model, ptr in model._meta.parents.iteritems():
            if ptr:
                parent_objs = [getattr(obj, ptr.name) for obj in new_objs]
                self.collect(parent_objs, source=model,
                             source_attr=ptr.rel.related_name,
                             collect_related=False,
                             reverse_dependency=True)

        if collect_related:
            for related in model._meta.get_all_related_objects(include_hidden=True):
                field = related.field
                if related.model._meta.auto_created:
                    self.add_batch(related.model, field, new_objs)
                else:
                    sub_objs = self.related_objects(related, new_objs)
                    if not sub_objs:
                        continue
                    field.rel.on_delete(self, field, sub_objs, self.using)

            # TODO This entire block is only needed as a special case to
            # support cascade-deletes for GenericRelation. It should be
            # removed/fixed when the ORM gains a proper abstraction for virtual
            # or composite fields, and GFKs are reworked to fit into that.
            for relation in model._meta.many_to_many:
                if not relation.rel.through:
                    sub_objs = relation.bulk_related_objects(new_objs, self.using)
                    self.collect(sub_objs,
                                 source=model,
                                 source_attr=relation.rel.related_name,
                                 nullable=True)

    def related_objects(self, related, objs):
        """
        Gets a QuerySet of objects related to ``objs`` via the relation ``related``.

        """
        return related.model._base_manager.using(self.using).filter(
            **{"%s__in" % related.field.name: objs}
        )

    def instances_with_model(self):
        for model, instances in self.data.iteritems():
            for obj in instances:
                yield model, obj

    def sort(self):
        sorted_models = []
        models = self.data.keys()
        while len(sorted_models) < len(models):
            found = False
            for model in models:
                if model in sorted_models:
                    continue
                dependencies = self.dependencies.get(model)
                if not (dependencies and dependencies.difference(sorted_models)):
                    sorted_models.append(model)
                    found = True
            if not found:
                return
        self.data = SortedDict([(model, self.data[model])
                                for model in sorted_models])

    @force_managed
    def delete(self):
        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer contraint checks until the
        # end of a transaction.
        self.sort()

        # send pre_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created:
                signals.pre_delete.send(
                    sender=model, instance=obj, using=self.using
                )

        # update fields
        for model, instances_for_fieldvalues in self.field_updates.iteritems():
            query = sql.UpdateQuery(model)
            for (field, value), instances in instances_for_fieldvalues.iteritems():
                query.update_batch([obj.pk for obj in instances],
                                   {field.name: value}, self.using)

        # reverse instance collections
        for instances in self.data.itervalues():
            instances.reverse()

        # delete batches
        for model, batches in self.batches.iteritems():
            query = sql.DeleteQuery(model)
            for field, instances in batches.iteritems():
                query.delete_batch([obj.pk for obj in instances], self.using, field)

        # delete instances
        for model, instances in self.data.iteritems():
            query = sql.DeleteQuery(model)
            pk_list = [obj.pk for obj in instances]
            query.delete_batch(pk_list, self.using)

        # send post_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created:
                signals.post_delete.send(
                    sender=model, instance=obj, using=self.using
                )

        # update collected instances
        for model, instances_for_fieldvalues in self.field_updates.iteritems():
            for (field, value), instances in instances_for_fieldvalues.iteritems():
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in self.data.iteritems():
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)
