"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from forms import BaseForm, DeclarativeFieldsMetaclass, SortedDictFromList

__all__ = ('save_instance', 'form_for_model', 'form_for_instance', 'form_for_fields')

def model_save(self, commit=True):
    """
    Creates and returns model instance according to self.clean_data.

    This method is created for any form_for_model Form.
    """
    if self.errors:
        raise ValueError("The %s could not be created because the data didn't validate." % self._model._meta.object_name)
    obj = self._model(**self.clean_data)
    if commit:
        obj.save()
    return obj

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
    for f in opts.fields + opts.many_to_many:
        if isinstance(f, models.AutoField):
            continue
        setattr(instance, f.attname, clean_data[f.name])
    if commit:
        instance.save()
    return instance

def make_instance_save(instance):
    "Returns the save() method for a form_for_instance Form."
    def save(self, commit=True):
        return save_instance(self, instance, commit)
    return save

def form_for_model(model, form=BaseForm):
    """
    Returns a Form class for the given Django model class.

    Provide ``form`` if you want to use a custom BaseForm subclass.
    """
    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        formfield = f.formfield()
        if formfield:
            field_list.append((f.name, formfield))
    fields = SortedDictFromList(field_list)
    return type(opts.object_name + 'Form', (form,), {'fields': fields, '_model': model, 'save': model_save})

def form_for_instance(instance, form=BaseForm):
    """
    Returns a Form class for the given Django model instance.

    Provide ``form`` if you want to use a custom BaseForm subclass.
    """
    model = instance.__class__
    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        current_value = f.value_from_object(instance)
        formfield = f.formfield(initial=current_value)
        if formfield:
            field_list.append((f.name, formfield))
    fields = SortedDictFromList(field_list)
    return type(opts.object_name + 'InstanceForm', (form,),
        {'fields': fields, '_model': model, 'save': make_instance_save(instance)})

def form_for_fields(field_list):
    "Returns a Form class for the given list of Django database field instances."
    fields = SortedDictFromList([(f.name, f.formfield()) for f in field_list])
    return type('FormForFields', (BaseForm,), {'fields': fields})
