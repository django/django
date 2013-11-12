"""
Classes allowing "generic" relations through ContentType and object-id fields.
"""
from __future__ import unicode_literals

from collections import defaultdict
from functools import partial

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db import models, router, DEFAULT_DB_ALIAS
from django.db.models import signals
from django.db.models.fields.related import ForeignObject, ForeignObjectRel
from django.db.models.related import PathInfo
from django.db.models.sql.where import Constraint
from django.forms import ModelForm, ALL_FIELDS
from django.forms.models import (BaseModelFormSet, modelformset_factory, save_instance,
    modelform_defines_fields)
from django.contrib.admin.options import InlineModelAdmin, flatten_fieldsets
from django.contrib.contenttypes.models import ContentType
from django.utils import six
from django.utils.deprecation import RenameMethodsBase
from django.utils.encoding import smart_text


class RenameGenericForeignKeyMethods(RenameMethodsBase):
    renamed_methods = (
        ('get_prefetch_query_set', 'get_prefetch_queryset', PendingDeprecationWarning),
    )


class GenericForeignKey(six.with_metaclass(RenameGenericForeignKeyMethods)):
    """
    Provides a generic relation to any object through content-type/object-id
    fields.
    """

    def __init__(self, ct_field="content_type", fk_field="object_id", for_concrete_model=True):
        self.ct_field = ct_field
        self.fk_field = fk_field
        self.for_concrete_model = for_concrete_model
        self.editable = False

    def contribute_to_class(self, cls, name):
        self.name = name
        self.model = cls
        self.cache_attr = "_%s_cache" % name
        cls._meta.add_virtual_field(self)

        # For some reason I don't totally understand, using weakrefs here doesn't work.
        signals.pre_init.connect(self.instance_pre_init, sender=cls, weak=False)

        # Connect myself as the descriptor for this field
        setattr(cls, name, self)

    def instance_pre_init(self, signal, sender, args, kwargs, **_kwargs):
        """
        Handles initializing an object with the generic FK instead of
        content-type/object-id fields.
        """
        if self.name in kwargs:
            value = kwargs.pop(self.name)
            kwargs[self.ct_field] = self.get_content_type(obj=value)
            kwargs[self.fk_field] = value._get_pk_val()

    def get_content_type(self, obj=None, id=None, using=None):
        if obj is not None:
            return ContentType.objects.db_manager(obj._state.db).get_for_model(
                obj, for_concrete_model=self.for_concrete_model)
        elif id:
            return ContentType.objects.db_manager(using).get_for_id(id)
        else:
            # This should never happen. I love comments like this, don't you?
            raise Exception("Impossible arguments to GFK.get_content_type!")

    def get_prefetch_queryset(self, instances):
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
            if ct_id:
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

    def __init__(self, to, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = GenericRel(
            self, to, related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),)
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

    def resolve_related_fields(self):
        self.to_fields = [self.model._meta.pk.name]
        return [(self.rel.to._meta.get_field_by_name(self.object_id_field_name)[0],
                 self.model._meta.pk)]

    def get_reverse_path_info(self):
        opts = self.rel.to._meta
        target = opts.get_field_by_name(self.object_id_field_name)[0]
        return [PathInfo(self.model._meta, opts, (target,), self.rel, True, False)]

    def get_choices_default(self):
        return super(GenericRelation, self).get_choices(include_blank=False)

    def value_to_string(self, obj):
        qs = getattr(obj, self.name).all()
        return smart_text([instance._get_pk_val() for instance in qs])

    def get_joining_columns(self, reverse_join=False):
        if not reverse_join:
            # This error message is meant for the user, and from user
            # perspective this is a reverse join along the GenericRelation.
            raise ValueError('Joining in reverse direction not allowed.')
        return super(GenericRelation, self).get_joining_columns(reverse_join)

    def contribute_to_class(self, cls, name):
        super(GenericRelation, self).contribute_to_class(cls, name, virtual_only=True)
        # Save a reference to which model this class is on for future use
        self.model = cls
        # Add the descriptor for the relation
        setattr(cls, self.name, ReverseGenericRelatedObjectsDescriptor(self, self.for_concrete_model))

    def contribute_to_related_class(self, cls, related):
        pass

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
        field = self.rel.to._meta.get_field_by_name(self.content_type_field_name)[0]
        contenttype_pk = self.get_content_type().pk
        cond = where_class()
        cond.add((Constraint(remote_alias, field.column, field), 'exact', contenttype_pk), 'AND')
        return cond

    def bulk_related_objects(self, objs, using=DEFAULT_DB_ALIAS):
        """
        Return all objects related to ``objs`` via this ``GenericRelation``.

        """
        return self.rel.to._base_manager.db_manager(using).filter(**{
                "%s__pk" % self.content_type_field_name:
                    ContentType.objects.db_manager(using).get_for_model(
                        self.model, for_concrete_model=self.for_concrete_model).pk,
                "%s__in" % self.object_id_field_name:
                    [obj.pk for obj in objs]
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
            model = rel_model,
            instance = instance,
            source_col_name = qn(join_cols[0]),
            target_col_name = qn(join_cols[1]),
            content_type = content_type,
            content_type_field_name = self.field.content_type_field_name,
            object_id_field_name = self.field.object_id_field_name,
            prefetch_cache_name = self.field.attname,
        )

        return manager

    def __set__(self, instance, value):
        manager = self.__get__(instance)
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
                '%s__exact' % object_id_field_name: instance._get_pk_val(),
            }

        def get_queryset(self):
            try:
                return self.instance._prefetched_objects_cache[self.prefetch_cache_name]
            except (AttributeError, KeyError):
                db = self._db or router.db_for_read(self.model, instance=self.instance)
                return super(GenericRelatedObjectManager, self).get_queryset().using(db).filter(**self.core_filters)

        def get_prefetch_queryset(self, instances):
            db = self._db or router.db_for_read(self.model, instance=instances[0])
            query = {
                '%s__pk' % self.content_type_field_name: self.content_type.id,
                '%s__in' % self.object_id_field_name:
                    set(obj._get_pk_val() for obj in instances)
                }
            qs = super(GenericRelatedObjectManager, self).get_queryset().using(db).filter(**query)
            # We (possibly) need to convert object IDs to the type of the
            # instances' PK in order to match up instances:
            object_id_converter = instances[0]._meta.pk.to_python
            return (qs,
                    lambda relobj: object_id_converter(getattr(relobj, self.object_id_field_name)),
                    lambda obj: obj._get_pk_val(),
                    False,
                    self.prefetch_cache_name)

        def add(self, *objs):
            for obj in objs:
                if not isinstance(obj, self.model):
                    raise TypeError("'%s' instance expected" % self.model._meta.object_name)
                setattr(obj, self.content_type_field_name, self.content_type)
                setattr(obj, self.object_id_field_name, self.pk_val)
                obj.save()
        add.alters_data = True

        def remove(self, *objs):
            db = router.db_for_write(self.model, instance=self.instance)
            for obj in objs:
                obj.delete(using=db)
        remove.alters_data = True

        def clear(self):
            db = router.db_for_write(self.model, instance=self.instance)
            for obj in self.all():
                obj.delete(using=db)
        clear.alters_data = True

        def create(self, **kwargs):
            kwargs[self.content_type_field_name] = self.content_type
            kwargs[self.object_id_field_name] = self.pk_val
            db = router.db_for_write(self.model, instance=self.instance)
            return super(GenericRelatedObjectManager, self).using(db).create(**kwargs)
        create.alters_data = True

    return GenericRelatedObjectManager

class GenericRel(ForeignObjectRel):

    def __init__(self, field, to, related_name=None, limit_choices_to=None):
        super(GenericRel, self).__init__(field, to, related_name, limit_choices_to)

class BaseGenericInlineFormSet(BaseModelFormSet):
    """
    A formset for generic inline objects to a parent.
    """

    def __init__(self, data=None, files=None, instance=None, save_as_new=None,
                 prefix=None, queryset=None, **kwargs):
        opts = self.model._meta
        self.instance = instance
        self.rel_name = '-'.join((
            opts.app_label, opts.model_name,
            self.ct_field.name, self.ct_fk_field.name,
        ))
        if self.instance is None or self.instance.pk is None:
            qs = self.model._default_manager.none()
        else:
            if queryset is None:
                queryset = self.model._default_manager
            qs = queryset.filter(**{
                self.ct_field.name: ContentType.objects.get_for_model(
                    self.instance, for_concrete_model=self.for_concrete_model),
                self.ct_fk_field.name: self.instance.pk,
            })
        super(BaseGenericInlineFormSet, self).__init__(
            queryset=qs, data=data, files=files,
            prefix=prefix,
            **kwargs
        )

    @classmethod
    def get_default_prefix(cls):
        opts = cls.model._meta
        return '-'.join((opts.app_label, opts.model_name,
                        cls.ct_field.name, cls.ct_fk_field.name,
        ))

    def save_new(self, form, commit=True):
        kwargs = {
            self.ct_field.get_attname(): ContentType.objects.get_for_model(
                self.instance, for_concrete_model=self.for_concrete_model).pk,
            self.ct_fk_field.get_attname(): self.instance.pk,
        }
        new_obj = self.model(**kwargs)
        return save_instance(form, new_obj, commit=commit)

def generic_inlineformset_factory(model, form=ModelForm,
                                  formset=BaseGenericInlineFormSet,
                                  ct_field="content_type", fk_field="object_id",
                                  fields=None, exclude=None,
                                  extra=3, can_order=False, can_delete=True,
                                  max_num=None,
                                  formfield_callback=None, validate_max=False,
                                  for_concrete_model=True):
    """
    Returns a ``GenericInlineFormSet`` for the given kwargs.

    You must provide ``ct_field`` and ``fk_field`` if they are different from
    the defaults ``content_type`` and ``object_id`` respectively.
    """
    opts = model._meta
    # if there is no field called `ct_field` let the exception propagate
    ct_field = opts.get_field(ct_field)
    if not isinstance(ct_field, models.ForeignKey) or ct_field.rel.to != ContentType:
        raise Exception("fk_name '%s' is not a ForeignKey to ContentType" % ct_field)
    fk_field = opts.get_field(fk_field) # let the exception propagate
    if exclude is not None:
        exclude = list(exclude)
        exclude.extend([ct_field.name, fk_field.name])
    else:
        exclude = [ct_field.name, fk_field.name]
    FormSet = modelformset_factory(model, form=form,
                                   formfield_callback=formfield_callback,
                                   formset=formset,
                                   extra=extra, can_delete=can_delete, can_order=can_order,
                                   fields=fields, exclude=exclude, max_num=max_num,
                                   validate_max=validate_max)
    FormSet.ct_field = ct_field
    FormSet.ct_fk_field = fk_field
    FormSet.for_concrete_model = for_concrete_model
    return FormSet

class GenericInlineModelAdmin(InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"
    formset = BaseGenericInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields(request, obj))
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # GenericInlineModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        exclude = exclude or None
        can_delete = self.can_delete and self.has_delete_permission(request, obj)
        defaults = {
            "ct_field": self.ct_field,
            "fk_field": self.ct_fk_field,
            "form": self.form,
            "formfield_callback": partial(self.formfield_for_dbfield, request=request),
            "formset": self.formset,
            "extra": self.extra,
            "can_delete": can_delete,
            "can_order": False,
            "fields": fields,
            "max_num": self.max_num,
            "exclude": exclude
        }
        defaults.update(kwargs)

        if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
            defaults['fields'] = ALL_FIELDS

        return generic_inlineformset_factory(self.model, **defaults)

class GenericStackedInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'

class GenericTabularInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'
