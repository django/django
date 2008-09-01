"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from django.utils.encoding import smart_unicode
from django.utils.datastructures import SortedDict
from django.utils.text import get_text_list, capfirst
from django.utils.translation import ugettext_lazy as _

from util import ValidationError, ErrorList
from forms import BaseForm, get_declared_fields
from fields import Field, ChoiceField, IntegerField, EMPTY_VALUES
from widgets import Select, SelectMultiple, HiddenInput, MultipleHiddenInput
from widgets import media_property
from formsets import BaseFormSet, formset_factory, DELETION_FIELD_NAME

__all__ = (
    'ModelForm', 'BaseModelForm', 'model_to_dict', 'fields_for_model',
    'save_instance', 'form_for_fields', 'ModelChoiceField',
    'ModelMultipleChoiceField',
)


def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None):
    """
    Saves bound Form ``form``'s cleaned_data into model instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.
    """
    from django.db import models
    opts = instance._meta
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
        if exclude and f.name in exclude:
            continue
        f.save_form_data(instance, cleaned_data[f.name])
    # Wrap up the saving of m2m data as a function.
    def save_m2m():
        opts = instance._meta
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

def form_for_fields(field_list):
    """
    Returns a Form class for the given list of Django database field instances.
    """
    fields = SortedDict([(f.name, f.formfield())
                         for f in field_list if f.editable])
    return type('FormForFields', (BaseForm,), {'base_fields': fields})


# ModelForms #################################################################

def model_to_dict(instance, fields=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned dict.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned dict, even if they are listed in
    the ``fields`` argument.
    """
    # avoid a circular import
    from django.db.models.fields.related import ManyToManyField, OneToOneField
    opts = instance._meta
    data = {}
    for f in opts.fields + opts.many_to_many:
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if isinstance(f, ManyToManyField):
            # If the object doesn't have a primry key yet, just use an empty
            # list for its m2m fields. Calling f.value_from_object will raise
            # an exception.
            if instance.pk is None:
                data[f.name] = []
            else:
                # MultipleChoiceWidget needs a list of pks, not object instances.
                data[f.name] = [obj.pk for obj in f.value_from_object(instance)]
        else:
            data[f.name] = f.value_from_object(instance)
    return data

def fields_for_model(model, fields=None, exclude=None, formfield_callback=lambda f: f.formfield()):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    # TODO: if fields is provided, it would be nice to return fields in that order
    field_list = []
    opts = model._meta
    for f in opts.fields + opts.many_to_many:
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        formfield = formfield_callback(f)
        if formfield:
            field_list.append((f.name, formfield))
    return SortedDict(field_list)

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)


class ModelFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback',
                lambda f: f.formfield())
        try:
            parents = [b for b in bases if issubclass(b, ModelForm)]
        except NameError:
            # We are defining ModelForm itself.
            parents = None
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(ModelFormMetaclass, cls).__new__(cls, name, bases,
                attrs)
        if not parents:
            return new_class

        if 'media' not in attrs:
            new_class.media = media_property(new_class)
        opts = new_class._meta = ModelFormOptions(getattr(new_class, 'Meta', None))
        if opts.model:
            # If a model is defined, extract form fields from it.
            fields = fields_for_model(opts.model, opts.fields,
                                      opts.exclude, formfield_callback)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class

class BaseModelForm(BaseForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        opts = self._meta
        if instance is None:
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.model()
            object_data = {}
        else:
            self.instance = instance
            object_data = model_to_dict(instance, opts.fields, opts.exclude)
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        super(BaseModelForm, self).__init__(data, files, auto_id, prefix, object_data,
                                            error_class, label_suffix, empty_permitted)
    def clean(self):
        self.validate_unique()
        return self.cleaned_data

    def validate_unique(self):
        from django.db.models.fields import FieldDoesNotExist
        unique_checks = list(self.instance._meta.unique_together[:])
        form_errors = []
        
        # Make sure the unique checks apply to actual fields on the ModelForm
        for name, field in self.fields.items():
            try:
                f = self.instance._meta.get_field_by_name(name)[0]
            except FieldDoesNotExist:
                # This is an extra field that's not on the ModelForm, ignore it
                continue
            # MySQL can't handle ... WHERE pk IS NULL, so make sure we don't 
            # don't generate queries of that form.
            is_null_pk = f.primary_key and self.cleaned_data[name] is None
            if name in self.cleaned_data and f.unique and not is_null_pk:
                unique_checks.append((name,))
                
        # Don't run unique checks on fields that already have an error.
        unique_checks = [check for check in unique_checks if not [x in self._errors for x in check if x in self._errors]]
        
        for unique_check in unique_checks:
            # Try to look up an existing object with the same values as this
            # object's values for all the unique field.
            
            lookup_kwargs = {}
            for field_name in unique_check:
                lookup_kwargs[field_name] = self.cleaned_data[field_name]
            
            qs = self.instance.__class__._default_manager.filter(**lookup_kwargs)

            # Exclude the current object from the query if we are editing an 
            # instance (as opposed to creating a new one)
            if self.instance.pk is not None:
                qs = qs.exclude(pk=self.instance.pk)
                
            # This cute trick with extra/values is the most efficiant way to
            # tell if a particular query returns any results.
            if qs.extra(select={'a': 1}).values('a').order_by():
                model_name = capfirst(self.instance._meta.verbose_name)
                
                # A unique field
                if len(unique_check) == 1:
                    field_name = unique_check[0]
                    field_label = self.fields[field_name].label
                    # Insert the error into the error dict, very sneaky
                    self._errors[field_name] = ErrorList([
                        _(u"%(model_name)s with this %(field_label)s already exists.") % \
                        {'model_name': unicode(model_name),
                         'field_label': unicode(field_label)}
                    ])
                # unique_together
                else:
                    field_labels = [self.fields[field_name].label for field_name in unique_check]
                    field_labels = get_text_list(field_labels, _('and'))
                    form_errors.append(
                        _(u"%(model_name)s with this %(field_label)s already exists.") % \
                        {'model_name': unicode(model_name),
                         'field_label': unicode(field_labels)}
                    )
                
                # Remove the data from the cleaned_data dict since it was invalid
                for field_name in unique_check:
                    del self.cleaned_data[field_name]
        
        if form_errors:
            # Raise the unique together errors since they are considered form-wide.
            raise ValidationError(form_errors)

    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        if self.instance.pk is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        return save_instance(self, self.instance, self._meta.fields, fail_message, commit)

class ModelForm(BaseModelForm):
    __metaclass__ = ModelFormMetaclass

def modelform_factory(model, form=ModelForm, fields=None, exclude=None,
                       formfield_callback=lambda f: f.formfield()):
    # HACK: we should be able to construct a ModelForm without creating
    # and passing in a temporary inner class
    class Meta:
        pass
    setattr(Meta, 'model', model)
    setattr(Meta, 'fields', fields)
    setattr(Meta, 'exclude', exclude)
    class_name = model.__name__ + 'Form'
    return ModelFormMetaclass(class_name, (form,), {'Meta': Meta,
                              'formfield_callback': formfield_callback})


# ModelFormSets ##############################################################

class BaseModelFormSet(BaseFormSet):
    """
    A ``FormSet`` for editing a queryset and/or adding new objects to it.
    """
    model = None

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 queryset=None, **kwargs):
        self.queryset = queryset
        defaults = {'data': data, 'files': files, 'auto_id': auto_id, 'prefix': prefix}
        defaults['initial'] = [model_to_dict(obj) for obj in self.get_queryset()]
        defaults.update(kwargs)
        super(BaseModelFormSet, self).__init__(**defaults)

    def _construct_form(self, i, **kwargs):
        if i < self._initial_form_count:
            kwargs['instance'] = self.get_queryset()[i]
        return super(BaseModelFormSet, self)._construct_form(i, **kwargs)

    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            if self.queryset is not None:
                qs = self.queryset
            else:
                qs = self.model._default_manager.get_query_set()
            if self.max_num > 0:
                self._queryset = qs[:self.max_num]
            else:
                self._queryset = qs
        return self._queryset

    def save_new(self, form, commit=True):
        """Saves and returns a new model instance for the given form."""
        return save_instance(form, self.model(), exclude=[self._pk_field.name], commit=commit)

    def save_existing(self, form, instance, commit=True):
        """Saves and returns an existing model instance for the given form."""
        return save_instance(form, instance, exclude=[self._pk_field.name], commit=commit)

    def save(self, commit=True):
        """Saves model instances for every form, adding and changing instances
        as necessary, and returns the list of instances.
        """
        if not commit:
            self.saved_forms = []
            def save_m2m():
                for form in self.saved_forms:
                    form.save_m2m()
            self.save_m2m = save_m2m
        return self.save_existing_objects(commit) + self.save_new_objects(commit)

    def save_existing_objects(self, commit=True):
        self.changed_objects = []
        self.deleted_objects = []
        if not self.get_queryset():
            return []

        # Put the objects from self.get_queryset into a dict so they are easy to lookup by pk
        existing_objects = {}
        for obj in self.get_queryset():
            existing_objects[obj.pk] = obj
        saved_instances = []
        for form in self.initial_forms:
            obj = existing_objects[form.cleaned_data[self._pk_field.name]]
            if self.can_delete and form.cleaned_data[DELETION_FIELD_NAME]:
                self.deleted_objects.append(obj)
                obj.delete()
            else:
                if form.changed_data:
                    self.changed_objects.append((obj, form.changed_data))
                    saved_instances.append(self.save_existing(form, obj, commit=commit))
                    if not commit:
                        self.saved_forms.append(form)
        return saved_instances

    def save_new_objects(self, commit=True):
        self.new_objects = []
        for form in self.extra_forms:
            if not form.has_changed():
                continue
            # If someone has marked an add form for deletion, don't save the
            # object.
            if self.can_delete and form.cleaned_data[DELETION_FIELD_NAME]:
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
            if not commit:
                self.saved_forms.append(form)
        return self.new_objects

    def add_fields(self, form, index):
        """Add a hidden field for the object's primary key."""
        from django.db.models import AutoField
        self._pk_field = pk = self.model._meta.pk
        if pk.auto_created or isinstance(pk, AutoField):
            form.fields[self._pk_field.name] = IntegerField(required=False, widget=HiddenInput)
        super(BaseModelFormSet, self).add_fields(form, index)

def modelformset_factory(model, form=ModelForm, formfield_callback=lambda f: f.formfield(),
                         formset=BaseModelFormSet,
                         extra=1, can_delete=False, can_order=False,
                         max_num=0, fields=None, exclude=None):
    """
    Returns a FormSet class for the given Django model class.
    """
    form = modelform_factory(model, form=form, fields=fields, exclude=exclude,
                             formfield_callback=formfield_callback)
    FormSet = formset_factory(form, formset, extra=extra, max_num=max_num,
                              can_order=can_order, can_delete=can_delete)
    FormSet.model = model
    return FormSet


# InlineFormSets #############################################################

class BaseInlineFormSet(BaseModelFormSet):
    """A formset for child objects related to a parent."""
    def __init__(self, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None):
        from django.db.models.fields.related import RelatedObject
        self.instance = instance
        self.save_as_new = save_as_new
        # is there a better way to get the object descriptor?
        self.rel_name = RelatedObject(self.fk.rel.to, self.model, self.fk).get_accessor_name()
        super(BaseInlineFormSet, self).__init__(data, files, prefix=prefix or self.rel_name)

    def _construct_forms(self):
        if self.save_as_new:
            self._total_form_count = self._initial_form_count
            self._initial_form_count = 0
        super(BaseInlineFormSet, self)._construct_forms()

    def _construct_form(self, i, **kwargs):
        form = super(BaseInlineFormSet, self)._construct_form(i, **kwargs)
        if self.save_as_new:
            # Remove the primary key from the form's data, we are only
            # creating new instances
            form.data[form.add_prefix(self._pk_field.name)] = None
        return form

    def get_queryset(self):
        """
        Returns this FormSet's queryset, but restricted to children of
        self.instance
        """
        kwargs = {self.fk.name: self.instance}
        return self.model._default_manager.filter(**kwargs)

    def save_new(self, form, commit=True):
        kwargs = {self.fk.get_attname(): self.instance.pk}
        new_obj = self.model(**kwargs)
        return save_instance(form, new_obj, exclude=[self._pk_field.name], commit=commit)
    
    def add_fields(self, form, index):
        super(BaseInlineFormSet, self).add_fields(form, index)
        if self._pk_field == self.fk:
            form.fields[self._pk_field.name] = IntegerField(required=False, widget=HiddenInput)

def _get_foreign_key(parent_model, model, fk_name=None):
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
            if not isinstance(fk, ForeignKey) or \
                    (fk.rel.to != parent_model and
                     fk.rel.to not in parent_model._meta.get_parent_list()):
                raise Exception("fk_name '%s' is not a ForeignKey to %s" % (fk_name, parent_model))
        elif len(fks_to_parent) == 0:
            raise Exception("%s has no field named '%s'" % (model, fk_name))
    else:
        # Try to discover what the ForeignKey from model to parent_model is
        fks_to_parent = [
            f for f in opts.fields
            if isinstance(f, ForeignKey)
            and (f.rel.to == parent_model
                or f.rel.to in parent_model._meta.get_parent_list())
        ]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
        elif len(fks_to_parent) == 0:
            raise Exception("%s has no ForeignKey to %s" % (model, parent_model))
        else:
            raise Exception("%s has more than 1 ForeignKey to %s" % (model, parent_model))
    return fk


def inlineformset_factory(parent_model, model, form=ModelForm,
                          formset=BaseInlineFormSet, fk_name=None,
                          fields=None, exclude=None,
                          extra=3, can_order=False, can_delete=True, max_num=0,
                          formfield_callback=lambda f: f.formfield()):
    """
    Returns an ``InlineFormSet`` for the given kwargs.

    You must provide ``fk_name`` if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    fk = _get_foreign_key(parent_model, model, fk_name=fk_name)
    # enforce a max_num=1 when the foreign key to the parent model is unique.
    if fk.unique:
        max_num = 1
    if exclude is not None:
        exclude.append(fk.name)
    else:
        exclude = [fk.name]
    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': formset,
        'extra': extra,
        'can_delete': can_delete,
        'can_order': can_order,
        'fields': fields,
        'exclude': exclude,
        'max_num': max_num,
    }
    FormSet = modelformset_factory(model, **kwargs)
    FormSet.fk = fk
    return FormSet


# Fields #####################################################################

class ModelChoiceIterator(object):
    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        if self.field.cache_choices:
            if self.field.choice_cache is None:
                self.field.choice_cache = [
                    (obj.pk, self.field.label_from_instance(obj))
                    for obj in self.queryset.all()
                ]
            for choice in self.field.choice_cache:
                yield choice
        else:
            for obj in self.queryset.all():
                yield (obj.pk, self.field.label_from_instance(obj))

class ModelChoiceField(ChoiceField):
    """A ChoiceField whose choices are a model QuerySet."""
    # This class is a subclass of ChoiceField for purity, but it doesn't
    # actually use any of ChoiceField's implementation.
    default_error_messages = {
        'invalid_choice': _(u'Select a valid choice. That choice is not one of'
                            u' the available choices.'),
    }

    def __init__(self, queryset, empty_label=u"---------", cache_choices=False,
                 required=True, widget=None, label=None, initial=None,
                 help_text=None, *args, **kwargs):
        self.empty_label = empty_label
        self.cache_choices = cache_choices

        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        Field.__init__(self, required, widget, label, initial, help_text,
                       *args, **kwargs)
        self.queryset = queryset
        self.choice_cache = None

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    # this method will be used to create object labels by the QuerySetIterator.
    # Override it to customize the label.
    def label_from_instance(self, obj):
        """
        This method is used to convert objects into strings; it's used to
        generate the labels for the choices presented by this object. Subclasses
        can override this method to customize the display of the choices.
        """
        return smart_unicode(obj)

    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices

        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not been
        # consumed. Note that we're instantiating a new QuerySetIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        return ModelChoiceIterator(self)

    choices = property(_get_choices, ChoiceField._set_choices)

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
    widget = SelectMultiple
    hidden_widget = MultipleHiddenInput
    default_error_messages = {
        'list': _(u'Enter a list of values.'),
        'invalid_choice': _(u'Select a valid choice. %s is not one of the'
                            u' available choices.'),
    }

    def __init__(self, queryset, cache_choices=False, required=True,
                 widget=None, label=None, initial=None,
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
