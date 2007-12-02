"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode
from django.utils.datastructures import SortedDict

from util import ValidationError
from forms import BaseForm
from fields import Field, ChoiceField, IntegerField, EMPTY_VALUES
from formsets import BaseFormSet, formset_for_form, DELETION_FIELD_NAME
from widgets import Select, SelectMultiple, HiddenInput, MultipleHiddenInput

__all__ = (
    'save_instance', 'form_for_model', 'form_for_instance', 'form_for_fields',
    'formset_for_model', 'inline_formset',
    'ModelChoiceField', 'ModelMultipleChoiceField',
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
            yield (obj.pk, smart_unicode(obj))
        # Clear the QuerySet cache if required.
        if not self.cache_choices:
            self.queryset._result_cache = None

class ModelChoiceField(ChoiceField):
    """A ChoiceField whose choices are a model QuerySet."""
    # This class is a subclass of ChoiceField for purity, but it doesn't
    # actually use any of ChoiceField's implementation.
    default_error_messages = {
        'invalid_choice': _(u'Select a valid choice. That choice is not one of'
                            u' the available choices.'),
    }

    def __init__(self, queryset, empty_label=u"---------", cache_choices=False,
                 required=True, widget=Select, label=None, initial=None,
                 help_text=None, *args, **kwargs):
        self.empty_label = empty_label
        self.cache_choices = cache_choices
        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        Field.__init__(self, required, widget, label, initial, help_text,
                       *args, **kwargs)
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
        if value in EMPTY_VALUES:
            return None
        try:
            value = self.queryset.get(pk=value)
        except self.queryset.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value

class ModelMultipleChoiceField(ModelChoiceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    hidden_widget = MultipleHiddenInput
    default_error_messages = {
        'list': _(u'Enter a list of values.'),
        'invalid_choice': _(u'Select a valid choice. %s is not one of the'
                            u' available choices.'),
    }

    def __init__(self, queryset, cache_choices=False, required=True,
                 widget=SelectMultiple, label=None, initial=None,
                 help_text=None, *args, **kwargs):
        super(ModelMultipleChoiceField, self).__init__(queryset, None,
            cache_choices, required, widget, label, initial, help_text,
            *args, **kwargs)

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['list'])
        final_values = []
        for val in value:
            try:
                obj = self.queryset.get(pk=val)
            except self.queryset.model.DoesNotExist:
                raise ValidationError(self.error_messages['invalid_choice'] % val)
            else:
                final_values.append(obj)
        return final_values

# Model-FormSet integration ###################################################

def initial_data(instance, fields=None):
    """
    Return a dictionary from data in ``instance`` that is suitable for
    use as a ``Form`` constructor's ``initial`` argument.

    Provide ``fields`` to specify the names of specific fields to return.
    All field values in the instance will be returned if ``fields`` is not
    provided.
    """
    # avoid a circular import
    from django.db.models.fields.related import ManyToManyField
    model = instance.__class__
    opts = model._meta
    initial = {}
    for f in opts.fields + opts.many_to_many:
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        if isinstance(f, ManyToManyField):
            # MultipleChoiceWidget needs a list of ints, not object instances.
            initial[f.name] = [obj.pk for obj in f.value_from_object(instance)]
        else:
            initial[f.name] = f.value_from_object(instance)
    return initial

class BaseModelFormSet(BaseFormSet):
    """
    A ``FormSet`` for editing a queryset and/or adding new objects to it.
    """
    model = None
    queryset = None

    def __init__(self, qs, data=None, files=None, auto_id='id_%s', prefix=None):
        kwargs = {'data': data, 'files': files, 'auto_id': auto_id, 'prefix': prefix}
        self.queryset = qs
        kwargs['initial'] = [initial_data(obj) for obj in qs]
        super(BaseModelFormSet, self).__init__(**kwargs)

    def save_new(self, form, commit=True):
        """Saves and returns a new model instance for the given form."""
        return save_instance(form, self.model(), commit=commit)

    def save_instance(self, form, instance, commit=True):
        """Saves and returns an existing model instance for the given form."""
        return save_instance(form, instance, commit=commit)

    def save(self, commit=True):
        """Saves model instances for every form, adding and changing instances
        as necessary, and returns the list of instances.
        """
        return self.save_existing_objects(commit) + self.save_new_objects(commit)

    def save_existing_objects(self, commit=True):
        if not self.queryset:
            return []
        # Put the objects from self.get_queryset into a dict so they are easy to lookup by pk
        existing_objects = {}
        for obj in self.queryset:
            existing_objects[obj.pk] = obj
        saved_instances = []
        for form in self.change_forms:
            obj = existing_objects[form.cleaned_data[self.model._meta.pk.attname]]
            if self.deletable and form.cleaned_data[DELETION_FIELD_NAME]:
                obj.delete()
            else:
                saved_instances.append(self.save_instance(form, obj, commit=commit))
        return saved_instances

    def save_new_objects(self, commit=True):
        new_objects = []
        for form in self.add_forms:
            if form.is_empty():
                continue
            # If someone has marked an add form for deletion, don't save the
            # object. At some point it would be nice if we didn't display
            # the deletion widget for add forms.
            if self.deletable and form.cleaned_data[DELETION_FIELD_NAME]:
                continue
            new_objects.append(self.save_new(form, commit=commit))
        return new_objects

    def add_fields(self, form, index):
        """Add a hidden field for the object's primary key."""
        self._pk_field_name = self.model._meta.pk.attname
        form.fields[self._pk_field_name] = IntegerField(required=False, widget=HiddenInput)
        super(BaseModelFormSet, self).add_fields(form, index)

def formset_for_model(model, form=BaseForm, formfield_callback=lambda f: f.formfield(),
                      formset=BaseModelFormSet, extra=1, orderable=False, deletable=False, fields=None):
    """
    Returns a FormSet class for the given Django model class. This FormSet
    will contain change forms for every instance of the given model as well
    as the number of add forms specified by ``extra``.
    
    This is essentially the same as ``formset_for_queryset``, but automatically
    uses the model's default manager to determine the queryset.
    """
    form = form_for_model(model, form=form, fields=fields, formfield_callback=formfield_callback)
    FormSet = formset_for_form(form, formset, extra, orderable, deletable)
    FormSet.model = model
    return FormSet

class InlineFormset(BaseModelFormSet):
    """A formset for child objects related to a parent."""
    def __init__(self, instance, data=None, files=None):
        from django.db.models.fields.related import RelatedObject
        self.instance = instance
        # is there a better way to get the object descriptor?
        self.rel_name = RelatedObject(self.fk.rel.to, self.model, self.fk).get_accessor_name()
        qs = self.get_queryset()
        super(InlineFormset, self).__init__(qs, data, files, prefix=self.rel_name)

    def get_queryset(self):
        """
        Returns this FormSet's queryset, but restricted to children of 
        self.instance
        """
        kwargs = {self.fk.name: self.instance}
        return self.model._default_manager.filter(**kwargs)

    def save_new(self, form, commit=True):
        kwargs = {self.fk.get_attname(): self.instance._get_pk_val()}
        new_obj = self.model(**kwargs)
        return save_instance(form, new_obj, commit=commit)

def get_foreign_key(parent_model, model, fk_name=None):
    """
    Finds and returns the ForeignKey from model to parent if there is one.
    If fk_name is provided, assume it is the name of the ForeignKey field.
    """
    # avoid circular import
    from django.db.models import ForeignKey
    opts = model._meta
    if fk_name:
        fks_to_parent = [f for f in opts.fields if f.name == fk_name]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
            if not isinstance(fk, ForeignKey) or fk.rel.to != parent_model:
                raise Exception("fk_name '%s' is not a ForeignKey to %s" % (fk_name, parent_model))
        elif len(fks_to_parent) == 0:
            raise Exception("%s has no field named '%s'" % (model, fk_name))
    else:
        # Try to discover what the ForeignKey from model to parent_model is
        fks_to_parent = [f for f in opts.fields if isinstance(f, ForeignKey) and f.rel.to == parent_model]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
        elif len(fks_to_parent) == 0:
            raise Exception("%s has no ForeignKey to %s" % (model, parent_model))
        else:
            raise Exception("%s has more than 1 ForeignKey to %s" % (model, parent_model))
    return fk

def inline_formset(parent_model, model, fk_name=None, fields=None, extra=3, orderable=False, deletable=True, formfield_callback=lambda f: f.formfield()):
    """
    Returns an ``InlineFormset`` for the given kwargs.

    You must provide ``fk_name`` if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    fk = get_foreign_key(parent_model, model, fk_name=fk_name)
    # let the formset handle object deletion by default
    FormSet = formset_for_model(model, formset=InlineFormset, fields=fields,
                                formfield_callback=formfield_callback,
                                extra=extra, orderable=orderable,
                                deletable=deletable)
    # HACK: remove the ForeignKey to the parent from every form
    # This should be done a line above before we pass 'fields' to formset_for_model
    # an 'omit' argument would be very handy here
    try:
        del FormSet.form_class.base_fields[fk.name]
    except KeyError:
        pass
    FormSet.fk = fk
    return FormSet
