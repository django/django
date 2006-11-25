"""
Helper functions for creating Forms from Django models and database field objects.
"""

__all__ = ('form_for_model', 'form_for_fields')

def form_for_model(model):
    "Returns a Form instance for the given Django model class."
    raise NotImplementedError

def form_for_fields(field_list):
    "Returns a Form instance for the given list of Django database field instances."
    raise NotImplementedError
