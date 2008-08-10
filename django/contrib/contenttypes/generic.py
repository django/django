"""
Classes allowing "generic" relations through ContentType and object-id fields.
"""

from django import oldforms
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import signals
from django.db import models
from django.db.models.fields.related import RelatedField, Field, ManyToManyRel
from django.db.models.loading import get_model
from django.utils.functional import curry

from django.forms import ModelForm
from django.forms.models import BaseModelFormSet, modelformset_factory, save_instance
from django.contrib.admin.options import InlineModelAdmin, flatten_fieldsets

class GenericForeignKey(object):
    """
    Provides a generic relation to any object through content-type/object-id
    fields.
    """

    def __init__(self, ct_field="content_type", fk_field="object_id"):
        self.ct_field = ct_field
        self.fk_field = fk_field

    def contribute_to_class(self, cls, name):
        # Make sure the fields exist (these raise FieldDoesNotExist,
        # which is a fine error to raise here)
        self.name = name
        self.model = cls
        self.cache_attr = "_%s_cache" % name

        # For some reason I don't totally understand, using weakrefs here doesn't work.
        signals.pre_init.connect(self.instance_pre_init, sender=cls, weak=False)

        # Connect myself as the descriptor for this field
        setattr(cls, name, self)

    def instance_pre_init(self, signal, sender, args, kwargs, **_kwargs):
        """
        Handles initializing an object with the generic FK instaed of
        content-type/object-id fields.
        """
        if self.name in kwargs:
            value = kwargs.pop(self.name)
            kwargs[self.ct_field] = self.get_content_type(obj=value)
            kwargs[self.fk_field] = value._get_pk_val()

    def get_content_type(self, obj=None, id=None):
        # Convenience function using get_model avoids a circular import when
        # using this model
        ContentType = get_model("contenttypes", "contenttype")
        if obj:
            return ContentType.objects.get_for_model(obj)
        elif id:
            return ContentType.objects.get_for_id(id)
        else:
            # This should never happen. I love comments like this, don't you?
            raise Exception("Impossible arguments to GFK.get_content_type!")

    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError, u"%s must be accessed via instance" % self.name

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
                ct = self.get_content_type(id=ct_id)
                try:
                    rel_obj = ct.get_object_for_this_type(pk=getattr(instance, self.fk_field))
                except ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError, u"%s must be accessed via instance" % self.related.opts.object_name

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

        # By its very nature, a GenericRelation doesn't create a table.
        self.creates_table = False

        # Override content-type/object-id field names on the related class
        self.object_id_field_name = kwargs.pop("object_id_field", "object_id")
        self.content_type_field_name = kwargs.pop("content_type_field", "content_type")

        kwargs['blank'] = True
        kwargs['editable'] = False
        kwargs['serialize'] = False
        Field.__init__(self, **kwargs)

    def get_manipulator_field_objs(self):
        choices = self.get_choices_default()
        return [curry(oldforms.SelectMultipleField, size=min(max(len(choices), 5), 15), choices=choices)]

    def get_choices_default(self):
        return Field.get_choices(self, include_blank=False)

    def flatten_data(self, follow, obj = None):
        new_data = {}
        if obj:
            instance_ids = [instance._get_pk_val() for instance in getattr(obj, self.name).all()]
            new_data[self.name] = instance_ids
        return new_data

    def m2m_db_table(self):
        return self.rel.to._meta.db_table

    def m2m_column_name(self):
        return self.object_id_field_name

    def m2m_reverse_name(self):
        return self.model._meta.pk.column

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

    def db_type(self):
        # Since we're simulating a ManyToManyField, in effect, best return the
        # same db_type as well.
        return None

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
            raise AttributeError, "Manager must be accessed via instance"

        # This import is done here to avoid circular import importing this module
        from django.contrib.contenttypes.models import ContentType

        # Dynamically create a class that subclasses the related model's
        # default manager.
        rel_model = self.field.rel.to
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_generic_related_manager(superclass)

        qn = connection.ops.quote_name

        manager = RelatedManager(
            model = rel_model,
            instance = instance,
            symmetrical = (self.field.rel.symmetrical and instance.__class__ == rel_model),
            join_table = qn(self.field.m2m_db_table()),
            source_col_name = qn(self.field.m2m_column_name()),
            target_col_name = qn(self.field.m2m_reverse_name()),
            content_type = ContentType.objects.get_for_model(self.field.model),
            content_type_field_name = self.field.content_type_field_name,
            object_id_field_name = self.field.object_id_field_name
        )

        return manager

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError, "Manager must be accessed via instance"

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
        def __init__(self, model=None, core_filters=None, instance=None, symmetrical=None,
                     join_table=None, source_col_name=None, target_col_name=None, content_type=None,
                     content_type_field_name=None, object_id_field_name=None):

            super(GenericRelatedObjectManager, self).__init__()
            self.core_filters = core_filters or {}
            self.model = model
            self.content_type = content_type
            self.symmetrical = symmetrical
            self.instance = instance
            self.join_table = join_table
            self.join_table = model._meta.db_table
            self.source_col_name = source_col_name
            self.target_col_name = target_col_name
            self.content_type_field_name = content_type_field_name
            self.object_id_field_name = object_id_field_name
            self.pk_val = self.instance._get_pk_val()

        def get_query_set(self):
            query = {
                '%s__pk' % self.content_type_field_name : self.content_type.id,
                '%s__exact' % self.object_id_field_name : self.pk_val,
            }
            return superclass.get_query_set(self).filter(**query)

        def add(self, *objs):
            for obj in objs:
                setattr(obj, self.content_type_field_name, self.content_type)
                setattr(obj, self.object_id_field_name, self.pk_val)
                obj.save()
        add.alters_data = True

        def remove(self, *objs):
            for obj in objs:
                obj.delete()
        remove.alters_data = True

        def clear(self):
            for obj in self.all():
                obj.delete()
        clear.alters_data = True

        def create(self, **kwargs):
            kwargs[self.content_type_field_name] = self.content_type
            kwargs[self.object_id_field_name] = self.pk_val
            obj = self.model(**kwargs)
            obj.save()
            return obj
        create.alters_data = True

    return GenericRelatedObjectManager

class GenericRel(ManyToManyRel):
    def __init__(self, to, related_name=None, limit_choices_to=None, symmetrical=True):
        self.to = to
        self.related_name = related_name
        self.limit_choices_to = limit_choices_to or {}
        self.edit_inline = False
        self.symmetrical = symmetrical
        self.multiple = True

class BaseGenericInlineFormSet(BaseModelFormSet):
    """
    A formset for generic inline objects to a parent.
    """
    ct_field_name = "content_type"
    ct_fk_field_name = "object_id"
    
    def __init__(self, data=None, files=None, instance=None, save_as_new=None):
        opts = self.model._meta
        self.instance = instance
        self.rel_name = '-'.join((
            opts.app_label, opts.object_name.lower(),
            self.ct_field.name, self.ct_fk_field.name,
        ))
        super(BaseGenericInlineFormSet, self).__init__(
            queryset=self.get_queryset(), data=data, files=files,
            prefix=self.rel_name
        )

    def get_queryset(self):
        # Avoid a circular import.
        from django.contrib.contenttypes.models import ContentType
        if self.instance is None:
            return self.model._default_manager.empty()
        return self.model._default_manager.filter(**{
            self.ct_field.name: ContentType.objects.get_for_model(self.instance),
            self.ct_fk_field.name: self.instance.pk,
        })

    def save_new(self, form, commit=True):
        # Avoid a circular import.
        from django.contrib.contenttypes.models import ContentType
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
                                  max_num=0,
                                  formfield_callback=lambda f: f.formfield()):
    """
    Returns an ``GenericInlineFormSet`` for the given kwargs.

    You must provide ``ct_field`` and ``object_id`` if they different from the
    defaults ``content_type`` and ``object_id`` respectively.
    """
    opts = model._meta
    # Avoid a circular import.
    from django.contrib.contenttypes.models import ContentType
    # if there is no field called `ct_field` let the exception propagate
    ct_field = opts.get_field(ct_field)
    if not isinstance(ct_field, models.ForeignKey) or ct_field.rel.to != ContentType:
        raise Exception("fk_name '%s' is not a ForeignKey to ContentType" % ct_field)
    fk_field = opts.get_field(fk_field) # let the exception propagate
    if exclude is not None:
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

    def get_formset(self, request, obj=None):
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        defaults = {
            "ct_field": self.ct_field,
            "fk_field": self.ct_fk_field,
            "form": self.form,
            "formfield_callback": self.formfield_for_dbfield,
            "formset": self.formset,
            "extra": self.extra,
            "can_delete": True,
            "can_order": False,
            "fields": fields,
        }
        return generic_inlineformset_factory(self.model, **defaults)

class GenericStackedInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'

class GenericTabularInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'

