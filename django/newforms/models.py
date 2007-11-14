"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from django.utils.translation import ugettext
from django.utils.encoding import smart_unicode
from django.utils.datastructures import SortedDict

from util import ValidationError
from forms import BaseForm
from fields import Field, ChoiceField
from widgets import Select, SelectMultiple, MultipleHiddenInput

__all__ = (
    'save_instance', 'form_for_model', 'form_for_instance', 'form_for_fields',
    'ModelChoiceField', 'ModelMultipleChoiceField'
)

def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True):
    """
    Saves bound Form ``form``'s cleaned_data into model instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.
    """
    from django.db import models
    opts = instance.__class__._meta
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (opts.object_name, fail_message))
    cleaned_data = form.cleaned_data
    for f in opts.fields:
        if not f.editable or isinstance(f, models.AutoField) \
                or not f.name in cleaned_data:
            continue
        if fields and f.name not in fields:
            continue
        f.save_form_data(instance, cleaned_data[f.name])
    # Wrap up the saving of m2m data as a function.
    def save_m2m():
        opts = instance.__class__._meta
        cleaned_data = form.cleaned_data
        for f in opts.many_to_many:
            if fields and f.name not in fields:
                continue
            if f.name in cleaned_data:
                f.save_form_data(instance, cleaned_data[f.name])
    if commit:
        # If we are committing, save the instance and the m2m data immediately.
        instance.save()
        save_m2m()
    else:
        # We're not committing. Add a method to the form to allow deferred
        # saving of m2m data.
        form.save_m2m = save_m2m
    return instance

def make_model_save(model, fields, fail_message):
    """Returns the save() method for a Form."""
    def save(self, commit=True):
        return save_instance(self, model(), fields, fail_message, commit)
    return save

def make_instance_save(instance, fields, fail_message):
    """Returns the save() method for a Form."""
    def save(self, commit=True):
        return save_instance(self, instance, fields, fail_message, commit)
    return save

def form_for_model(model, form=BaseForm, fields=None,
                   formfield_callback=lambda f: f.formfield()):
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
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        formfield = formfield_callback(f)
        if formfield:
            field_list.append((f.name, formfield))
    base_fields = SortedDict(field_list)
    return type(opts.object_name + 'Form', (form,),
        {'base_fields': base_fields, '_model': model,
         'save': make_model_save(model, fields, 'created')})

def form_for_instance(instance, form=BaseForm, fields=None,
                      formfield_callback=lambda f, **kwargs: f.formfield(**kwargs)):
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
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        current_value = f.value_from_object(instance)
        formfield = formfield_callback(f, initial=current_value)
        if formfield:
            field_list.append((f.name, formfield))
    base_fields = SortedDict(field_list)
    return type(opts.object_name + 'InstanceForm', (form,),
        {'base_fields': base_fields, '_model': model,
         'save': make_instance_save(instance, fields, 'changed')})

def form_for_fields(field_list):
    """
    Returns a Form class for the given list of Django database field instances.
    """
    fields = SortedDict([(f.name, f.formfield())
                         for f in field_list if f.editable])
    return type('FormForFields', (BaseForm,), {'base_fields': fields})

class QuerySetIterator(object):
    def __init__(self, queryset, empty_label, cache_choices):
        self.queryset = queryset
        self.empty_label = empty_label
        self.cache_choices = cache_choices

    def __iter__(self):
        if self.empty_label is not None:
            yield (u"", self.empty_label)
        for obj in self.queryset:
            yield (obj._get_pk_val(), smart_unicode(obj))
        # Clear the QuerySet cache if required.
        if not self.cache_choices:
            self.queryset._result_cache = None

class ModelChoiceField(ChoiceField):
    """A ChoiceField whose choices are a model QuerySet."""
    # This class is a subclass of ChoiceField for purity, but it doesn't
    # actually use any of ChoiceField's implementation.

    def __init__(self, queryset, empty_label=u"---------", cache_choices=False,
                 required=True, widget=Select, label=None, initial=None,
                 help_text=None):
        self.empty_label = empty_label
        self.cache_choices = cache_choices
        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        Field.__init__(self, required, widget, label, initial, help_text)
        self.queryset = queryset

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices
        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not
        # been consumed. Note that we're instantiating a new QuerySetIterator
        # *each* time _get_choices() is called (and, thus, each time
        # self.choices is accessed) so that we can ensure the QuerySet has not
        # been consumed.
        return QuerySetIterator(self.queryset, self.empty_label,
                                self.cache_choices)

    def _set_choices(self, value):
        # This method is copied from ChoiceField._set_choices(). It's necessary
        # because property() doesn't allow a subclass to overwrite only
        # _get_choices without implementing _set_choices.
        self._choices = self.widget.choices = list(value)

    choices = property(_get_choices, _set_choices)

    def clean(self, value):
        Field.clean(self, value)
        if value in ('', None):
            return None
        try:
            value = self.queryset.get(pk=value)
        except self.queryset.model.DoesNotExist:
            raise ValidationError(ugettext(u'Select a valid choice. That'
                                           u' choice is not one of the'
                                           u' available choices.'))
        return value

class ModelMultipleChoiceField(ModelChoiceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    hidden_widget = MultipleHiddenInput

    def __init__(self, queryset, cache_choices=False, required=True,
                 widget=SelectMultiple, label=None, initial=None,
                 help_text=None):
        super(ModelMultipleChoiceField, self).__init__(queryset, None,
            cache_choices, required, widget, label, initial, help_text)

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(ugettext(u'This field is required.'))
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValidationError(ugettext(u'Enter a list of values.'))
        final_values = []
        for val in value:
            try:
                obj = self.queryset.get(pk=val)
            except self.queryset.model.DoesNotExist:
                raise ValidationError(ugettext(u'Select a valid choice. %s is'
                                               u' not one of the available'
                                               u' choices.') % val)
            else:
                final_values.append(obj)
        return final_values
