from __future__ import unicode_literals

import warnings

from django.apps import apps
from django.core import checks
from django.db import connections, router, transaction
from django.db.models import signals
from django.db.models.deletion import CASCADE
from django.db.models.fields import BLANK_CHOICE_DASH, Field, FieldDoesNotExist
from django.db.models.lookups import IsNull
from django.db.models.query_utils import PathInfo
from django.db.models.expressions import Col
from django.utils.encoding import force_text, smart_text
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import cached_property
from django.core import exceptions

RECURSIVE_RELATIONSHIP_CONSTANT = 'self'


def add_lazy_relation(cls, field, relation, operation):
    """
    Adds a lookup on ``cls`` when a related field is defined using a string,
    i.e.::

        class MyModel(Model):
            fk = ForeignKey("AnotherModel")

    This string can be:

        * RECURSIVE_RELATIONSHIP_CONSTANT (i.e. "self") to indicate a recursive
          relation.

        * The name of a model (i.e "AnotherModel") to indicate another model in
          the same app.

        * An app-label and model name (i.e. "someapp.AnotherModel") to indicate
          another model in a different app.

    If the other model hasn't yet been loaded -- almost a given if you're using
    lazy relationships -- then the relation won't be set up until the
    class_prepared signal fires at the end of model initialization.

    operation is the work that must be performed once the relation can be resolved.
    """
    # Check for recursive relations
    if relation == RECURSIVE_RELATIONSHIP_CONSTANT:
        app_label = cls._meta.app_label
        model_name = cls.__name__

    else:
        # Look for an "app.Model" relation

        if isinstance(relation, six.string_types):
            try:
                app_label, model_name = relation.split(".")
            except ValueError:
                # If we can't split, assume a model in current app
                app_label = cls._meta.app_label
                model_name = relation
        else:
            # it's actually a model class
            app_label = relation._meta.app_label
            model_name = relation._meta.object_name

    # Try to look up the related model, and if it's already loaded resolve the
    # string right away. If get_registered_model raises a LookupError, it means
    # that the related model isn't loaded yet, so we need to pend the relation
    # until the class is prepared.
    try:
        model = cls._meta.apps.get_registered_model(app_label, model_name)
    except LookupError:
        key = (app_label, model_name)
        value = (cls, field, operation)
        cls._meta.apps._pending_lookups.setdefault(key, []).append(value)
    else:
        operation(field, model, cls)


def do_pending_lookups(sender, **kwargs):
    """
    Handle any pending relations to the sending model. Sent from class_prepared.
    """
    key = (sender._meta.app_label, sender.__name__)
    for cls, field, operation in sender._meta.apps._pending_lookups.pop(key, []):
        operation(field, sender, cls)

signals.class_prepared.connect(do_pending_lookups)


class RelatedField(Field):
    def check(self, **kwargs):
        errors = super(RelatedField, self).check(**kwargs)
        errors.extend(self._check_related_name_is_valid())
        errors.extend(self._check_relation_model_exists())
        errors.extend(self._check_referencing_to_swapped_model())
        errors.extend(self._check_clashes())
        return errors

    def _check_related_name_is_valid(self):
        import re
        import keyword
        related_name = self.rel.related_name

        is_valid_id = (related_name and re.match('^[a-zA-Z_][a-zA-Z0-9_]*$', related_name)
                       and not keyword.iskeyword(related_name))
        if related_name and not (is_valid_id or related_name.endswith('+')):
            return [
                checks.Error(
                    "The name '%s' is invalid related_name for field %s.%s" %
                    (self.rel.related_name, self.model._meta.object_name,
                     self.name),
                    hint="Related name must be a valid Python identifier or end with a '+'",
                    obj=self,
                    id='fields.E306',
                )
            ]
        return []

    def _check_relation_model_exists(self):
        rel_is_missing = self.rel.to not in apps.get_models()
        rel_is_string = isinstance(self.rel.to, six.string_types)
        model_name = self.rel.to if rel_is_string else self.rel.to._meta.object_name
        if rel_is_missing and (rel_is_string or not self.rel.to._meta.swapped):
            return [
                checks.Error(
                    ("Field defines a relation with model '%s', which "
                     "is either not installed, or is abstract.") % model_name,
                    hint=None,
                    obj=self,
                    id='fields.E300',
                )
            ]
        return []

    def _check_referencing_to_swapped_model(self):
        if (self.rel.to not in apps.get_models() and
                not isinstance(self.rel.to, six.string_types) and
                self.rel.to._meta.swapped):
            model = "%s.%s" % (
                self.rel.to._meta.app_label,
                self.rel.to._meta.object_name
            )
            return [
                checks.Error(
                    ("Field defines a relation with the model '%s', "
                     "which has been swapped out.") % model,
                    hint="Update the relation to point at 'settings.%s'." % self.rel.to._meta.swappable,
                    obj=self,
                    id='fields.E301',
                )
            ]
        return []

    def _check_clashes(self):
        """ Check accessor and reverse query name clashes. """

        from django.db.models.base import ModelBase

        errors = []
        opts = self.model._meta

        # `f.rel.to` may be a string instead of a model. Skip if model name is
        # not resolved.
        if not isinstance(self.rel.to, ModelBase):
            return []

        # If the field doesn't install backward relation on the target model (so
        # `is_hidden` returns True), then there are no clashes to check and we
        # can skip these fields.
        if self.rel.is_hidden():
            return []

        try:
            self.rel
        except AttributeError:
            return []

        # Consider that we are checking field `Model.foreign` and the models
        # are:
        #
        #     class Target(models.Model):
        #         model = models.IntegerField()
        #         model_set = models.IntegerField()
        #
        #     class Model(models.Model):
        #         foreign = models.ForeignKey(Target)
        #         m2m = models.ManyToManyField(Target)

        rel_opts = self.rel.to._meta
        # rel_opts.object_name == "Target"
        rel_name = self.rel.get_accessor_name()  # i. e. "model_set"
        rel_query_name = self.related_query_name()  # i. e. "model"
        field_name = "%s.%s" % (opts.object_name,
            self.name)  # i. e. "Model.field"

        # Check clashes between accessor or reverse query name of `field`
        # and any other field name -- i.e. accessor for Model.foreign is
        # model_set and it clashes with Target.model_set.
        potential_clashes = rel_opts.fields + rel_opts.many_to_many
        for clash_field in potential_clashes:
            clash_name = "%s.%s" % (rel_opts.object_name,
                clash_field.name)  # i. e. "Target.model_set"
            if clash_field.name == rel_name:
                errors.append(
                    checks.Error(
                        "Reverse accessor for '%s' clashes with field name '%s'." % (field_name, clash_name),
                        hint=("Rename field '%s', or add/change a related_name "
                              "argument to the definition for field '%s'.") % (clash_name, field_name),
                        obj=self,
                        id='fields.E302',
                    )
                )

            if clash_field.name == rel_query_name:
                errors.append(
                    checks.Error(
                        "Reverse query name for '%s' clashes with field name '%s'." % (field_name, clash_name),
                        hint=("Rename field '%s', or add/change a related_name "
                              "argument to the definition for field '%s'.") % (clash_name, field_name),
                        obj=self,
                        id='fields.E303',
                    )
                )

        # Check clashes between accessors/reverse query names of `field` and
        # any other field accessor -- i. e. Model.foreign accessor clashes with
        # Model.m2m accessor.
        potential_clashes = rel_opts.get_all_related_many_to_many_objects()
        potential_clashes += rel_opts.get_all_related_objects()
        potential_clashes = (r for r in potential_clashes
            if r.field is not self)
        for clash_field in potential_clashes:
            clash_name = "%s.%s" % (  # i. e. "Model.m2m"
                clash_field.model._meta.object_name,
                clash_field.field.name)
            if clash_field.get_accessor_name() == rel_name:
                errors.append(
                    checks.Error(
                        "Reverse accessor for '%s' clashes with reverse accessor for '%s'." % (field_name, clash_name),
                        hint=("Add or change a related_name argument "
                              "to the definition for '%s' or '%s'.") % (field_name, clash_name),
                        obj=self,
                        id='fields.E304',
                    )
                )

            if clash_field.get_accessor_name() == rel_query_name:
                errors.append(
                    checks.Error(
                        "Reverse query name for '%s' clashes with reverse query name for '%s'."
                        % (field_name, clash_name),
                        hint=("Add or change a related_name argument "
                              "to the definition for '%s' or '%s'.") % (field_name, clash_name),
                        obj=self,
                        id='fields.E305',
                    )
                )

        return errors

    def db_type(self, connection):
        '''By default related field will not have a column
           as it relates columns to another table'''
        return None

    def contribute_to_class(self, cls, name, virtual_only=False):
        sup = super(RelatedField, self)

        # Store the opts for related_query_name()
        self.opts = cls._meta

        if hasattr(sup, 'contribute_to_class'):
            sup.contribute_to_class(cls, name, virtual_only=virtual_only)

        if not cls._meta.abstract and self.rel.related_name:
            related_name = force_text(self.rel.related_name) % {
                'class': cls.__name__.lower(),
                'app_label': cls._meta.app_label.lower()
            }
            self.rel.related_name = related_name
        other = self.rel.to
        if isinstance(other, six.string_types) or other._meta.pk is None:
            def resolve_related_class(field, model, cls):
                field.rel.to = model
                field.do_related_class(model, cls)
            add_lazy_relation(cls, self, other, resolve_related_class)
        else:
            self.do_related_class(other, cls)

    @property
    def swappable_setting(self):
        """
        Gets the setting that this is powered from for swapping, or None
        if it's not swapped in / marked with swappable=False.
        """
        if self.swappable:
            # Work out string form of "to"
            if isinstance(self.rel.to, six.string_types):
                to_string = self.rel.to
            else:
                to_string = "%s.%s" % (
                    self.rel.to._meta.app_label,
                    self.rel.to._meta.object_name,
                )
            # See if anything swapped/swappable matches
            for model in apps.get_models(include_swapped=True):
                if model._meta.swapped:
                    if model._meta.swapped == to_string:
                        return model._meta.swappable
                if ("%s.%s" % (model._meta.app_label, model._meta.object_name)) == to_string and model._meta.swappable:
                    return model._meta.swappable
        return None

    def set_attributes_from_rel(self):
        self.name = self.name or (self.rel.to._meta.model_name + '_' + self.rel.to._meta.pk.name)
        if self.verbose_name is None:
            self.verbose_name = self.rel.to._meta.verbose_name
        self.rel.set_field_name()

    @property
    def related(self):
        warnings.warn(
            "Usage of field.related has been deprecated. Use field.rel instead.",
            RemovedInDjango20Warning, 2)
        return self.rel

    def do_related_class(self, other, cls):
        self.set_attributes_from_rel()
        if not cls._meta.abstract:
            self.contribute_to_related_class(other, self.rel)

    def get_limit_choices_to(self):
        """Returns 'limit_choices_to' for this model field.

        If it is a callable, it will be invoked and the result will be
        returned.
        """
        if callable(self.rel.limit_choices_to):
            return self.rel.limit_choices_to()
        return self.rel.limit_choices_to

    def formfield(self, **kwargs):
        """Passes ``limit_choices_to`` to field being constructed.

        Only passes it if there is a type that supports related fields.
        This is a similar strategy used to pass the ``queryset`` to the field
        being constructed.
        """
        defaults = {}
        if hasattr(self.rel, 'get_related_field'):
            # If this is a callable, do not invoke it here. Just pass
            # it in the defaults for when the form class will later be
            # instantiated.
            limit_choices_to = self.rel.limit_choices_to
            defaults.update({
                'limit_choices_to': limit_choices_to,
            })
        defaults.update(kwargs)
        return super(RelatedField, self).formfield(**defaults)

    def related_query_name(self):
        # This method defines the name that can be used to identify this
        # related object in a table-spanning query. It uses the lower-cased
        # object_name by default, but this can be overridden with the
        # "related_name" option.
        return self.rel.related_query_name or self.rel.related_name or self.opts.model_name


class ReverseSingleRelatedObjectDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # a single "remote" value, on the class that defines the related field.
    # In the example "choice.poll", the poll attribute is a
    # ReverseSingleRelatedObjectDescriptor instance.
    def __init__(self, field_with_rel):
        self.field = field_with_rel
        self.cache_name = self.field.get_cache_name()

    @cached_property
    def RelatedObjectDoesNotExist(self):
        # The exception can't be created at initialization time since the
        # related model might not be resolved yet; `rel.to` might still be
        # a string model reference.
        return type(
            str('RelatedObjectDoesNotExist'),
            (self.field.rel.to.DoesNotExist, AttributeError),
            {}
        )

    def is_cached(self, instance):
        return hasattr(instance, self.cache_name)

    def get_queryset(self, **hints):
        manager = self.field.rel.to._default_manager
        # If the related manager indicates that it should be used for
        # related fields, respect that.
        if not getattr(manager, 'use_for_related_fields', False):
            manager = self.field.rel.to._base_manager
        return manager.db_manager(hints=hints).all()

    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        rel_obj_attr = self.field.get_foreign_related_value
        instance_attr = self.field.get_local_related_value
        instances_dict = {instance_attr(inst): inst for inst in instances}
        related_field = self.field.foreign_related_fields[0]

        # FIXME: This will need to be revisited when we introduce support for
        # composite fields. In the meantime we take this practical approach to
        # solve a regression on 1.6 when the reverse manager in hidden
        # (related_name ends with a '+'). Refs #21410.
        # The check for len(...) == 1 is a special case that allows the query
        # to be join-less and smaller. Refs #21760.
        if self.field.rel.is_hidden() or len(self.field.foreign_related_fields) == 1:
            query = {'%s__in' % related_field.name: set(instance_attr(inst)[0] for inst in instances)}
        else:
            query = {'%s__in' % self.field.related_query_name(): instances}
        queryset = queryset.filter(**query)

        # Since we're going to assign directly in the cache,
        # we must manage the reverse relation cache manually.
        if not self.field.rel.multiple:
            rel_obj_cache_name = self.field.rel.get_cache_name()
            for rel_obj in queryset:
                instance = instances_dict[rel_obj_attr(rel_obj)]
                setattr(rel_obj, rel_obj_cache_name, instance)
        return queryset, rel_obj_attr, instance_attr, True, self.cache_name

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        try:
            rel_obj = getattr(instance, self.cache_name)
        except AttributeError:
            val = self.field.get_local_related_value(instance)
            if None in val:
                rel_obj = None
            else:
                params = {
                    rh_field.attname: getattr(instance, lh_field.attname)
                    for lh_field, rh_field in self.field.related_fields}
                qs = self.get_queryset(instance=instance)
                extra_filter = self.field.get_extra_descriptor_filter(instance)
                if isinstance(extra_filter, dict):
                    params.update(extra_filter)
                    qs = qs.filter(**params)
                else:
                    qs = qs.filter(extra_filter, **params)
                # Assuming the database enforces foreign keys, this won't fail.
                rel_obj = qs.get()
                if not self.field.rel.multiple:
                    setattr(rel_obj, self.field.rel.get_cache_name(), instance)
            setattr(instance, self.cache_name, rel_obj)
        if rel_obj is None and not self.field.null:
            raise self.RelatedObjectDoesNotExist(
                "%s has no %s." % (self.field.model.__name__, self.field.name)
            )
        else:
            return rel_obj

    def __set__(self, instance, value):
        # If null=True, we can assign null here, but otherwise the value needs
        # to be an instance of the related class.
        if value is None and self.field.null is False:
            raise ValueError(
                'Cannot assign None: "%s.%s" does not allow null values.' %
                (instance._meta.object_name, self.field.name)
            )
        elif value is not None and not isinstance(value, self.field.rel.to):
            raise ValueError(
                'Cannot assign "%r": "%s.%s" must be a "%s" instance.' % (
                    value,
                    instance._meta.object_name,
                    self.field.name,
                    self.field.rel.to._meta.object_name,
                )
            )
        elif value is not None:
            if instance._state.db is None:
                instance._state.db = router.db_for_write(instance.__class__, instance=value)
            elif value._state.db is None:
                value._state.db = router.db_for_write(value.__class__, instance=instance)
            elif value._state.db is not None and instance._state.db is not None:
                if not router.allow_relation(value, instance):
                    raise ValueError('Cannot assign "%r": the current database router prevents this relation.' % value)

        # If we're setting the value of a OneToOneField to None, we need to clear
        # out the cache on any old related object. Otherwise, deleting the
        # previously-related object will also cause this object to be deleted,
        # which is wrong.
        if value is None:
            # Look up the previously-related object, which may still be available
            # since we've not yet cleared out the related field.
            # Use the cache directly, instead of the accessor; if we haven't
            # populated the cache, then we don't care - we're only accessing
            # the object to invalidate the accessor cache, so there's no
            # need to populate the cache just to expire it again.
            related = getattr(instance, self.cache_name, None)

            # If we've got an old related object, we need to clear out its
            # cache. This cache also might not exist if the related object
            # hasn't been accessed yet.
            if related is not None:
                setattr(related, self.field.rel.get_cache_name(), None)

            for lh_field, rh_field in self.field.related_fields:
                setattr(instance, lh_field.attname, None)

        # Set the values of the related field.
        else:
            for lh_field, rh_field in self.field.related_fields:
                pk = value._get_pk_val()
                if pk is None:
                    raise ValueError(
                        'Cannot assign "%r": "%s" instance isn\'t saved in the database.' %
                        (value, self.field.rel.to._meta.object_name)
                    )
                setattr(instance, lh_field.attname, getattr(value, rh_field.attname))

        # Since we already know what the related object is, seed the related
        # object caches now, too. This avoids another db hit if you get the
        # object you just set.
        setattr(instance, self.cache_name, value)
        if value is not None and not self.field.rel.multiple:
            setattr(value, self.field.rel.get_cache_name(), instance)


def create_foreign_related_manager(superclass, rel_field, rel_model):
    class RelatedManager(superclass):
        def __init__(self, instance):
            super(RelatedManager, self).__init__()
            self.instance = instance
            self.core_filters = {'%s__exact' % rel_field.name: instance}
            self.model = rel_model

        def __call__(self, **kwargs):
            # We use **kwargs rather than a kwarg argument to enforce the
            # `manager='manager_name'` syntax.
            manager = getattr(self.model, kwargs.pop('manager'))
            manager_class = create_foreign_related_manager(manager.__class__, rel_field, rel_model)
            return manager_class(self.instance)
        do_not_call_in_templates = True

        def get_queryset(self):
            try:
                return self.instance._prefetched_objects_cache[rel_field.related_query_name()]
            except (AttributeError, KeyError):
                db = self._db or router.db_for_read(self.model, instance=self.instance)
                empty_strings_as_null = connections[db].features.interprets_empty_strings_as_nulls
                qs = super(RelatedManager, self).get_queryset()
                qs._add_hints(instance=self.instance)
                if self._db:
                    qs = qs.using(self._db)
                qs = qs.filter(**self.core_filters)
                for field in rel_field.foreign_related_fields:
                    val = getattr(self.instance, field.attname)
                    if val is None or (val == '' and empty_strings_as_null):
                        return qs.none()
                qs._known_related_objects = {rel_field: {self.instance.pk: self.instance}}
                return qs

        def get_prefetch_queryset(self, instances, queryset=None):
            if queryset is None:
                queryset = super(RelatedManager, self).get_queryset()

            queryset._add_hints(instance=instances[0])
            queryset = queryset.using(queryset._db or self._db)

            rel_obj_attr = rel_field.get_local_related_value
            instance_attr = rel_field.get_foreign_related_value
            instances_dict = {instance_attr(inst): inst for inst in instances}
            query = {'%s__in' % rel_field.name: instances}
            queryset = queryset.filter(**query)

            # Since we just bypassed this class' get_queryset(), we must manage
            # the reverse relation manually.
            for rel_obj in queryset:
                instance = instances_dict[rel_obj_attr(rel_obj)]
                setattr(rel_obj, rel_field.name, instance)
            cache_name = rel_field.related_query_name()
            return queryset, rel_obj_attr, instance_attr, False, cache_name

        def add(self, *objs):
            objs = list(objs)
            db = router.db_for_write(self.model, instance=self.instance)
            with transaction.atomic(using=db, savepoint=False):
                for obj in objs:
                    if not isinstance(obj, self.model):
                        raise TypeError("'%s' instance expected, got %r" %
                                        (self.model._meta.object_name, obj))
                    setattr(obj, rel_field.name, self.instance)
                    obj.save()
        add.alters_data = True

        def create(self, **kwargs):
            kwargs[rel_field.name] = self.instance
            db = router.db_for_write(self.model, instance=self.instance)
            return super(RelatedManager, self.db_manager(db)).create(**kwargs)
        create.alters_data = True

        def get_or_create(self, **kwargs):
            kwargs[rel_field.name] = self.instance
            db = router.db_for_write(self.model, instance=self.instance)
            return super(RelatedManager, self.db_manager(db)).get_or_create(**kwargs)
        get_or_create.alters_data = True

        def update_or_create(self, **kwargs):
            kwargs[rel_field.name] = self.instance
            db = router.db_for_write(self.model, instance=self.instance)
            return super(RelatedManager, self.db_manager(db)).update_or_create(**kwargs)
        update_or_create.alters_data = True

        # remove() and clear() are only provided if the ForeignKey can have a value of null.
        if rel_field.null:
            def remove(self, *objs, **kwargs):
                if not objs:
                    return
                bulk = kwargs.pop('bulk', True)
                val = rel_field.get_foreign_related_value(self.instance)
                old_ids = set()
                for obj in objs:
                    # Is obj actually part of this descriptor set?
                    if rel_field.get_local_related_value(obj) == val:
                        old_ids.add(obj.pk)
                    else:
                        raise rel_field.rel.to.DoesNotExist("%r is not related to %r." % (obj, self.instance))
                self._clear(self.filter(pk__in=old_ids), bulk)
            remove.alters_data = True

            def clear(self, **kwargs):
                bulk = kwargs.pop('bulk', True)
                self._clear(self, bulk)
            clear.alters_data = True

            def _clear(self, queryset, bulk):
                db = router.db_for_write(self.model, instance=self.instance)
                queryset = queryset.using(db)
                if bulk:
                    # `QuerySet.update()` is intrinsically atomic.
                    queryset.update(**{rel_field.name: None})
                else:
                    with transaction.atomic(using=db, savepoint=False):
                        for obj in queryset:
                            setattr(obj, rel_field.name, None)
                            obj.save(update_fields=[rel_field.name])
            _clear.alters_data = True

    return RelatedManager


class ForeignRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ForeignKey pointed at them by
    # some other model. In the example "poll.choice_set", the choice_set
    # attribute is a ForeignRelatedObjectsDescriptor instance.
    def __init__(self, related):
        self.related = related   # RelatedObject instance

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        return self.related_manager_cls(instance)

    def __set__(self, instance, value):
        # Force evaluation of `value` in case it's a queryset whose
        # value could be affected by `manager.clear()`. Refs #19816.
        value = tuple(value)

        manager = self.__get__(instance)
        db = router.db_for_write(manager.model, instance=manager.instance)
        with transaction.atomic(using=db, savepoint=False):
            # If the foreign key can support nulls, then completely clear the related set.
            # Otherwise, just move the named objects into the set.
            if self.related.field.null:
                manager.clear()
            manager.add(*value)

    @cached_property
    def related_manager_cls(self):
        # Dynamically create a class that subclasses the related model's default
        # manager.
        return create_foreign_related_manager(
            self.related.model._default_manager.__class__,
            self.related.field,
            self.related.model,
        )


class ForeignObjectRel(object):
    def __init__(self, field, to, related_name=None, limit_choices_to=None,
                 parent_link=False, on_delete=None, related_query_name=None):
        self.field = field
        self.to = to
        self.related_name = related_name
        self.related_query_name = related_query_name
        self.limit_choices_to = {} if limit_choices_to is None else limit_choices_to
        self.multiple = True
        self.parent_link = parent_link
        self.on_delete = on_delete
        self.symmetrical = False

    # This and the following cached_properties can't be initialized in
    # __init__ as the field doesn't have its model yet. Calling these methods
    # before field.contribute_to_class() has been called will result in
    # AttributeError
    @cached_property
    def model(self):
        if not self.field.model:
            raise AttributeError(
                "This property can't be accessed before self.field.contribute_to_class has been called.")
        return self.field.model

    @cached_property
    def opts(self):
        return self.model._meta

    @cached_property
    def to_opts(self):
        return self.to._meta

    @cached_property
    def parent_model(self):
        return self.to

    @cached_property
    def name(self):
        return '%s.%s' % (self.opts.app_label, self.opts.model_name)

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH,
                    limit_to_currently_related=False):
        """
        Returns choices with a default blank choices included, for use as
        SelectField choices for this field.

        Analog of django.db.models.fields.Field.get_choices(), provided
        initially for utilization by RelatedFieldListFilter.
        """
        first_choice = blank_choice if include_blank else []
        queryset = self.model._default_manager.all()
        if limit_to_currently_related:
            queryset = queryset.complex_filter(
                {'%s__isnull' % self.parent_model._meta.model_name: False}
            )
        lst = [(x._get_pk_val(), smart_text(x)) for x in queryset]
        return first_choice + lst

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        # Defer to the actual field definition for db prep
        return self.field.get_db_prep_lookup(lookup_type, value, connection=connection, prepared=prepared)

    def is_hidden(self):
        "Should the related object be hidden?"
        return self.related_name and self.related_name[-1] == '+'

    def get_joining_columns(self):
        return self.field.get_reverse_joining_columns()

    def get_extra_restriction(self, where_class, alias, related_alias):
        return self.field.get_extra_restriction(where_class, related_alias, alias)

    def set_field_name(self):
        """
        Sets the related field's name, this is not available until later stages
        of app loading, so set_field_name is called from
        set_attributes_from_rel()
        """
        # By default foreign object doesn't relate to any remote field (for
        # example custom multicolumn joins currently have no remote field).
        self.field_name = None

    def get_lookup_constraint(self, constraint_class, alias, targets, sources, lookup_type,
                              raw_value):
        return self.field.get_lookup_constraint(constraint_class, alias, targets, sources,
                                                lookup_type, raw_value)

    def get_accessor_name(self, model=None):
        # This method encapsulates the logic that decides what name to give an
        # accessor descriptor that retrieves related many-to-one or
        # many-to-many objects. It uses the lower-cased object_name + "_set",
        # but this can be overridden with the "related_name" option.
        # Due to backwards compatibility ModelForms need to be able to provide
        # an alternate model. See BaseInlineFormSet.get_default_prefix().
        opts = model._meta if model else self.opts
        model = model or self.model
        if self.multiple:
            # If this is a symmetrical m2m relation on self, there is no reverse accessor.
            if self.symmetrical and model == self.to:
                return None
        if self.related_name:
            return self.related_name
        if opts.default_related_name:
            return self.opts.default_related_name % {
                'model_name': self.opts.model_name.lower(),
                'app_label': self.opts.app_label.lower(),
            }
        return opts.model_name + ('_set' if self.multiple else '')

    def get_cache_name(self):
        return "_%s_cache" % self.get_accessor_name()

    def get_path_info(self):
        return self.field.get_reverse_path_info()


class ForeignObject(RelatedField):
    requires_unique_target = True
    generate_reverse_relation = True
    related_accessor_class = ForeignRelatedObjectsDescriptor

    def __init__(self, to, from_fields, to_fields, swappable=True, **kwargs):
        self.from_fields = from_fields
        self.to_fields = to_fields
        self.swappable = swappable

        if 'rel' not in kwargs:
            kwargs['rel'] = ForeignObjectRel(
                self, to,
                related_name=kwargs.pop('related_name', None),
                related_query_name=kwargs.pop('related_query_name', None),
                limit_choices_to=kwargs.pop('limit_choices_to', None),
                parent_link=kwargs.pop('parent_link', False),
                on_delete=kwargs.pop('on_delete', CASCADE),
            )
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)

        super(ForeignObject, self).__init__(**kwargs)

    def check(self, **kwargs):
        errors = super(ForeignObject, self).check(**kwargs)
        errors.extend(self._check_unique_target())
        return errors

    def _check_unique_target(self):
        rel_is_string = isinstance(self.rel.to, six.string_types)
        if rel_is_string or not self.requires_unique_target:
            return []

        # Skip if the
        try:
            self.foreign_related_fields
        except FieldDoesNotExist:
            return []

        try:
            self.rel
        except AttributeError:
            return []

        has_unique_field = any(rel_field.unique
            for rel_field in self.foreign_related_fields)
        if not has_unique_field and len(self.foreign_related_fields) > 1:
            field_combination = ', '.join("'%s'" % rel_field.name
                for rel_field in self.foreign_related_fields)
            model_name = self.rel.to.__name__
            return [
                checks.Error(
                    "None of the fields %s on model '%s' have a unique=True constraint."
                    % (field_combination, model_name),
                    hint=None,
                    obj=self,
                    id='fields.E310',
                )
            ]
        elif not has_unique_field:
            field_name = self.foreign_related_fields[0].name
            model_name = self.rel.to.__name__
            return [
                checks.Error(
                    ("'%s.%s' must set unique=True "
                     "because it is referenced by a foreign key.") % (model_name, field_name),
                    hint=None,
                    obj=self,
                    id='fields.E311',
                )
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super(ForeignObject, self).deconstruct()
        kwargs['from_fields'] = self.from_fields
        kwargs['to_fields'] = self.to_fields
        if self.rel.related_name is not None:
            kwargs['related_name'] = self.rel.related_name
        if self.rel.related_query_name is not None:
            kwargs['related_query_name'] = self.rel.related_query_name
        if self.rel.on_delete != CASCADE:
            kwargs['on_delete'] = self.rel.on_delete
        if self.rel.parent_link:
            kwargs['parent_link'] = self.rel.parent_link
        # Work out string form of "to"
        if isinstance(self.rel.to, six.string_types):
            kwargs['to'] = self.rel.to
        else:
            kwargs['to'] = "%s.%s" % (self.rel.to._meta.app_label, self.rel.to._meta.object_name)
        # If swappable is True, then see if we're actually pointing to the target
        # of a swap.
        swappable_setting = self.swappable_setting
        if swappable_setting is not None:
            # If it's already a settings reference, error
            if hasattr(kwargs['to'], "setting_name"):
                if kwargs['to'].setting_name != swappable_setting:
                    raise ValueError(
                        "Cannot deconstruct a ForeignKey pointing to a model "
                        "that is swapped in place of more than one model (%s and %s)"
                        % (kwargs['to'].setting_name, swappable_setting)
                    )
            # Set it
            from django.db.migrations.writer import SettingsReference
            kwargs['to'] = SettingsReference(
                kwargs['to'],
                swappable_setting,
            )
        return name, path, args, kwargs

    def resolve_related_fields(self):
        if len(self.from_fields) < 1 or len(self.from_fields) != len(self.to_fields):
            raise ValueError('Foreign Object from and to fields must be the same non-zero length')
        if isinstance(self.rel.to, six.string_types):
            raise ValueError('Related model %r cannot be resolved' % self.rel.to)
        related_fields = []
        for index in range(len(self.from_fields)):
            from_field_name = self.from_fields[index]
            to_field_name = self.to_fields[index]
            from_field = (self if from_field_name == 'self'
                          else self.opts.get_field_by_name(from_field_name)[0])
            to_field = (self.rel.to._meta.pk if to_field_name is None
                        else self.rel.to._meta.get_field_by_name(to_field_name)[0])
            related_fields.append((from_field, to_field))
        return related_fields

    @property
    def related_fields(self):
        if not hasattr(self, '_related_fields'):
            self._related_fields = self.resolve_related_fields()
        return self._related_fields

    @property
    def reverse_related_fields(self):
        return [(rhs_field, lhs_field) for lhs_field, rhs_field in self.related_fields]

    @property
    def local_related_fields(self):
        return tuple(lhs_field for lhs_field, rhs_field in self.related_fields)

    @property
    def foreign_related_fields(self):
        return tuple(rhs_field for lhs_field, rhs_field in self.related_fields)

    def get_local_related_value(self, instance):
        return self.get_instance_value_for_fields(instance, self.local_related_fields)

    def get_foreign_related_value(self, instance):
        return self.get_instance_value_for_fields(instance, self.foreign_related_fields)

    @staticmethod
    def get_instance_value_for_fields(instance, fields):
        ret = []
        opts = instance._meta
        for field in fields:
            # Gotcha: in some cases (like fixture loading) a model can have
            # different values in parent_ptr_id and parent's id. So, use
            # instance.pk (that is, parent_ptr_id) when asked for instance.id.
            if field.primary_key:
                possible_parent_link = opts.get_ancestor_link(field.model)
                if (not possible_parent_link or
                        possible_parent_link.primary_key or
                        possible_parent_link.model._meta.abstract):
                    ret.append(instance.pk)
                    continue
            ret.append(getattr(instance, field.attname))
        return tuple(ret)

    def get_attname_column(self):
        attname, column = super(ForeignObject, self).get_attname_column()
        return attname, None

    def get_joining_columns(self, reverse_join=False):
        source = self.reverse_related_fields if reverse_join else self.related_fields
        return tuple((lhs_field.column, rhs_field.column) for lhs_field, rhs_field in source)

    def get_reverse_joining_columns(self):
        return self.get_joining_columns(reverse_join=True)

    def get_extra_descriptor_filter(self, instance):
        """
        Returns an extra filter condition for related object fetching when
        user does 'instance.fieldname', that is the extra filter is used in
        the descriptor of the field.

        The filter should be either a dict usable in .filter(**kwargs) call or
        a Q-object. The condition will be ANDed together with the relation's
        joining columns.

        A parallel method is get_extra_restriction() which is used in
        JOIN and subquery conditions.
        """
        return {}

    def get_extra_restriction(self, where_class, alias, related_alias):
        """
        Returns a pair condition used for joining and subquery pushdown. The
        condition is something that responds to as_sql(compiler, connection)
        method.

        Note that currently referring both the 'alias' and 'related_alias'
        will not work in some conditions, like subquery pushdown.

        A parallel method is get_extra_descriptor_filter() which is used in
        instance.fieldname related object fetching.
        """
        return None

    def get_path_info(self):
        """
        Get path from this field to the related model.
        """
        opts = self.rel.to._meta
        from_opts = self.model._meta
        return [PathInfo(from_opts, opts, self.foreign_related_fields, self, False, True)]

    def get_reverse_path_info(self):
        """
        Get path from the related model to this field's model.
        """
        opts = self.model._meta
        from_opts = self.rel.to._meta
        pathinfos = [PathInfo(from_opts, opts, (opts.pk,), self.rel, not self.unique, False)]
        return pathinfos

    def get_lookup_constraint(self, constraint_class, alias, targets, sources, lookups,
                              raw_value):
        from django.db.models.sql.where import SubqueryConstraint, AND, OR
        root_constraint = constraint_class()
        assert len(targets) == len(sources)
        if len(lookups) > 1:
            raise exceptions.FieldError('Relation fields do not support nested lookups')
        lookup_type = lookups[0]

        def get_normalized_value(value):
            from django.db.models import Model
            if isinstance(value, Model):
                value_list = []
                for source in sources:
                    # Account for one-to-one relations when sent a different model
                    while not isinstance(value, source.model) and source.rel:
                        source = source.rel.to._meta.get_field(source.rel.field_name)
                    value_list.append(getattr(value, source.attname))
                return tuple(value_list)
            elif not isinstance(value, tuple):
                return (value,)
            return value

        is_multicolumn = len(self.related_fields) > 1
        if (hasattr(raw_value, '_as_sql') or
                hasattr(raw_value, 'get_compiler')):
            root_constraint.add(SubqueryConstraint(alias, [target.column for target in targets],
                                                   [source.name for source in sources], raw_value),
                                AND)
        elif lookup_type == 'isnull':
            root_constraint.add(IsNull(Col(alias, targets[0], sources[0]), raw_value), AND)
        elif (lookup_type == 'exact' or (lookup_type in ['gt', 'lt', 'gte', 'lte']
                                         and not is_multicolumn)):
            value = get_normalized_value(raw_value)
            for target, source, val in zip(targets, sources, value):
                lookup_class = target.get_lookup(lookup_type)
                root_constraint.add(
                    lookup_class(Col(alias, target, source), val), AND)
        elif lookup_type in ['range', 'in'] and not is_multicolumn:
            values = [get_normalized_value(value) for value in raw_value]
            value = [val[0] for val in values]
            lookup_class = targets[0].get_lookup(lookup_type)
            root_constraint.add(lookup_class(Col(alias, targets[0], sources[0]), value), AND)
        elif lookup_type == 'in':
            values = [get_normalized_value(value) for value in raw_value]
            for value in values:
                value_constraint = constraint_class()
                for source, target, val in zip(sources, targets, value):
                    lookup_class = target.get_lookup('exact')
                    lookup = lookup_class(Col(alias, target, source), val)
                    value_constraint.add(lookup, AND)
                root_constraint.add(value_constraint, OR)
        else:
            raise TypeError('Related Field got invalid lookup: %s' % lookup_type)
        return root_constraint

    @property
    def attnames(self):
        return tuple(field.attname for field in self.local_related_fields)

    def get_defaults(self):
        return tuple(field.get_default() for field in self.local_related_fields)

    def contribute_to_class(self, cls, name, virtual_only=False):
        super(ForeignObject, self).contribute_to_class(cls, name, virtual_only=virtual_only)
        setattr(cls, self.name, ReverseSingleRelatedObjectDescriptor(self))

    def contribute_to_related_class(self, cls, related):
        # Internal FK's - i.e., those with a related name ending with '+' -
        # and swapped models don't get a related descriptor.
        if not self.rel.is_hidden() and not related.model._meta.swapped:
            setattr(cls, related.get_accessor_name(), self.related_accessor_class(related))
            # While 'limit_choices_to' might be a callable, simply pass
            # it along for later - this is too early because it's still
            # model load time.
            if self.rel.limit_choices_to:
                cls._meta.related_fkey_lookups.append(self.rel.limit_choices_to)
