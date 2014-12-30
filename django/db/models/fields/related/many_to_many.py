from django import forms
from django.apps import apps
from django.core import checks
from django.db import router, transaction, connections, connection
from django.db.backends import utils
from django.db.models import signals, Q, QuerySet
from django.db.models.fields import Field, FieldDoesNotExist
from django.db.models.fields.related.base import (
    add_lazy_relation, ForeignObjectRel, RECURSIVE_RELATIONSHIP_CONSTANT, RelatedField)
from django.utils import six
from django.utils.encoding import smart_text
from django.utils.functional import cached_property, curry
from django.utils.translation import ugettext_lazy as _


def create_many_to_many_intermediary_model(field, klass):
    from django.db import models
    managed = True
    if isinstance(field.rel.to, six.string_types) and field.rel.to != RECURSIVE_RELATIONSHIP_CONSTANT:
        to_model = field.rel.to
        to = to_model.split('.')[-1]

        def set_managed(field, model, cls):
            field.rel.through._meta.managed = model._meta.managed or cls._meta.managed
        add_lazy_relation(klass, field, to_model, set_managed)
    elif isinstance(field.rel.to, six.string_types):
        to = klass._meta.object_name
        to_model = klass
        managed = klass._meta.managed
    else:
        to = field.rel.to._meta.object_name
        to_model = field.rel.to
        managed = klass._meta.managed or to_model._meta.managed
    name = '%s_%s' % (klass._meta.object_name, field.name)
    if field.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT or to == klass._meta.object_name:
        from_ = 'from_%s' % to.lower()
        to = 'to_%s' % to.lower()
    else:
        from_ = klass._meta.model_name
        to = to.lower()
    meta = type(str('Meta'), (object,), {
        'db_table': field._get_m2m_db_table(klass._meta),
        'managed': managed,
        'auto_created': klass,
        'app_label': klass._meta.app_label,
        'db_tablespace': klass._meta.db_tablespace,
        'unique_together': (from_, to),
        'verbose_name': '%(from)s-%(to)s relationship' % {'from': from_, 'to': to},
        'verbose_name_plural': '%(from)s-%(to)s relationships' % {'from': from_, 'to': to},
        'apps': field.model._meta.apps,
    })
    # Construct and return the new class.
    return type(str(name), (models.Model,), {
        'Meta': meta,
        '__module__': klass.__module__,
        from_: models.ForeignKey(
            klass,
            related_name='%s+' % name,
            db_tablespace=field.db_tablespace,
            db_constraint=field.rel.db_constraint,
        ),
        to: models.ForeignKey(
            to_model,
            related_name='%s+' % name,
            db_tablespace=field.db_tablespace,
            db_constraint=field.rel.db_constraint,
        )
    })


def create_many_related_manager(superclass, rel):
    """Creates a manager that subclasses 'superclass' (which is a Manager)
    and adds behavior for many-to-many related objects."""
    class ManyRelatedManager(superclass):
        def __init__(self, model=None, query_field_name=None, instance=None, symmetrical=None,
                     source_field_name=None, target_field_name=None, reverse=False,
                     through=None, prefetch_cache_name=None):
            super(ManyRelatedManager, self).__init__()
            self.model = model
            self.query_field_name = query_field_name

            source_field = through._meta.get_field(source_field_name)
            source_related_fields = source_field.related_fields

            self.core_filters = {}
            for lh_field, rh_field in source_related_fields:
                self.core_filters['%s__%s' % (query_field_name, rh_field.name)] = getattr(instance, rh_field.attname)

            self.instance = instance
            self.symmetrical = symmetrical
            self.source_field = source_field
            self.target_field = through._meta.get_field(target_field_name)
            self.source_field_name = source_field_name
            self.target_field_name = target_field_name
            self.reverse = reverse
            self.through = through
            self.prefetch_cache_name = prefetch_cache_name
            self.related_val = source_field.get_foreign_related_value(instance)
            if None in self.related_val:
                raise ValueError('"%r" needs to have a value for field "%s" before '
                                 'this many-to-many relationship can be used.' %
                                 (instance, source_field_name))
            # Even if this relation is not to pk, we require still pk value.
            # The wish is that the instance has been already saved to DB,
            # although having a pk value isn't a guarantee of that.
            if instance.pk is None:
                raise ValueError("%r instance needs to have a primary key value before "
                                 "a many-to-many relationship can be used." %
                                 instance.__class__.__name__)

        def __call__(self, **kwargs):
            # We use **kwargs rather than a kwarg argument to enforce the
            # `manager='manager_name'` syntax.
            manager = getattr(self.model, kwargs.pop('manager'))
            manager_class = create_many_related_manager(manager.__class__, rel)
            return manager_class(
                model=self.model,
                query_field_name=self.query_field_name,
                instance=self.instance,
                symmetrical=self.symmetrical,
                source_field_name=self.source_field_name,
                target_field_name=self.target_field_name,
                reverse=self.reverse,
                through=self.through,
                prefetch_cache_name=self.prefetch_cache_name,
            )
        do_not_call_in_templates = True

        def _build_remove_filters(self, removed_vals):
            filters = Q(**{self.source_field_name: self.related_val})
            # No need to add a subquery condition if removed_vals is a QuerySet without
            # filters.
            removed_vals_filters = (not isinstance(removed_vals, QuerySet) or
                                    removed_vals._has_filters())
            if removed_vals_filters:
                filters &= Q(**{'%s__in' % self.target_field_name: removed_vals})
            if self.symmetrical:
                symmetrical_filters = Q(**{self.target_field_name: self.related_val})
                if removed_vals_filters:
                    symmetrical_filters &= Q(
                        **{'%s__in' % self.source_field_name: removed_vals})
                filters |= symmetrical_filters
            return filters

        def get_queryset(self):
            try:
                return self.instance._prefetched_objects_cache[self.prefetch_cache_name]
            except (AttributeError, KeyError):
                qs = super(ManyRelatedManager, self).get_queryset()
                qs._add_hints(instance=self.instance)
                if self._db:
                    qs = qs.using(self._db)
                return qs._next_is_sticky().filter(**self.core_filters)

        def get_prefetch_queryset(self, instances, queryset=None):
            if queryset is None:
                queryset = super(ManyRelatedManager, self).get_queryset()

            queryset._add_hints(instance=instances[0])
            queryset = queryset.using(queryset._db or self._db)

            query = {'%s__in' % self.query_field_name: instances}
            queryset = queryset._next_is_sticky().filter(**query)

            # M2M: need to annotate the query in order to get the primary model
            # that the secondary model was actually related to. We know that
            # there will already be a join on the join table, so we can just add
            # the select.

            # For non-autocreated 'through' models, can't assume we are
            # dealing with PK values.
            fk = self.through._meta.get_field(self.source_field_name)
            join_table = self.through._meta.db_table
            connection = connections[queryset.db]
            qn = connection.ops.quote_name
            queryset = queryset.extra(select={
                '_prefetch_related_val_%s' % f.attname:
                '%s.%s' % (qn(join_table), qn(f.column)) for f in fk.local_related_fields})
            return (
                queryset,
                lambda result: tuple(
                    getattr(result, '_prefetch_related_val_%s' % f.attname)
                    for f in fk.local_related_fields
                ),
                lambda inst: tuple(getattr(inst, f.attname) for f in fk.foreign_related_fields),
                False,
                self.prefetch_cache_name,
            )

        def add(self, *objs):
            if not rel.through._meta.auto_created:
                opts = self.through._meta
                raise AttributeError(
                    "Cannot use add() on a ManyToManyField which specifies an "
                    "intermediary model. Use %s.%s's Manager instead." %
                    (opts.app_label, opts.object_name)
                )

            db = router.db_for_write(self.through, instance=self.instance)
            with transaction.atomic(using=db, savepoint=False):
                self._add_items(self.source_field_name, self.target_field_name, *objs)

                # If this is a symmetrical m2m relation to self, add the mirror entry in the m2m table
                if self.symmetrical:
                    self._add_items(self.target_field_name, self.source_field_name, *objs)
        add.alters_data = True

        def remove(self, *objs):
            if not rel.through._meta.auto_created:
                opts = self.through._meta
                raise AttributeError(
                    "Cannot use remove() on a ManyToManyField which specifies "
                    "an intermediary model. Use %s.%s's Manager instead." %
                    (opts.app_label, opts.object_name)
                )
            self._remove_items(self.source_field_name, self.target_field_name, *objs)
        remove.alters_data = True

        def clear(self):
            db = router.db_for_write(self.through, instance=self.instance)
            with transaction.atomic(using=db, savepoint=False):
                signals.m2m_changed.send(sender=self.through, action="pre_clear",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=None, using=db)

                filters = self._build_remove_filters(super(ManyRelatedManager, self).get_queryset().using(db))
                self.through._default_manager.using(db).filter(filters).delete()

                signals.m2m_changed.send(sender=self.through, action="post_clear",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=None, using=db)
        clear.alters_data = True

        def create(self, **kwargs):
            # This check needs to be done here, since we can't later remove this
            # from the method lookup table, as we do with add and remove.
            if not self.through._meta.auto_created:
                opts = self.through._meta
                raise AttributeError(
                    "Cannot use create() on a ManyToManyField which specifies "
                    "an intermediary model. Use %s.%s's Manager instead." %
                    (opts.app_label, opts.object_name)
                )
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            new_obj = super(ManyRelatedManager, self.db_manager(db)).create(**kwargs)
            self.add(new_obj)
            return new_obj
        create.alters_data = True

        def get_or_create(self, **kwargs):
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            obj, created = super(ManyRelatedManager, self.db_manager(db)).get_or_create(**kwargs)
            # We only need to add() if created because if we got an object back
            # from get() then the relationship already exists.
            if created:
                self.add(obj)
            return obj, created
        get_or_create.alters_data = True

        def update_or_create(self, **kwargs):
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            obj, created = super(ManyRelatedManager, self.db_manager(db)).update_or_create(**kwargs)
            # We only need to add() if created because if we got an object back
            # from get() then the relationship already exists.
            if created:
                self.add(obj)
            return obj, created
        update_or_create.alters_data = True

        def _add_items(self, source_field_name, target_field_name, *objs):
            # source_field_name: the PK fieldname in join table for the source object
            # target_field_name: the PK fieldname in join table for the target object
            # *objs - objects to add. Either object instances, or primary keys of object instances.

            # If there aren't any objects, there is nothing to do.
            from django.db.models import Model
            if objs:
                new_ids = set()
                for obj in objs:
                    if isinstance(obj, self.model):
                        if not router.allow_relation(obj, self.instance):
                            raise ValueError(
                                'Cannot add "%r": instance is on database "%s", value is on database "%s"' %
                                (obj, self.instance._state.db, obj._state.db)
                            )
                        fk_val = self.through._meta.get_field(
                            target_field_name).get_foreign_related_value(obj)[0]
                        if fk_val is None:
                            raise ValueError(
                                'Cannot add "%r": the value for field "%s" is None' %
                                (obj, target_field_name)
                            )
                        new_ids.add(fk_val)
                    elif isinstance(obj, Model):
                        raise TypeError(
                            "'%s' instance expected, got %r" %
                            (self.model._meta.object_name, obj)
                        )
                    else:
                        new_ids.add(obj)

                db = router.db_for_write(self.through, instance=self.instance)
                vals = (self.through._default_manager.using(db)
                        .values_list(target_field_name, flat=True)
                        .filter(**{
                            source_field_name: self.related_val[0],
                            '%s__in' % target_field_name: new_ids,
                        }))
                new_ids = new_ids - set(vals)

                with transaction.atomic(using=db, savepoint=False):
                    if self.reverse or source_field_name == self.source_field_name:
                        # Don't send the signal when we are inserting the
                        # duplicate data row for symmetrical reverse entries.
                        signals.m2m_changed.send(sender=self.through, action='pre_add',
                            instance=self.instance, reverse=self.reverse,
                            model=self.model, pk_set=new_ids, using=db)

                    # Add the ones that aren't there already
                    self.through._default_manager.using(db).bulk_create([
                        self.through(**{
                            '%s_id' % source_field_name: self.related_val[0],
                            '%s_id' % target_field_name: obj_id,
                        })
                        for obj_id in new_ids
                    ])

                    if self.reverse or source_field_name == self.source_field_name:
                        # Don't send the signal when we are inserting the
                        # duplicate data row for symmetrical reverse entries.
                        signals.m2m_changed.send(sender=self.through, action='post_add',
                            instance=self.instance, reverse=self.reverse,
                            model=self.model, pk_set=new_ids, using=db)

        def _remove_items(self, source_field_name, target_field_name, *objs):
            # source_field_name: the PK colname in join table for the source object
            # target_field_name: the PK colname in join table for the target object
            # *objs - objects to remove
            if not objs:
                return

            # Check that all the objects are of the right type
            old_ids = set()
            for obj in objs:
                if isinstance(obj, self.model):
                    fk_val = self.target_field.get_foreign_related_value(obj)[0]
                    old_ids.add(fk_val)
                else:
                    old_ids.add(obj)

            db = router.db_for_write(self.through, instance=self.instance)
            with transaction.atomic(using=db, savepoint=False):
                # Send a signal to the other end if need be.
                signals.m2m_changed.send(sender=self.through, action="pre_remove",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=old_ids, using=db)
                target_model_qs = super(ManyRelatedManager, self).get_queryset()
                if target_model_qs._has_filters():
                    old_vals = target_model_qs.using(db).filter(**{
                        '%s__in' % self.target_field.related_field.attname: old_ids})
                else:
                    old_vals = old_ids
                filters = self._build_remove_filters(old_vals)
                self.through._default_manager.using(db).filter(filters).delete()

                signals.m2m_changed.send(sender=self.through, action="post_remove",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=old_ids, using=db)

    return ManyRelatedManager


class ManyRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField pointed at them by
    # some other model (rather than having a ManyToManyField themselves).
    # In the example "publication.article_set", the article_set attribute is a
    # ManyRelatedObjectsDescriptor instance.
    def __init__(self, related):
        self.related = related   # RelatedObject instance

    @cached_property
    def related_manager_cls(self):
        # Dynamically create a class that subclasses the related
        # model's default manager.
        return create_many_related_manager(
            self.related.model._default_manager.__class__,
            self.related.field.rel
        )

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        rel_model = self.related.model

        manager = self.related_manager_cls(
            model=rel_model,
            query_field_name=self.related.field.name,
            prefetch_cache_name=self.related.field.related_query_name(),
            instance=instance,
            symmetrical=False,
            source_field_name=self.related.field.m2m_reverse_field_name(),
            target_field_name=self.related.field.m2m_field_name(),
            reverse=True,
            through=self.related.field.rel.through,
        )

        return manager

    def __set__(self, instance, value):
        if not self.related.field.rel.through._meta.auto_created:
            opts = self.related.field.rel.through._meta
            raise AttributeError(
                "Cannot set values on a ManyToManyField which specifies an "
                "intermediary model. Use %s.%s's Manager instead." % (opts.app_label, opts.object_name)
            )

        # Force evaluation of `value` in case it's a queryset whose
        # value could be affected by `manager.clear()`. Refs #19816.
        value = tuple(value)

        manager = self.__get__(instance)
        db = router.db_for_write(manager.through, instance=manager.instance)
        with transaction.atomic(using=db, savepoint=False):
            manager.clear()
            manager.add(*value)


class ReverseManyRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField defined in their
    # model (rather than having another model pointed *at* them).
    # In the example "article.publications", the publications attribute is a
    # ReverseManyRelatedObjectsDescriptor instance.
    def __init__(self, m2m_field):
        self.field = m2m_field

    @property
    def through(self):
        # through is provided so that you have easy access to the through
        # model (Book.authors.through) for inlines, etc. This is done as
        # a property to ensure that the fully resolved value is returned.
        return self.field.rel.through

    @cached_property
    def related_manager_cls(self):
        # Dynamically create a class that subclasses the related model's
        # default manager.
        return create_many_related_manager(
            self.field.rel.to._default_manager.__class__,
            self.field.rel
        )

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        manager = self.related_manager_cls(
            model=self.field.rel.to,
            query_field_name=self.field.related_query_name(),
            prefetch_cache_name=self.field.name,
            instance=instance,
            symmetrical=self.field.rel.symmetrical,
            source_field_name=self.field.m2m_field_name(),
            target_field_name=self.field.m2m_reverse_field_name(),
            reverse=False,
            through=self.field.rel.through,
        )

        return manager

    def __set__(self, instance, value):
        if not self.field.rel.through._meta.auto_created:
            opts = self.field.rel.through._meta
            raise AttributeError(
                "Cannot set values on a ManyToManyField which specifies an "
                "intermediary model.  Use %s.%s's Manager instead." % (opts.app_label, opts.object_name)
            )

        # Force evaluation of `value` in case it's a queryset whose
        # value could be affected by `manager.clear()`. Refs #19816.
        value = tuple(value)

        manager = self.__get__(instance)
        db = router.db_for_write(manager.through, instance=manager.instance)
        with transaction.atomic(using=db, savepoint=False):
            manager.clear()
            manager.add(*value)


class ManyToManyRel(ForeignObjectRel):
    def __init__(self, field, to, related_name=None, limit_choices_to=None,
                 symmetrical=True, through=None, through_fields=None,
                 db_constraint=True, related_query_name=None):
        if through and not db_constraint:
            raise ValueError("Can't supply a through model and db_constraint=False")
        if through_fields and not through:
            raise ValueError("Cannot specify through_fields without a through model")
        super(ManyToManyRel, self).__init__(
            field, to, related_name=related_name,
            limit_choices_to=limit_choices_to, related_query_name=related_query_name)
        self.symmetrical = symmetrical
        self.multiple = True
        self.through = through
        self.through_fields = through_fields
        self.db_constraint = db_constraint

    def get_related_field(self):
        """
        Returns the field in the 'to' object to which this relationship is tied.
        Provided for symmetry with ManyToOneRel.
        """
        opts = self.through._meta
        if self.through_fields:
            field = opts.get_field(self.through_fields[0])
        else:
            for field in opts.fields:
                rel = getattr(field, 'rel', None)
                if rel and rel.to == self.to:
                    break
        return field.foreign_related_fields[0]


class ManyToManyField(RelatedField):
    description = _("Many-to-many relationship")

    def __init__(self, to, db_constraint=True, swappable=True, **kwargs):
        try:
            to._meta
        except AttributeError:  # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, six.string_types), (
                "%s(%r) is invalid. First parameter to ManyToManyField must be "
                "either a model, a model name, or the string %r" %
                (self.__class__.__name__, to, RECURSIVE_RELATIONSHIP_CONSTANT)
            )
            # Class names must be ASCII in Python 2.x, so we forcibly coerce it
            # here to break early if there's a problem.
            to = str(to)

        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = ManyToManyRel(
            self, to,
            related_name=kwargs.pop('related_name', None),
            related_query_name=kwargs.pop('related_query_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            symmetrical=kwargs.pop('symmetrical', to == RECURSIVE_RELATIONSHIP_CONSTANT),
            through=kwargs.pop('through', None),
            through_fields=kwargs.pop('through_fields', None),
            db_constraint=db_constraint,
        )

        self.swappable = swappable
        self.db_table = kwargs.pop('db_table', None)
        if kwargs['rel'].through is not None:
            assert self.db_table is None, "Cannot specify a db_table if an intermediary model is used."

        super(ManyToManyField, self).__init__(**kwargs)

    def check(self, **kwargs):
        errors = super(ManyToManyField, self).check(**kwargs)
        errors.extend(self._check_unique(**kwargs))
        errors.extend(self._check_relationship_model(**kwargs))
        errors.extend(self._check_ignored_options(**kwargs))
        return errors

    def _check_unique(self, **kwargs):
        if self.unique:
            return [
                checks.Error(
                    'ManyToManyFields cannot be unique.',
                    hint=None,
                    obj=self,
                    id='fields.E330',
                )
            ]
        return []

    def _check_ignored_options(self, **kwargs):
        warnings = []

        if self.null:
            warnings.append(
                checks.Warning(
                    'null has no effect on ManyToManyField.',
                    hint=None,
                    obj=self,
                    id='fields.W340',
                )
            )

        if len(self._validators) > 0:
            warnings.append(
                checks.Warning(
                    'ManyToManyField does not support validators.',
                    hint=None,
                    obj=self,
                    id='fields.W341',
                )
            )

        return warnings

    def _check_relationship_model(self, from_model=None, **kwargs):
        if hasattr(self.rel.through, '_meta'):
            qualified_model_name = "%s.%s" % (
                self.rel.through._meta.app_label, self.rel.through.__name__)
        else:
            qualified_model_name = self.rel.through

        errors = []

        if self.rel.through not in apps.get_models(include_auto_created=True):
            # The relationship model is not installed.
            errors.append(
                checks.Error(
                    ("Field specifies a many-to-many relation through model "
                     "'%s', which has not been installed.") %
                    qualified_model_name,
                    hint=None,
                    obj=self,
                    id='fields.E331',
                )
            )

        else:

            assert from_model is not None, \
                "ManyToManyField with intermediate " \
                "tables cannot be checked if you don't pass the model " \
                "where the field is attached to."

            # Set some useful local variables
            to_model = self.rel.to
            from_model_name = from_model._meta.object_name
            if isinstance(to_model, six.string_types):
                to_model_name = to_model
            else:
                to_model_name = to_model._meta.object_name
            relationship_model_name = self.rel.through._meta.object_name
            self_referential = from_model == to_model

            # Check symmetrical attribute.
            if (self_referential and self.rel.symmetrical and
                    not self.rel.through._meta.auto_created):
                errors.append(
                    checks.Error(
                        'Many-to-many fields with intermediate tables must not be symmetrical.',
                        hint=None,
                        obj=self,
                        id='fields.E332',
                    )
                )

            # Count foreign keys in intermediate model
            if self_referential:
                seen_self = sum(from_model == getattr(field.rel, 'to', None)
                    for field in self.rel.through._meta.fields)

                if seen_self > 2 and not self.rel.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than two foreign keys "
                             "to '%s', which is ambiguous. You must specify "
                             "which two foreign keys Django should use via the "
                             "through_fields keyword argument.") % (self, from_model_name),
                            hint=("Use through_fields to specify which two "
                                  "foreign keys Django should use."),
                            obj=self.rel.through,
                            id='fields.E333',
                        )
                    )

            else:
                # Count foreign keys in relationship model
                seen_from = sum(from_model == getattr(field.rel, 'to', None)
                    for field in self.rel.through._meta.fields)
                seen_to = sum(to_model == getattr(field.rel, 'to', None)
                    for field in self.rel.through._meta.fields)

                if seen_from > 1 and not self.rel.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than one foreign key "
                             "from '%s', which is ambiguous. You must specify "
                             "which foreign key Django should use via the "
                             "through_fields keyword argument.") % (self, from_model_name),
                            hint=('If you want to create a recursive relationship, '
                                  'use ForeignKey("self", symmetrical=False, '
                                  'through="%s").') % relationship_model_name,
                            obj=self,
                            id='fields.E334',
                        )
                    )

                if seen_to > 1 and not self.rel.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than one foreign key "
                             "to '%s', which is ambiguous. You must specify "
                             "which foreign key Django should use via the "
                             "through_fields keyword argument.") % (self, to_model_name),
                            hint=('If you want to create a recursive '
                                  'relationship, use ForeignKey("self", '
                                  'symmetrical=False, through="%s").') % relationship_model_name,
                            obj=self,
                            id='fields.E335',
                        )
                    )

                if seen_from == 0 or seen_to == 0:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it does not have a foreign key to '%s' or '%s'.") % (
                                self, from_model_name, to_model_name
                            ),
                            hint=None,
                            obj=self.rel.through,
                            id='fields.E336',
                        )
                    )

        # Validate `through_fields`
        if self.rel.through_fields is not None:
            # Validate that we're given an iterable of at least two items
            # and that none of them is "falsy"
            if not (len(self.rel.through_fields) >= 2 and
                    self.rel.through_fields[0] and self.rel.through_fields[1]):
                errors.append(
                    checks.Error(
                        ("Field specifies 'through_fields' but does not "
                         "provide the names of the two link fields that should be "
                         "used for the relation through model "
                         "'%s'.") % qualified_model_name,
                        hint=("Make sure you specify 'through_fields' as "
                              "through_fields=('field1', 'field2')"),
                        obj=self,
                        id='fields.E337',
                    )
                )

            # Validate the given through fields -- they should be actual
            # fields on the through model, and also be foreign keys to the
            # expected models
            else:
                assert from_model is not None, \
                    "ManyToManyField with intermediate " \
                    "tables cannot be checked if you don't pass the model " \
                    "where the field is attached to."

                source, through, target = from_model, self.rel.through, self.rel.to
                source_field_name, target_field_name = self.rel.through_fields[:2]

                for field_name, related_model in ((source_field_name, source),
                                                  (target_field_name, target)):

                    possible_field_names = []
                    for f in through._meta.fields:
                        if hasattr(f, 'rel') and getattr(f.rel, 'to', None) == related_model:
                            possible_field_names.append(f.name)
                    if possible_field_names:
                        hint = ("Did you mean one of the following foreign "
                                "keys to '%s': %s?") % (related_model._meta.object_name,
                                                        ', '.join(possible_field_names))
                    else:
                        hint = None

                    try:
                        field = through._meta.get_field(field_name)
                    except FieldDoesNotExist:
                        errors.append(
                            checks.Error(
                                ("The intermediary model '%s' has no field '%s'.") % (
                                    qualified_model_name, field_name),
                                hint=hint,
                                obj=self,
                                id='fields.E338',
                            )
                        )
                    else:
                        if not (hasattr(field, 'rel') and
                                getattr(field.rel, 'to', None) == related_model):
                            errors.append(
                                checks.Error(
                                    "'%s.%s' is not a foreign key to '%s'." % (
                                        through._meta.object_name, field_name,
                                        related_model._meta.object_name),
                                    hint=hint,
                                    obj=self,
                                    id='fields.E339',
                                )
                            )

        return errors

    def deconstruct(self):
        name, path, args, kwargs = super(ManyToManyField, self).deconstruct()
        # Handle the simpler arguments
        if self.db_table is not None:
            kwargs['db_table'] = self.db_table
        if self.rel.db_constraint is not True:
            kwargs['db_constraint'] = self.rel.db_constraint
        if self.rel.related_name is not None:
            kwargs['related_name'] = self.rel.related_name
        if self.rel.related_query_name is not None:
            kwargs['related_query_name'] = self.rel.related_query_name
        # Rel needs more work.
        if isinstance(self.rel.to, six.string_types):
            kwargs['to'] = self.rel.to
        else:
            kwargs['to'] = "%s.%s" % (self.rel.to._meta.app_label, self.rel.to._meta.object_name)
        if getattr(self.rel, 'through', None) is not None:
            if isinstance(self.rel.through, six.string_types):
                kwargs['through'] = self.rel.through
            elif not self.rel.through._meta.auto_created:
                kwargs['through'] = "%s.%s" % (self.rel.through._meta.app_label, self.rel.through._meta.object_name)
        # If swappable is True, then see if we're actually pointing to the target
        # of a swap.
        swappable_setting = self.swappable_setting
        if swappable_setting is not None:
            # If it's already a settings reference, error
            if hasattr(kwargs['to'], "setting_name"):
                if kwargs['to'].setting_name != swappable_setting:
                    raise ValueError(
                        "Cannot deconstruct a ManyToManyField pointing to a "
                        "model that is swapped in place of more than one model "
                        "(%s and %s)" % (kwargs['to'].setting_name, swappable_setting)
                    )
            # Set it
            from django.db.migrations.writer import SettingsReference
            kwargs['to'] = SettingsReference(
                kwargs['to'],
                swappable_setting,
            )
        return name, path, args, kwargs

    def _get_path_info(self, direct=False):
        """
        Called by both direct and indirect m2m traversal.
        """
        pathinfos = []
        int_model = self.rel.through
        linkfield1 = int_model._meta.get_field_by_name(self.m2m_field_name())[0]
        linkfield2 = int_model._meta.get_field_by_name(self.m2m_reverse_field_name())[0]
        if direct:
            join1infos = linkfield1.get_reverse_path_info()
            join2infos = linkfield2.get_path_info()
        else:
            join1infos = linkfield2.get_reverse_path_info()
            join2infos = linkfield1.get_path_info()
        pathinfos.extend(join1infos)
        pathinfos.extend(join2infos)
        return pathinfos

    def get_path_info(self):
        return self._get_path_info(direct=True)

    def get_reverse_path_info(self):
        return self._get_path_info(direct=False)

    def get_choices_default(self):
        return Field.get_choices(self, include_blank=False)

    def _get_m2m_db_table(self, opts):
        "Function that can be curried to provide the m2m table name for this relation"
        if self.rel.through is not None:
            return self.rel.through._meta.db_table
        elif self.db_table:
            return self.db_table
        else:
            return utils.truncate_name('%s_%s' % (opts.db_table, self.name),
                                      connection.ops.max_name_length())

    def _get_m2m_attr(self, related, attr):
        "Function that can be curried to provide the source accessor or DB column name for the m2m table"
        cache_attr = '_m2m_%s_cache' % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        if self.rel.through_fields is not None:
            link_field_name = self.rel.through_fields[0]
        else:
            link_field_name = None
        for f in self.rel.through._meta.fields:
            if hasattr(f, 'rel') and f.rel and f.rel.to == related.model and \
                    (link_field_name is None or link_field_name == f.name):
                setattr(self, cache_attr, getattr(f, attr))
                return getattr(self, cache_attr)

    def _get_m2m_reverse_attr(self, related, attr):
        "Function that can be curried to provide the related accessor or DB column name for the m2m table"
        cache_attr = '_m2m_reverse_%s_cache' % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        found = False
        if self.rel.through_fields is not None:
            link_field_name = self.rel.through_fields[1]
        else:
            link_field_name = None
        for f in self.rel.through._meta.fields:
            if hasattr(f, 'rel') and f.rel and f.rel.to == related.parent_model:
                if link_field_name is None and related.model == related.parent_model:
                    # If this is an m2m-intermediate to self,
                    # the first foreign key you find will be
                    # the source column. Keep searching for
                    # the second foreign key.
                    if found:
                        setattr(self, cache_attr, getattr(f, attr))
                        break
                    else:
                        found = True
                elif link_field_name is None or link_field_name == f.name:
                    setattr(self, cache_attr, getattr(f, attr))
                    break
        return getattr(self, cache_attr)

    def value_to_string(self, obj):
        data = ''
        if obj:
            qs = getattr(obj, self.name).all()
            data = [instance._get_pk_val() for instance in qs]
        else:
            # In required many-to-many fields with only one available choice,
            # select that one available choice.
            if not self.blank:
                choices_list = self.get_choices_default()
                if len(choices_list) == 1:
                    data = [choices_list[0][0]]
        return smart_text(data)

    def contribute_to_class(self, cls, name, **kwargs):
        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.rel.symmetrical and (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name

        super(ManyToManyField, self).contribute_to_class(cls, name, **kwargs)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        #  3) The class owning the m2m field has been swapped out.
        if not self.rel.through and not cls._meta.abstract and not cls._meta.swapped:
            self.rel.through = create_many_to_many_intermediary_model(self, cls)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseManyRelatedObjectsDescriptor(self))

        # Set up the accessor for the m2m table name for the relation
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

        # Populate some necessary rel arguments so that cross-app relations
        # work correctly.
        if isinstance(self.rel.through, six.string_types):
            def resolve_through_model(field, model, cls):
                field.rel.through = model
            add_lazy_relation(cls, self, self.rel.through, resolve_through_model)

    def contribute_to_related_class(self, cls, related):
        # Internal M2Ms (i.e., those with a related name ending with '+')
        # and swapped models don't get a related descriptor.
        if not self.rel.is_hidden() and not related.model._meta.swapped:
            setattr(cls, related.get_accessor_name(), ManyRelatedObjectsDescriptor(related))

        # Set up the accessors for the column names on the m2m table
        self.m2m_column_name = curry(self._get_m2m_attr, related, 'column')
        self.m2m_reverse_name = curry(self._get_m2m_reverse_attr, related, 'column')

        self.m2m_field_name = curry(self._get_m2m_attr, related, 'name')
        self.m2m_reverse_field_name = curry(self._get_m2m_reverse_attr, related, 'name')

        get_m2m_rel = curry(self._get_m2m_attr, related, 'rel')
        self.m2m_target_field_name = lambda: get_m2m_rel().field_name
        get_m2m_reverse_rel = curry(self._get_m2m_reverse_attr, related, 'rel')
        self.m2m_reverse_target_field_name = lambda: get_m2m_reverse_rel().field_name

    def set_attributes_from_rel(self):
        pass

    def value_from_object(self, obj):
        "Returns the value of this field in the given model instance."
        return getattr(obj, self.attname).all()

    def save_form_data(self, instance, data):
        setattr(instance, self.attname, data)

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        defaults = {
            'form_class': forms.ModelMultipleChoiceField,
            'queryset': self.rel.to._default_manager.using(db),
        }
        defaults.update(kwargs)
        # If initial is passed in, it's a list of related objects, but the
        # MultipleChoiceField takes a list of IDs.
        if defaults.get('initial') is not None:
            initial = defaults['initial']
            if callable(initial):
                initial = initial()
            defaults['initial'] = [i._get_pk_val() for i in initial]
        return super(ManyToManyField, self).formfield(**defaults)

    def db_type(self, connection):
        # A ManyToManyField is not represented by a single column,
        # so return None.
        return None

    def db_parameters(self, connection):
        return {"type": None, "check": None}
