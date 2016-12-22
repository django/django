from django import forms


def default_formfield(db_field, form_class, defaults):
    defaults['widget'] = forms.Textarea
    return form_class(**defaults)
