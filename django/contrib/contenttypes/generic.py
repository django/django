"""
Classes allowing "generic" relations through ContentType and object-id fields.
"""
from __future__ import unicode_literals

from collections import defaultdict
from functools import partial

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import signals
from django.db import models, router, DEFAULT_DB_ALIAS
from django.db.models.fields.related import RelatedField, Field, ManyToManyRel
from django.db.models.related import PathInfo
from django.forms import ModelForm
from django.forms.models import BaseModelFormSet, modelformset_factory, save_instance
from django.contrib.admin.options import InlineModelAdmin, flatten_fieldsets
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_text


class GenericForeignKey(object):
    """
    Provides a generic relation to any object through content-type/object-id
    fields.
    """

    def __init__(self, ct_field="content_type", fk_field="object_id"):
        self.ct_field = ct_field
        self.fk_field = fk_field

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
            return ContentType.objects.db_manager(obj._state.db).get_for_model(obj)
        elif id:
            return ContentType.objects.db_manager(using).get_for_id(id)
        else:
            # This should never happen. I love comments like this, don't you?
            raise Exception("Impossible arguments to GFK.get_content_type!")

    def get_prefetch_query_set(self, instances):
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
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.related.opts.object_name)

        ct = None
        fk = None
        if value is not None:
            ct = self.get_content_type(obj=value)
            fk = value._get_pk_val()

        setattr(instance, self.ct_field, ct)
        setattr(instance, self.fk_field, fk)
        setattr(instance, self.cache_attr, value)

class GenericRelation(RelatedField, Field):
    """Provides an accessor to generic related objects (e.g. comments)"""

    def __init__(self, to, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = GenericRel(to,
                            related_name=kwargs.pop('related_name', None),
                            limit_choices_to=kwargs.pop('limit_choices_to', None),
                            symmetrical=kwargs.pop('symmetrical', True))


        # Override content-type/object-id field names on the related class
        self.object_id_field_name = kwargs.pop("object_id_field", "object_id")
        self.content_type_field_name = kwargs.pop("content_type_field", "content_type")

        kwargs['blank'] = True
        kwargs['editable'] = False
        kwargs['serialize'] = False
        Field.__init__(self, **kwargs)

    def get_path_info(self):
        from_field = self.model._meta.pk
        opts = self.rel.to._meta
        target = opts.get_field_by_name(self.object_id_field_name)[0]
        # Note that we are using different field for the join_field
        # than from_field or to_field. This is a hack, but we need the
        # GenericRelation to generate the extra SQL.
        return ([PathInfo(from_field, target, self.model._meta, opts, self, True, False)],
                opts, target, self)

    def get_choices_default(self):
        return Field.get_choices(self, include_blank=False)

    def value_to_string(self, obj):
        qs = getattr(obj, self.name).all()
        return smart_text([instance._get_pk_val() for instance in qs])

    def m2m_db_table(self):
        return self.rel.to._meta.db_table

    def m2m_column_name(self):
        return self.object_id_field_name

    def m2m_reverse_name(self):
        return self.rel.to._meta.pk.column

    def m2m_target_field_name(self):
        return self.model._meta.pk.name

    def m2m_reverse_target_field_name(self):
        return self.rel.to._meta.pk.name

    def contribute_to_class(self, cls, name):
        super(GenericRelation, self).contribute_to_class(cls, name)

        # Save a reference to which model this class is on for future use
        self.model = cls

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseGenericRelatedObjectsDescriptor(self))

    def contribute_to_related_class(self, cls, related):
        pass

    def set_attributes_from_rel(self):
        pass

    def get_internal_type(self):
        return "ManyToManyField"

    def db_type(self, connection):
        # Since we're simulating a ManyToManyField, in effect, best return the
        # same db_type as well.
        return None

    def get_content_type(self):
        """
        Returns the content type associated with this field's model.
        """
        return ContentType.objects.get_for_model(self.model)

    def get_extra_join_sql(self, connection, qn, lhs_alias, rhs_alias):
        extra_col = self.rel.to._meta.get_field_by_name(self.content_type_field_name)[0].column
        contenttype = self.get_content_type().pk
        return " AND %s.%s = %%s" % (qn(rhs_alias), qn(extra_col)), [contenttype]

    def bulk_related_objects(self, objs, using=DEFAULT_DB_ALIAS):
        """
        Return all objects related to ``objs`` via this ``GenericRelation``.

        """
        return self.rel.to._base_manager.db_manager(using).filter(**{
                "%s__pk" % self.content_type_field_name:
                    ContentType.objects.db_manager(using).get_for_model(self.model).pk,
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
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        # Dynamically create a class that subclasses the related model's
        # default manager.
        rel_model = self.field.rel.to
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_generic_related_manager(superclass)

        qn = connection.ops.quote_name
        content_type = ContentType.objects.db_manager(instance._state.db).get_for_model(instance)

        manager = RelatedManager(
            model = rel_model,
            instance = instance,
            symmetrical = (self.field.rel.symmetrical and instance.__class__ == rel_model),
            source_col_name = qn(self.field.m2m_column_name()),
            target_col_name = qn(self.field.m2m_reverse_name()),
            content_type = content_type,
            content_type_field_name = self.field.content_type_field_name,
            object_id_field_name = self.field.object_id_field_name,
            prefetch_cache_name = self.field.attname,
        )

        return manager

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

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

        def get_query_set(self):
            try:
                return self.instance._prefetched_objects_cache[self.prefetch_cache_name]
            except (AttributeError, KeyError):
                db = self._db or router.db_for_read(self.model, instance=self.instance)
                return super(GenericRelatedObjectManager, self).get_query_set().using(db).filter(**self.core_filters)

        def get_prefetch_query_set(self, instances):
            db = self._db or router.db_for_read(self.model, instance=instances[0])
            query = {
                '%s__pk' % self.content_type_field_name: self.content_type.id,
                '%s__in' % self.object_id_field_name:
                    set(obj._get_pk_val() for obj in instances)
                }
            qs = super(GenericRelatedObjectManager, self).get_query_set().using(db).filter(**query)
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

class GenericRel(ManyToManyRel):
    def __init__(self, to, related_name=None, limit_choices_to=None, symmetrical=True):
        self.to = to
        self.related_name = related_name
        self.limit_choices_to = limit_choices_to or {}
        self.symmetrical = symmetrical
        self.multiple = True
        self.through = None

class BaseGenericInlineFormSet(BaseModelFormSet):
    """
    A formset for generic inline objects to a parent.
    """

    def __init__(self, data=None, files=None, instance=None, save_as_new=None,
                 prefix=None, queryset=None):
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
                self.ct_field.name: ContentType.objects.get_for_model(self.instance),
                self.ct_fk_field.name: self.instance.pk,
            })
        super(BaseGenericInlineFormSet, self).__init__(
            queryset=qs, data=data, files=files,
            prefix=prefix
        )

    @classmethod
    def get_default_prefix(cls):
        opts = cls.model._meta
        return '-'.join((opts.app_label, opts.model_name,
                        cls.ct_field.name, cls.ct_fk_field.name,
        ))

    def save_new(self, form, commit=True):
        kwargs = {
            self.ct_field.get_attname(): ContentType.objects.get_for_model(self.instance).pk,
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
                                  formfield_callback=None):
    """
    Returns a ``GenericInlineFormSet`` for the given kwargs.

    You must provide ``ct_field`` and ``object_id`` if they different from the
    defaults ``content_type`` and ``object_id`` respectively.
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
                                   fields=fields, exclude=exclude, max_num=max_num)
    FormSet.ct_field = ct_field
    FormSet.ct_fk_field = fk_field
    return FormSet

class GenericInlineModelAdmin(InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"
    formset = BaseGenericInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
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
        return generic_inlineformset_factory(self.model, **defaults)

class GenericStackedInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'

class GenericTabularInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'
