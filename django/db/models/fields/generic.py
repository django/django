"""
Classes allowing "generic" relations through ContentType and object-id fields.
"""

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db import backend
from django.db.models import signals
from django.db.models.fields.related import RelatedField, Field, ManyToManyRel
from django.db.models.loading import get_model
from django.dispatch import dispatcher
from django.utils.functional import curry

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
        dispatcher.connect(self.instance_pre_init, signal=signals.pre_init, sender=cls, weak=False)

        # Connect myself as the descriptor for this field
        setattr(cls, name, self)

    def instance_pre_init(self, signal, sender, args, kwargs):
        # Handle initalizing an object with the generic FK instaed of 
        # content-type/object-id fields.        
        if kwargs.has_key(self.name):
            value = kwargs.pop(self.name)
            kwargs[self.ct_field] = self.get_content_type(value)
            kwargs[self.fk_field] = value._get_pk_val()
            
    def get_content_type(self, obj):
        # Convenience function using get_model avoids a circular import when using this model
        ContentType = get_model("contenttypes", "contenttype")
        return ContentType.objects.get_for_model(obj)
        
    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError, "%s must be accessed via instance" % self.name

        try:
            return getattr(instance, self.cache_attr)
        except AttributeError:
            rel_obj = None
            ct = getattr(instance, self.ct_field)
            if ct:
                try:
                    rel_obj = ct.get_object_for_this_type(pk=getattr(instance, self.fk_field))
                except ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError, "%s must be accessed via instance" % self.related.opts.object_name

        ct = None
        fk = None
        if value is not None:
            ct = self.get_content_type(value)
            fk = value._get_pk_val()

        setattr(instance, self.ct_field, ct)
        setattr(instance, self.fk_field, fk)
        setattr(instance, self.cache_attr, value)
    
class GenericRelation(RelatedField, Field):
    """Provides an accessor to generic related objects (i.e. comments)"""

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
        Field.__init__(self, **kwargs)

    def get_manipulator_field_objs(self):
        choices = self.get_choices_default()
        return [curry(forms.SelectMultipleField, size=min(max(len(choices), 5), 15), choices=choices)]

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
        return self.object_id_field_name

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

        manager = RelatedManager(
            model = rel_model,
            instance = instance,
            symmetrical = (self.field.rel.symmetrical and instance.__class__ == rel_model),
            join_table = backend.quote_name(self.field.m2m_db_table()),
            source_col_name = backend.quote_name(self.field.m2m_column_name()),
            target_col_name = backend.quote_name(self.field.m2m_reverse_name()),
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
        self.num_in_admin = 0
        self.related_name = related_name
        self.filter_interface = None
        self.limit_choices_to = limit_choices_to or {}
        self.edit_inline = False
        self.raw_id_admin = False
        self.symmetrical = symmetrical
        self.multiple = True
        assert not (self.raw_id_admin and self.filter_interface), \
            "Generic relations may not use both raw_id_admin and filter_interface"
