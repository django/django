"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from forms import BaseForm, DeclarativeFieldsMetaclass, SortedDictFromList

__all__ = ('form_for_model', 'form_for_fields')

def create(self, save=True):
    "Creates and returns model instance according to self.clean_data."
    if self.errors:
        raise ValueError("The %s could not be created because the data didn't validate." % self._model._meta.object_name)
    obj = self._model(**self.clean_data)
    if save:
        obj.save()
    return obj

def form_for_model(model, form=None):
    """
    Returns a Form class for the given Django model class.

    Provide 'form' if you want to use a custom BaseForm subclass.
    """
    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        formfield = f.formfield()
        if formfield:
            field_list.append((f.name, formfield))
    fields = SortedDictFromList(field_list)
    form = form or BaseForm
    return type(opts.object_name + 'Form', (form,), {'fields': fields, '_model': model, 'create': create})

def form_for_fields(field_list):
    "Returns a Form class for the given list of Django database field instances."
    fields = SortedDictFromList([(f.name, f.formfield()) for f in field_list])
    return type('FormForFields', (BaseForm,), {'fields': fields})
