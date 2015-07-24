from __future__ import unicode_literals

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import DEFAULT_DB_ALIAS, connection, models, router, transaction
from django.db.models import DO_NOTHING, signals
from django.db.models.base import ModelBase
from django.db.models.fields.related import ForeignObject, ForeignObjectRel
from django.db.models.query_utils import PathInfo
from django.utils.encoding import python_2_unicode_compatible, smart_text


@python_2_unicode_compatible
class GenericForeignKey(object):
    """
    Provides a generic relation to any object through content-type/object-id
    fields.
    """
    # Field flags
    auto_created = False
    concrete = False
    editable = False
    hidden = False

    is_relation = True
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False
    related_model = None

    # For backwards compatibility; ignored as of Django 1.8.4.
    allow_unsaved_instance_assignment = False

    def __init__(self, ct_field="content_type", fk_field="object_id", for_concrete_model=True):
        self.ct_field = ct_field
        self.fk_field = fk_field
        self.for_concrete_model = for_concrete_model
        self.editable = False
        self.rel = None
        self.column = None

    def contribute_to_class(self, cls, name, **kwargs):
        self.name = name
        self.model = cls
        self.cache_attr = "_%s_cache" % name
        cls._meta.add_field(self, virtual=True)

        # Only run pre-initialization field assignment on non-abstract models
        if not cls._meta.abstract:
            signals.pre_init.connect(self.instance_pre_init, sender=cls)

        setattr(cls, name, self)

    def __str__(self):
        model = self.model
        app = model._meta.app_label
        return '%s.%s.%s' % (app, model._meta.object_name, self.name)

    def check(self, **kwargs):
        errors = []
        errors.extend(self._check_field_name())
        errors.extend(self._check_object_id_field())
        errors.extend(self._check_content_type_field())
        return errors

    def _check_field_name(self):
        if self.name.endswith("_"):
            return [
                checks.Error(
                    'Field names must not end with an underscore.',
                    hint=None,
                    obj=self,
                    id='fields.E001',
                )
            ]
        else:
            return []

    def _check_object_id_field(self):
        try:
            self.model._meta.get_field(self.fk_field)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The GenericForeignKey object ID references the non-existent field '%s'." % self.fk_field,
                    hint=None,
                    obj=self,
                    id='contenttypes.E001',
                )
            ]
        else:
            return []

    def _check_content_type_field(self):
        """ Check if field named `field_name` in model `model` exists and is
        valid content_type field (is a ForeignKey to ContentType). """

        try:
            field = self.model._meta.get_field(self.ct_field)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "The GenericForeignKey content type references the non-existent field '%s.%s'." % (
                        self.model._meta.object_name, self.ct_field
                    ),
                    hint=None,
                    obj=self,
                    id='contenttypes.E002',
                )
            ]
        else:
            if not isinstance(field, models.ForeignKey):
                return [
                    checks.Error(
                        "'%s.%s' is not a ForeignKey." % (
                            self.model._meta.object_name, self.ct_field
                        ),
                        hint=(
                            "GenericForeignKeys must use a ForeignKey to "
                            "'contenttypes.ContentType' as the 'content_type' field."
                        ),
                        obj=self,
                        id='contenttypes.E003',
                    )
                ]
            elif field.rel.to != ContentType:
                return [
                    checks.Error(
                        "'%s.%s' is not a ForeignKey to 'contenttypes.ContentType'." % (
                            self.model._meta.object_name, self.ct_field
                        ),
                        hint=(
                            "GenericForeignKeys must use a ForeignKey to "
                            "'contenttypes.ContentType' as the 'content_type' field."
                        ),
                        obj=self,
                        id='contenttypes.E004',
                    )
                ]
            else:
                return []

    def instance_pre_init(self, signal, sender, args, kwargs, **_kwargs):
        """
        Handles initializing an object with the generic FK instead of
        content-type/object-id fields.
        """
        if self.name in kwargs:
            value = kwargs.pop(self.name)
            if value is not None:
                kwargs[self.ct_field] = self.get_content_type(obj=value)
                kwargs[self.fk_field] = value._get_pk_val()
            else:
                kwargs[self.ct_field] = None
                kwargs[self.fk_field] = None

    def get_content_type(self, obj=None, id=None, using=None):
        if obj is not None:
            return ContentType.objects.db_manager(obj._state.db).get_for_model(
                obj, for_concrete_model=self.for_concrete_model)
        elif id is not None:
            return ContentType.objects.db_manager(using).get_for_id(id)
        else:
            # This should never happen. I love comments like this, don't you?
            raise Exception("Impossible arguments to GFK.get_content_type!")

    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is not None:
            raise ValueError("Custom queryset can't be used for this lookup.")

        # For efficiency, group the instances by content type and then do one
        # query per model
        fk_dict = defaultdict(set)
        # We need one instance for each group in order to get the right db:
        instance_dict = {}
        ct_attname = self.model._meta.get_field(self.ct_field).get_attname()
        for instance in instances:
            # We avoid looking for values if either ct_id or fkey value is None
            ct_id = getattr(instance, ct_attname)
            if ct_id is not None:
                fk_val = getattr(instance, self.fk_field)
                if fk_val is not None:
                    fk_dict[ct_id].add(fk_val)
                    instance_dict[ct_id] = instance

        ret_val = []
        for ct_id, fkeys in fk_dict.items():
            instance = instance_dict[ct_id]
            ct = self.get_content_type(id=ct_id, using=instance._state.db)
            ret_val.extend(ct.get_all_objects_for_this_type(pk__in=fkeys))

        # For doing the join in Python, we have to match both the FK val and the
        # content type, so we use a callable that returns a (fk, class) pair.
        def gfk_key(obj):
            ct_id = getattr(obj, ct_attname)
            if ct_id is None:
                return None
            else:
                model = self.get_content_type(id=ct_id,
                                              using=obj._state.db).model_class()
                return (model._meta.pk.get_prep_value(getattr(obj, self.fk_field)),
                        model)

        return (ret_val,
                lambda obj: (obj._get_pk_val(), obj.__class__),
                gfk_key,
                True,
                self.cache_attr)

    def is_cached(self, instance):
        return hasattr(instance, self.cache_attr)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        try:
            return getattr(instance, self.cache_attr)
        except AttributeError:
            rel_obj = None

            # Make sure to use ContentType.objects.get_for_id() to ensure that
            # lookups are cached (see ticket #5570). This takes more code than
            # the naive ``getattr(instance, self.ct_field)``, but has better
            # performance when dealing with GFKs in loops and such.
            f = self.model._meta.get_field(self.ct_field)
            ct_id = getattr(instance, f.get_attname(), None)
            if ct_id is not None:
                ct = self.get_content_type(id=ct_id, using=instance._state.db)
                try:
                    rel_obj = ct.get_object_for_this_type(pk=getattr(instance, self.fk_field))
                except ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        ct = None
        fk = None
        if value is not None:
            ct = self.get_content_type(obj=value)
            fk = value._get_pk_val()

        setattr(instance, self.ct_field, ct)
        setattr(instance, self.fk_field, fk)
        setattr(instance, self.cache_attr, value)


class GenericRelation(ForeignObject):
    """Provides an accessor to generic related objects (e.g. comments)"""
    # Field flags
    auto_created = False

    many_to_many = False
    many_to_one = False
    one_to_many = True
    one_to_one = False

    def __init__(self, to, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = GenericRel(
            self, to,
            related_query_name=kwargs.pop('related_query_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
        )
        # Override content-type/object-id field names on the related class
        self.object_id_field_name = kwargs.pop("object_id_field", "object_id")
        self.content_type_field_name = kwargs.pop("content_type_field", "content_type")

        self.for_concrete_model = kwargs.pop("for_concrete_model", True)

        kwargs['blank'] = True
        kwargs['editable'] = False
        kwargs['serialize'] = False
        # This construct is somewhat of an abuse of ForeignObject. This field
        # represents a relation from pk to object_id field. But, this relation
        # isn't direct, the join is generated reverse along foreign key. So,
        # the from_field is object_id field, to_field is pk because of the
        # reverse join.
        super(GenericRelation, self).__init__(
            to, to_fields=[],
            from_fields=[self.object_id_field_name], **kwargs)

    def check(self, **kwargs):
        errors = super(GenericRelation, self).check(**kwargs)
        errors.extend(self._check_generic_foreign_key_existence())
        return errors

    def _check_generic_foreign_key_existence(self):
        target = self.rel.to
        if isinstance(target, ModelBase):
            # Using `vars` is very ugly approach, but there is no better one,
            # because GenericForeignKeys are not considered as fields and,
            # therefore, are not included in `target._meta.local_fields`.
            fields = target._meta.virtual_fields
            if any(isinstance(field, GenericForeignKey) and
                    field.ct_field == self.content_type_field_name and
                    field.fk_field == self.object_id_field_name
                    for field in fields):
                return []
            else:
                return [
                    checks.Error(
                        ("The GenericRelation defines a relation with the model "
                         "'%s.%s', but that model does not have a GenericForeignKey.") % (
                            target._meta.app_label, target._meta.object_name
                        ),
                        hint=None,
                        obj=self,
                        id='contenttypes.E004',
                    )
                ]
        else:
            return []

    def resolve_related_fields(self):
        self.to_fields = [self.model._meta.pk.name]
        return [(self.rel.to._meta.get_field(self.object_id_field_name), self.model._meta.pk)]

    def get_path_info(self):
        opts = self.rel.to._meta
        target = opts.pk
        return [PathInfo(self.model._meta, opts, (target,), self.rel, True, False)]

    def get_reverse_path_info(self):
        opts = self.model._meta
        from_opts = self.rel.to._meta
        return [PathInfo(from_opts, opts, (opts.pk,), self, not self.unique, False)]

    def get_choices_default(self):
        return super(GenericRelation, self).get_choices(include_blank=False)

    def value_to_string(self, obj):
        qs = getattr(obj, self.name).all()
        return smart_text([instance._get_pk_val() for instance in qs])

    def contribute_to_class(self, cls, name, **kwargs):
        kwargs['virtual_only'] = True
        super(GenericRelation, self).contribute_to_class(cls, name, **kwargs)
        # Save a reference to which model this class is on for future use
        self.model = cls
        # Add the descriptor for the relation
        setattr(cls, self.name, ReverseGenericRelatedObjectsDescriptor(self, self.for_concrete_model))

    def set_attributes_from_rel(self):
        pass

    def get_internal_type(self):
        return "ManyToManyField"

    def get_content_type(self):
        """
        Returns the content type associated with this field's model.
        """
        return ContentType.objects.get_for_model(self.model,
                                                 for_concrete_model=self.for_concrete_model)

    def get_extra_restriction(self, where_class, alias, remote_alias):
        field = self.rel.to._meta.get_field(self.content_type_field_name)
        contenttype_pk = self.get_content_type().pk
        cond = where_class()
        lookup = field.get_lookup('exact')(field.get_col(remote_alias), contenttype_pk)
        cond.add(lookup, 'AND')
        return cond

    def bulk_related_objects(self, objs, using=DEFAULT_DB_ALIAS):
        """
        Return all objects related to ``objs`` via this ``GenericRelation``.

        """
        return self.rel.to._base_manager.db_manager(using).filter(**{
            "%s__pk" % self.content_type_field_name: ContentType.objects.db_manager(using).get_for_model(
                self.model, for_concrete_model=self.for_concrete_model).pk,
            "%s__in" % self.object_id_field_name: [obj.pk for obj in objs]
        })


class ReverseGenericRelatedObjectsDescriptor(object):
    """
    This class provides the functionality that makes the related-object
    managers available as attributes on a model class, for fields that have
    multiple "remote" values and have a GenericRelation defined in their model
    (rather than having another model pointed *at* them). In the example
    "article.publications", the publications attribute is a
    ReverseGenericRelatedObjectsDescriptor instance.
    """
    def __init__(self, field, for_concrete_model=True):
        self.field = field
        self.for_concrete_model = for_concrete_model

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        # Dynamically create a class that subclasses the related model's
        # default manager.
        rel_model = self.field.rel.to
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_generic_related_manager(superclass)

        qn = connection.ops.quote_name
        content_type = ContentType.objects.db_manager(instance._state.db).get_for_model(
            instance, for_concrete_model=self.for_concrete_model)

        join_cols = self.field.get_joining_columns(reverse_join=True)[0]
        manager = RelatedManager(
            model=rel_model,
            instance=instance,
            source_col_name=qn(join_cols[0]),
            target_col_name=qn(join_cols[1]),
            content_type=content_type,
            content_type_field_name=self.field.content_type_field_name,
            object_id_field_name=self.field.object_id_field_name,
            prefetch_cache_name=self.field.attname,
        )

        return manager

    def __set__(self, instance, value):
        # Force evaluation of `value` in case it's a queryset whose
        # value could be affected by `manager.clear()`. Refs #19816.
        value = tuple(value)

        manager = self.__get__(instance)
        db = router.db_for_write(manager.model, instance=manager.instance)
        with transaction.atomic(using=db, savepoint=False):
            manager.clear()
            for obj in value:
                manager.add(obj)


def create_generic_related_manager(superclass):
    """
    Factory function for a manager that subclasses 'superclass' (which is a
    Manager) and adds behavior for generic related objects.
    """

    class GenericRelatedObjectManager(superclass):
        def __init__(self, model=None, instance=None, symmetrical=None,
                     source_col_name=None, target_col_name=None, content_type=None,
                     content_type_field_name=None, object_id_field_name=None,
                     prefetch_cache_name=None):

            super(GenericRelatedObjectManager, self).__init__()
            self.model = model
            self.content_type = content_type
            self.symmetrical = symmetrical
            self.instance = instance
            self.source_col_name = source_col_name
            self.target_col_name = target_col_name
            self.content_type_field_name = content_type_field_name
            self.object_id_field_name = object_id_field_name
            self.prefetch_cache_name = prefetch_cache_name
            self.pk_val = self.instance._get_pk_val()
            self.core_filters = {
                '%s__pk' % content_type_field_name: content_type.id,
                '%s' % object_id_field_name: instance._get_pk_val(),
            }

        def __call__(self, **kwargs):
            # We use **kwargs rather than a kwarg argument to enforce the
            # `manager='manager_name'` syntax.
            manager = getattr(self.model, kwargs.pop('manager'))
            manager_class = create_generic_related_manager(manager.__class__)
            return manager_class(
                model=self.model,
                instance=self.instance,
                symmetrical=self.symmetrical,
                source_col_name=self.source_col_name,
                target_col_name=self.target_col_name,
                content_type=self.content_type,
                content_type_field_name=self.content_type_field_name,
                object_id_field_name=self.object_id_field_name,
                prefetch_cache_name=self.prefetch_cache_name,
            )
        do_not_call_in_templates = True

        def __str__(self):
            return repr(self)

        def get_queryset(self):
            try:
                return self.instance._prefetched_objects_cache[self.prefetch_cache_name]
            except (AttributeError, KeyError):
                db = self._db or router.db_for_read(self.model, instance=self.instance)
                return super(GenericRelatedObjectManager, self).get_queryset().using(db).filter(**self.core_filters)

        def get_prefetch_queryset(self, instances, queryset=None):
            if queryset is None:
                queryset = super(GenericRelatedObjectManager, self).get_queryset()

            queryset._add_hints(instance=instances[0])
            queryset = queryset.using(queryset._db or self._db)

            query = {
                '%s__pk' % self.content_type_field_name: self.content_type.id,
                '%s__in' % self.object_id_field_name: set(obj._get_pk_val() for obj in instances)
            }

            # We (possibly) need to convert object IDs to the type of the
            # instances' PK in order to match up instances:
            object_id_converter = instances[0]._meta.pk.to_python
            return (queryset.filter(**query),
                    lambda relobj: object_id_converter(getattr(relobj, self.object_id_field_name)),
                    lambda obj: obj._get_pk_val(),
                    False,
                    self.prefetch_cache_name)

        def add(self, *objs):
            db = router.db_for_write(self.model, instance=self.instance)
            with transaction.atomic(using=db, savepoint=False):
                for obj in objs:
                    if not isinstance(obj, self.model):
                        raise TypeError("'%s' instance expected" % self.model._meta.object_name)
                    setattr(obj, self.content_type_field_name, self.content_type)
                    setattr(obj, self.object_id_field_name, self.pk_val)
                    obj.save()
        add.alters_data = True

        def remove(self, *objs, **kwargs):
            if not objs:
                return
            bulk = kwargs.pop('bulk', True)
            self._clear(self.filter(pk__in=[o.pk for o in objs]), bulk)
        remove.alters_data = True

        def clear(self, **kwargs):
            bulk = kwargs.pop('bulk', True)
            self._clear(self, bulk)
        clear.alters_data = True

        def _clear(self, queryset, bulk):
            db = router.db_for_write(self.model, instance=self.instance)
            queryset = queryset.using(db)
            if bulk:
                # `QuerySet.delete()` creates its own atomic block which
                # contains the `pre_delete` and `post_delete` signal handlers.
                queryset.delete()
            else:
                with transaction.atomic(using=db, savepoint=False):
                    for obj in queryset:
                        obj.delete()
        _clear.alters_data = True

        def create(self, **kwargs):
            kwargs[self.content_type_field_name] = self.content_type
            kwargs[self.object_id_field_name] = self.pk_val
            db = router.db_for_write(self.model, instance=self.instance)
            return super(GenericRelatedObjectManager, self).using(db).create(**kwargs)
        create.alters_data = True

        def get_or_create(self, **kwargs):
            kwargs[self.content_type_field_name] = self.content_type
            kwargs[self.object_id_field_name] = self.pk_val
            db = router.db_for_write(self.model, instance=self.instance)
            return super(GenericRelatedObjectManager, self).using(db).get_or_create(**kwargs)
        get_or_create.alters_data = True

        def update_or_create(self, **kwargs):
            kwargs[self.content_type_field_name] = self.content_type
            kwargs[self.object_id_field_name] = self.pk_val
            db = router.db_for_write(self.model, instance=self.instance)
            return super(GenericRelatedObjectManager, self).using(db).update_or_create(**kwargs)
        update_or_create.alters_data = True

    return GenericRelatedObjectManager


class GenericRel(ForeignObjectRel):
    def __init__(self, field, to, related_name=None, limit_choices_to=None, related_query_name=None):
        super(GenericRel, self).__init__(field=field, to=to, related_name=related_query_name or '+',
                                         limit_choices_to=limit_choices_to, on_delete=DO_NOTHING,
                                         related_query_name=related_query_name)
