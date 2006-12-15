"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from forms import BaseForm, DeclarativeFieldsMetaclass, SortedDictFromList

__all__ = ('form_for_model', 'form_for_fields')

def form_for_model(model):
    "Returns a Form class for the given Django model class."
    opts = model._meta
    fields = SortedDictFromList([(f.name, f.formfield()) for f in opts.fields + opts.many_to_many])
    return type(opts.object_name + 'Form', (BaseForm,), {'fields': fields, '_model_opts': opts})

def form_for_fields(field_list):
    "Returns a Form class for the given list of Django database field instances."
    fields = SortedDictFromList([(f.name, f.formfield()) for f in field_list])
    return type('FormForFields', (BaseForm,), {'fields': fields})
