"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from forms import BaseForm, DeclarativeFieldsMetaclass, SortedDictFromList
from fields import ChoiceField, MultipleChoiceField
from widgets import Select, SelectMultiple

__all__ = ('save_instance', 'form_for_model', 'form_for_instance', 'form_for_fields',
           'ModelChoiceField', 'ModelMultipleChoiceField')

def model_save(self, commit=True):
    """
    Creates and returns model instance according to self.clean_data.

    This method is created for any form_for_model Form.
    """
    if self.errors:
        raise ValueError("The %s could not be created because the data didn't validate." % self._model._meta.object_name)
    return save_instance(self, self._model(), commit)

def save_instance(form, instance, commit=True):
    """
    Saves bound Form ``form``'s clean_data into model instance ``instance``.

    Assumes ``form`` has a field for every non-AutoField database field in
    ``instance``. If commit=True, then the changes to ``instance`` will be
    saved to the database. Returns ``instance``.
    """
    from django.db import models
    opts = instance.__class__._meta
    if form.errors:
        raise ValueError("The %s could not be changed because the data didn't validate." % opts.object_name)
    clean_data = form.clean_data
    for f in opts.fields:
        if isinstance(f, models.AutoField):
            continue
        setattr(instance, f.name, clean_data[f.name])
    if commit:
        instance.save()
        for f in opts.many_to_many:
            setattr(instance, f.attname, clean_data[f.name])
    # GOTCHA: If many-to-many data is given and commit=False, the many-to-many
    # data will be lost. This happens because a many-to-many options cannot be
    # set on an object until after it's saved. Maybe we should raise an
    # exception in that case.
    return instance

def make_instance_save(instance):
    "Returns the save() method for a form_for_instance Form."
    def save(self, commit=True):
        return save_instance(self, instance, commit)
    return save

def form_for_model(model, form=BaseForm, formfield_callback=lambda f: f.formfield()):
    """
    Returns a Form class for the given Django model class.

    Provide ``form`` if you want to use a custom BaseForm subclass.

    Provide ``formfield_callback`` if you want to define different logic for
    determining the formfield for a given database field. It's a callable that
    takes a database Field instance and returns a form Field instance.
    """
    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        formfield = formfield_callback(f)
        if formfield:
            field_list.append((f.name, formfield))
    fields = SortedDictFromList(field_list)
    return type(opts.object_name + 'Form', (form,), {'base_fields': fields, '_model': model, 'save': model_save})

def form_for_instance(instance, form=BaseForm, formfield_callback=lambda f, **kwargs: f.formfield(**kwargs)):
    """
    Returns a Form class for the given Django model instance.

    Provide ``form`` if you want to use a custom BaseForm subclass.

    Provide ``formfield_callback`` if you want to define different logic for
    determining the formfield for a given database field. It's a callable that
    takes a database Field instance, plus **kwargs, and returns a form Field
    instance with the given kwargs (i.e. 'initial').
    """
    model = instance.__class__
    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        current_value = f.value_from_object(instance)
        formfield = formfield_callback(f, initial=current_value)
        if formfield:
            field_list.append((f.name, formfield))
    fields = SortedDictFromList(field_list)
    return type(opts.object_name + 'InstanceForm', (form,),
        {'base_fields': fields, '_model': model, 'save': make_instance_save(instance)})

def form_for_fields(field_list):
    "Returns a Form class for the given list of Django database field instances."
    fields = SortedDictFromList([(f.name, f.formfield()) for f in field_list])
    return type('FormForFields', (BaseForm,), {'base_fields': fields})

class ModelChoiceField(ChoiceField):
    "A ChoiceField whose choices are a model QuerySet."
    def __init__(self, queryset, empty_label=u"---------", **kwargs):
        self.model = queryset.model
        choices = [(obj._get_pk_val(), str(obj)) for obj in queryset]
        if empty_label is not None:
            choices = [(u"", empty_label)] + choices
        ChoiceField.__init__(self, choices=choices, **kwargs)

    def clean(self, value):
        value = ChoiceField.clean(self, value)
        if not value:
            return None
        try:
            value = self.model._default_manager.get(pk=value)
        except self.model.DoesNotExist:
            raise ValidationError(gettext(u'Select a valid choice. That choice is not one of the available choices.'))
        return value

class ModelMultipleChoiceField(MultipleChoiceField):
    "A MultipleChoiceField whose choices are a model QuerySet."
    def __init__(self, queryset, **kwargs):
        self.model = queryset.model
        MultipleChoiceField.__init__(self, choices=[(obj._get_pk_val(), str(obj)) for obj in queryset], **kwargs)

    def clean(self, value):
        value = MultipleChoiceField.clean(self, value)
        if not value:
            return []
        return self.model._default_manager.filter(pk__in=value)
