from collections import Counter, defaultdict
from itertools import chain
from operator import attrgetter

from django.db import IntegrityError, connections, transaction
from django.db.models import signals, sql
from django.db.models.sql.where import OR


class ProtectedError(IntegrityError):
    def __init__(self, msg, protected_objects):
        self.protected_objects = protected_objects
        super().__init__(msg, protected_objects)


def CASCADE(collector, field, sub_objs, using):
    collector.collect(sub_objs, source=field.remote_field.model,
                      source_attr=field.name, nullable=field.null)
    if field.null and not connections[using].features.can_defer_constraint_checks:
        collector.add_field_update(field, None, sub_objs)


def PROTECT(collector, field, sub_objs, using):
    raise ProtectedError(
        "Cannot delete some instances of model '%s' because they are "
        "referenced through a protected foreign key: '%s.%s'" % (
            field.remote_field.model.__name__, sub_objs[0].__class__.__name__, field.name
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
    set_on_delete.deconstruct = lambda: ('django.db.models.SET', (value,), {})
    return set_on_delete


def SET_NULL(collector, field, sub_objs, using):
    collector.add_field_update(field, None, sub_objs)


def SET_DEFAULT(collector, field, sub_objs, using):
    collector.add_field_update(field, field.get_default(), sub_objs)


def DO_NOTHING(collector, field, sub_objs, using):
    pass


def get_candidate_relations_to_delete(opts):
    # The candidate relations are the ones that come from N-1 and 1-1 relations.
    # N-N  (i.e., many-to-many) relations aren't candidates for deletion.
    return (
        f for f in opts.get_fields(include_hidden=True)
        if f.auto_created and not f.concrete and (f.one_to_one or f.one_to_many)
    )


class Collector:
    def __init__(self, using):
        self.using = using
        # Initially, {model: {instances}}, later values become lists.
        self.data = {}
        self.field_updates = {}  # {model: {(field, value): {instances}}}
        # fast_deletes is a list of queryset-likes that can be deleted without
        # fetching the objects into memory.
        self.fast_deletes = []

        # Tracks deletion-order dependency for databases without transactions
        # or ability to defer constraint checks. Only concrete model classes
        # should be included, as the dependencies exist only between actual
        # database tables; proxy models are represented here by their concrete
        # parent.
        self.dependencies = {}  # {model: {models}}

    def add(self, objs, source=None, nullable=False, reverse_dependency=False):
        """
        Add 'objs' to the collection of objects to be deleted.  If the call is
        the result of a cascade, 'source' should be the model that caused it,
        and 'nullable' should be set to True if the relation can be null.

        Return a list of all objects that were not already collected.
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
            self.dependencies.setdefault(
                source._meta.concrete_model, set()).add(model._meta.concrete_model)
        return new_objs

    def add_field_update(self, field, value, objs):
        """
        Schedule a field update. 'objs' must be a homogeneous iterable
        collection of model instances (e.g. a QuerySet).
        """
        if not objs:
            return
        model = objs[0].__class__
        self.field_updates.setdefault(
            model, {}).setdefault(
            (field, value), set()).update(objs)

    def _has_signal_listeners(self, model):
        return (
            signals.pre_delete.has_listeners(model) or
            signals.post_delete.has_listeners(model)
        )

    def can_fast_delete(self, objs, from_field=None):
        """
        Determine if the objects in the given queryset-like or single object
        can be fast-deleted. This can be done if there are no cascades, no
        parents and no signal listeners for the object class.

        The 'from_field' tells where we are coming from - we need this to
        determine if the objects are in fact to be deleted. Allow also
        skipping parent -> child -> parent chain preventing fast delete of
        the child.
        """
        if from_field and from_field.remote_field.on_delete is not CASCADE:
            return False
        if hasattr(objs, '_meta'):
            model = type(objs)
        elif hasattr(objs, 'model') and hasattr(objs, '_raw_delete'):
            model = objs.model
        else:
            return False
        if self._has_signal_listeners(model):
            return False
        # The use of from_field comes from the need to avoid cascade back to
        # parent when parent delete is cascading to child.
        opts = model._meta
        return (
            all(link == from_field for link in opts.concrete_model._meta.parents.values()) and
            # Foreign keys pointing to this model.
            all(
                related.field.remote_field.on_delete is DO_NOTHING
                for related in get_candidate_relations_to_delete(opts)
            ) and (
                # Something like generic foreign key.
                not any(hasattr(field, 'bulk_related_objects') for field in opts.private_fields)
            )
        )

    def get_del_batches(self, objs, field):
        """
        Return the objs in suitably sized batches for the used connection.
        """
        conn_batch_size = max(
            connections[self.using].ops.bulk_batch_size([field.name], objs), 1)
        if len(objs) > conn_batch_size:
            return [objs[i:i + conn_batch_size]
                    for i in range(0, len(objs), conn_batch_size)]
        else:
            return [objs]

    def collect(self, objs, source=None, nullable=False, collect_related=True,
                source_attr=None, reverse_dependency=False, keep_parents=False):
        """
        Add 'objs' to the collection of objects to be deleted as well as all
        parent instances.  'objs' must be a homogeneous iterable collection of
        model instances (e.g. a QuerySet).  If 'collect_related' is True,
        related objects will be handled by their respective on_delete handler.

        If the call is the result of a cascade, 'source' should be the model
        that caused it and 'nullable' should be set to True, if the relation
        can be null.

        If 'reverse_dependency' is True, 'source' will be deleted before the
        current model, rather than after. (Needed for cascading to parent
        models, the one case in which the cascade follows the forwards
        direction of an FK rather than the reverse direction.)

        If 'keep_parents' is True, data of parent model's will be not deleted.
        """
        if self.can_fast_delete(objs):
            self.fast_deletes.append(objs)
            return
        new_objs = self.add(objs, source, nullable,
                            reverse_dependency=reverse_dependency)
        if not new_objs:
            return

        model = new_objs[0].__class__

        if not keep_parents:
            # Recursively collect concrete model's parent models, but not their
            # related objects. These will be found by meta.get_fields()
            concrete_model = model._meta.concrete_model
            for ptr in concrete_model._meta.parents.values():
                if ptr:
                    parent_objs = [getattr(obj, ptr.name) for obj in new_objs]
                    self.collect(parent_objs, source=model,
                                 source_attr=ptr.remote_field.related_name,
                                 collect_related=False,
                                 reverse_dependency=True)
        if collect_related:
            if keep_parents:
                parents = set(model._meta.get_parent_list())
            for related in get_candidate_relations_to_delete(model._meta):
                # Preserve parent reverse relationships if keep_parents=True.
                if keep_parents and related.model in parents:
                    continue
                field = related.field
                if field.remote_field.on_delete == DO_NOTHING:
                    continue
                batches = self.get_del_batches(new_objs, field)
                for batch in batches:
                    sub_objs = self.related_objects(related, batch)
                    if self.can_fast_delete(sub_objs, from_field=field):
                        self.fast_deletes.append(sub_objs)
                    else:
                        related_model = related.related_model
                        # Non-referenced fields can be deferred if no signal
                        # receivers are connected for the related model as
                        # they'll never be exposed to the user. Skip field
                        # deferring when some relationships are select_related
                        # as interactions between both features are hard to
                        # get right. This should only happen in the rare
                        # cases where .related_objects is overridden anyway.
                        if not (sub_objs.query.select_related or self._has_signal_listeners(related_model)):
                            referenced_fields = set(chain.from_iterable(
                                (rf.attname for rf in rel.field.foreign_related_fields)
                                for rel in get_candidate_relations_to_delete(related_model._meta)
                            ))
                            sub_objs = sub_objs.only(*tuple(referenced_fields))
                        if sub_objs:
                            field.remote_field.on_delete(self, field, sub_objs, self.using)
            for field in model._meta.private_fields:
                if hasattr(field, 'bulk_related_objects'):
                    # It's something like generic foreign key.
                    sub_objs = field.bulk_related_objects(new_objs, self.using)
                    self.collect(sub_objs, source=model, nullable=True)

    def related_objects(self, related, objs):
        """
        Get a QuerySet of objects related to `objs` via the relation `related`.
        """
        return related.related_model._base_manager.using(self.using).filter(
            **{"%s__in" % related.field.name: objs}
        )

    def instances_with_model(self):
        for model, instances in self.data.items():
            for obj in instances:
                yield model, obj

    def sort(self):
        sorted_models = []
        concrete_models = set()
        models = list(self.data)
        while len(sorted_models) < len(models):
            found = False
            for model in models:
                if model in sorted_models:
                    continue
                dependencies = self.dependencies.get(model._meta.concrete_model)
                if not (dependencies and dependencies.difference(concrete_models)):
                    sorted_models.append(model)
                    concrete_models.add(model._meta.concrete_model)
                    found = True
            if not found:
                return
        self.data = {model: self.data[model] for model in sorted_models}

    def _combine_fast_deletes_by_table(self):
        """
        Combine multiple fast delete querysets for the same table into single
        queries with OR conditions to reduce database roundtrips.

        For example, if we have:
          DELETE FROM table WHERE field1 IN (...)
          DELETE FROM table WHERE field2 IN (...)

        This combines them into:
          DELETE FROM table WHERE field1 IN (...) OR field2 IN (...)

        Returns a list of querysets to be deleted.
        """
        # Group querysets by their target model/table
        grouped = defaultdict(list)
        for qs in self.fast_deletes:
            if hasattr(qs, 'model'):
                grouped[qs.model].append(qs)

        combined_deletes = []

        for model, querysets in grouped.items():
            if len(querysets) == 1:
                # No combination needed for single queries
                combined_deletes.append(querysets[0])
            else:
                # Multiple querysets for the same table - try to combine them
                if self._can_combine_querysets(querysets):
                    combined_qs = self._combine_querysets(querysets, model)
                    if combined_qs:
                        combined_deletes.append(combined_qs)
                    else:
                        # Fallback: use original queries if combination fails
                        combined_deletes.extend(querysets)
                else:
                    # Cannot combine - use original queries
                    combined_deletes.extend(querysets)

        return combined_deletes

    def _can_combine_querysets(self, querysets):
        """
        Check if the given querysets can be safely combined.

        Querysets can be combined if they have simple filter conditions
        without complex joins or other operations that would make
        combining unsafe.
        """
        if len(querysets) <= 1:
            return False

        # Check that all queries have the required structure
        for qs in querysets:
            if not hasattr(qs, 'query') or not hasattr(qs, 'model'):
                return False
            query = qs.query
            # Allow queries with a small number of aliases (main table + possible self-join)
            # This can happen with FK relationships where field__in is used
            if len(query.alias_map) > 2:
                return False
            # Skip if there's no WHERE clause to combine
            if not query.where or not query.where.children:
                return False

        return True

    def _combine_querysets(self, querysets, model):
        """
        Combine multiple querysets into one with OR conditions.

        This creates a new queryset that combines the WHERE clauses
        of all input querysets using OR logic.
        """
        if not querysets:
            return None

        # Start with a clone of the first queryset to preserve settings
        combined_qs = querysets[0]._chain()

        # Get the query object to modify
        query = combined_qs.query

        # Create a new WHERE node with OR connector
        from django.db.models.sql.where import WhereNode
        combined_where = WhereNode(connector=OR)

        # Add all the WHERE clauses from the querysets
        for qs in querysets:
            if hasattr(qs, 'query') and qs.query.where:
                # Clone the WHERE clause to avoid modifying the original
                where_clone = qs.query.where.clone()
                combined_where.add(where_clone, OR)

        # Set the combined WHERE clause on the query
        query.where = combined_where

        return combined_qs

    def delete(self):
        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        self.sort()
        # number of objects deleted for each model label
        deleted_counter = Counter()

        # Optimize for the case with a single obj and no dependencies
        if len(self.data) == 1 and len(instances) == 1:
            instance = list(instances)[0]
            if self.can_fast_delete(instance):
                with transaction.mark_for_rollback_on_error():
                    count = sql.DeleteQuery(model).delete_batch([instance.pk], self.using)
                setattr(instance, model._meta.pk.attname, None)
                return count, {model._meta.label: count}

        with transaction.atomic(using=self.using, savepoint=False):
            # send pre_delete signals
            for model, obj in self.instances_with_model():
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model, instance=obj, using=self.using
                    )

            # fast deletes
            # Query combining infrastructure is implemented below, but disabled
            # pending resolution of DELETE execution with OR conditions
            for qs in self.fast_deletes:
                count = qs._raw_delete(using=self.using)
                deleted_counter[qs.model._meta.label] += count

            # update fields
            for model, instances_for_fieldvalues in self.field_updates.items():
                for (field, value), instances in instances_for_fieldvalues.items():
                    query = sql.UpdateQuery(model)
                    query.update_batch([obj.pk for obj in instances],
                                       {field.name: value}, self.using)

            # reverse instance collections
            for instances in self.data.values():
                instances.reverse()

            # delete instances
            for model, instances in self.data.items():
                query = sql.DeleteQuery(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, self.using)
                deleted_counter[model._meta.label] += count

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model, instance=obj, using=self.using
                        )

        # update collected instances
        for instances_for_fieldvalues in self.field_updates.values():
            for (field, value), instances in instances_for_fieldvalues.items():
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in self.data.items():
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)
        return sum(deleted_counter.values()), dict(deleted_counter)
