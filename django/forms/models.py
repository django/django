"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from django.db import connections
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.datastructures import SortedDict
from django.utils.text import get_text_list, capfirst
from django.utils.translation import ugettext_lazy as _, ugettext

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.validators import EMPTY_VALUES
from util import ErrorList
from forms import BaseForm, get_declared_fields
from fields import Field, ChoiceField
from widgets import SelectMultiple, HiddenInput, MultipleHiddenInput
from widgets import media_property
from formsets import BaseFormSet, formset_factory, DELETION_FIELD_NAME

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

__all__ = (
    'ModelForm', 'BaseModelForm', 'model_to_dict', 'fields_for_model',
    'save_instance', 'form_for_fields', 'ModelChoiceField',
    'ModelMultipleChoiceField',
)

def construct_instance(form, instance, fields=None, exclude=None):
    """
    Constructs and returns a model instance from the bound ``form``'s
    ``cleaned_data``, but does not save the returned instance to the
    database.
    """
    from django.db import models
    opts = instance._meta

    cleaned_data = form.cleaned_data
    file_field_list = []
    for f in opts.fields:
        if not f.editable or isinstance(f, models.AutoField) \
                or not f.name in cleaned_data:
            continue
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        # Defer saving file-type fields until after the other fields, so a
        # callable upload_to can use the values from other fields.
        if isinstance(f, models.FileField):
            file_field_list.append(f)
        else:
            f.save_form_data(instance, cleaned_data[f.name])

    for f in file_field_list:
        f.save_form_data(instance, cleaned_data[f.name])

    return instance

def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None, construct=True):
    """
    Saves bound Form ``form``'s cleaned_data into model instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.

    If construct=False, assume ``instance`` has already been constructed and
    just needs to be saved.
    """
    if construct:
        instance = construct_instance(form, instance, fields, exclude)
    opts = instance._meta
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (opts.object_name, fail_message))

    # Wrap up the saving of m2m data as a function.
    def save_m2m():
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
    from django.db.models.fields.related import ManyToManyField
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

def fields_for_model(model, fields=None, exclude=None, widgets=None, formfield_callback=lambda f, **kwargs: f.formfield(**kwargs)):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    field_list = []
    opts = model._meta
    for f in opts.fields + opts.many_to_many:
        if not f.editable:
            continue
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if widgets and f.name in widgets:
            kwargs = {'widget': widgets[f.name]}
        else:
            kwargs = {}
        formfield = formfield_callback(f, **kwargs)
        if formfield:
            field_list.append((f.name, formfield))
    field_dict = SortedDict(field_list)
    if fields:
        field_dict = SortedDict([(f, field_dict.get(f)) for f in fields if (not exclude) or (exclude and f not in exclude)])
    return field_dict

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)


class ModelFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback',
                lambda f, **kwargs: f.formfield(**kwargs))
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
                                      opts.exclude, opts.widgets, formfield_callback)
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
            if opts.model is None:
                raise ValueError('ModelForm has no model class specified.')
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.model()
            object_data = {}
            self.instance._adding = True
        else:
            self.instance = instance
            self.instance._adding = False
            object_data = model_to_dict(instance, opts.fields, opts.exclude)
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        # self._validate_unique will be set to True by BaseModelForm.clean().
        # It is False by default so overriding self.clean() and failing to call
        # super will stop validate_unique from being called.
        self._validate_unique = False
        super(BaseModelForm, self).__init__(data, files, auto_id, prefix, object_data,
                                            error_class, label_suffix, empty_permitted)

    def _update_errors(self, message_dict):
        for k, v in message_dict.items():
            if k != NON_FIELD_ERRORS:
                self._errors.setdefault(k, self.error_class()).extend(v)
                # Remove the data from the cleaned_data dict since it was invalid
                if k in self.cleaned_data:
                    del self.cleaned_data[k]
        if NON_FIELD_ERRORS in message_dict:
            messages = message_dict[NON_FIELD_ERRORS]
            self._errors.setdefault(NON_FIELD_ERRORS, self.error_class()).extend(messages)

    def _get_validation_exclusions(self):
        """
        For backwards-compatibility, several types of fields need to be
        excluded from model validation. See the following tickets for
        details: #12507, #12521, #12553
        """
        exclude = []
        # Build up a list of fields that should be excluded from model field
        # validation and unique checks.
        for f in self.instance._meta.fields:
            field = f.name
            # Exclude fields that aren't on the form. The developer may be
            # adding these values to the model after form validation.
            if field not in self.fields:
                exclude.append(f.name)

            # Don't perform model validation on fields that were defined
            # manually on the form and excluded via the ModelForm's Meta
            # class. See #12901.
            elif self._meta.fields and field not in self._meta.fields:
                exclude.append(f.name)
            elif self._meta.exclude and field in self._meta.exclude:
                exclude.append(f.name)

            # Exclude fields that failed form validation. There's no need for
            # the model fields to validate them as well.
            elif field in self._errors.keys():
                exclude.append(f.name)

            # Exclude empty fields that are not required by the form. The
            # underlying model field may be required, so this keeps the model
            # field from raising that error.
            else:
                form_field = self.fields[field]
                field_value = self.cleaned_data.get(field, None)
                if field_value is None and not form_field.required:
                    exclude.append(f.name)
        return exclude

    def clean(self):
        self._validate_unique = True
        return self.cleaned_data

    def _post_clean(self):
        exclude = self._get_validation_exclusions()
        opts = self._meta

        # Update the model instance with self.cleaned_data.
        self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude)

        # Clean the model instance's fields.
        try:
            self.instance.clean_fields(exclude=exclude)
        except ValidationError, e:
            self._update_errors(e.message_dict)

        # Call the model instance's clean method.
        try:
            self.instance.clean()
        except ValidationError, e:
            self._update_errors({NON_FIELD_ERRORS: e.messages})

        # Validate uniqueness if needed.
        if self._validate_unique:
            self.validate_unique()

    def validate_unique(self):
        """
        Calls the instance's validate_unique() method and updates the form's
        validation errors if any were raised.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError, e:
            self._update_errors(e.message_dict)

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
        return save_instance(self, self.instance, self._meta.fields,
                             fail_message, commit, construct=False)

    save.alters_data = True

class ModelForm(BaseModelForm):
    __metaclass__ = ModelFormMetaclass

def modelform_factory(model, form=ModelForm, fields=None, exclude=None,
                       formfield_callback=lambda f: f.formfield()):
    # Create the inner Meta class. FIXME: ideally, we should be able to
    # construct a ModelForm without creating and passing in a temporary
    # inner class.

    # Build up a list of attributes that the Meta object will have.
    attrs = {'model': model}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    class_name = model.__name__ + 'Form'

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta,
        'formfield_callback': formfield_callback
    }

    return ModelFormMetaclass(class_name, (form,), form_class_attrs)


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
        defaults.update(kwargs)
        super(BaseModelFormSet, self).__init__(**defaults)

    def initial_form_count(self):
        """Returns the number of forms that are required in this FormSet."""
        if not (self.data or self.files):
            return len(self.get_queryset())
        return super(BaseModelFormSet, self).initial_form_count()

    def _existing_object(self, pk):
        if not hasattr(self, '_object_dict'):
            self._object_dict = dict([(o.pk, o) for o in self.get_queryset()])
        return self._object_dict.get(pk)

    def _construct_form(self, i, **kwargs):
        if self.is_bound and i < self.initial_form_count():
            pk_key = "%s-%s" % (self.add_prefix(i), self.model._meta.pk.name)
            pk = self.data[pk_key]
            pk_field = self.model._meta.pk
            pk = pk_field.get_db_prep_lookup('exact', pk,
                connection=connections[self.get_queryset().db])
            if isinstance(pk, list):
                pk = pk[0]
            kwargs['instance'] = self._existing_object(pk)
        if i < self.initial_form_count() and not kwargs.get('instance'):
            kwargs['instance'] = self.get_queryset()[i]
        return super(BaseModelFormSet, self)._construct_form(i, **kwargs)

    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            if self.queryset is not None:
                qs = self.queryset
            else:
                qs = self.model._default_manager.get_query_set()

            # If the queryset isn't already ordered we need to add an
            # artificial ordering here to make sure that all formsets
            # constructed from this queryset have the same form order.
            if not qs.ordered:
                qs = qs.order_by(self.model._meta.pk.name)

            if self.max_num > 0:
                self._queryset = qs[:self.max_num]
            else:
                self._queryset = qs
        return self._queryset

    def save_new(self, form, commit=True):
        """Saves and returns a new model instance for the given form."""
        return form.save(commit=commit)

    def save_existing(self, form, instance, commit=True):
        """Saves and returns an existing model instance for the given form."""
        return form.save(commit=commit)

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

    def clean(self):
        self.validate_unique()

    def validate_unique(self):
        # Collect unique_checks and date_checks to run from all the forms.
        all_unique_checks = set()
        all_date_checks = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            exclude = form._get_validation_exclusions()
            unique_checks, date_checks = form.instance._get_unique_checks(exclude=exclude)
            all_unique_checks = all_unique_checks.union(set(unique_checks))
            all_date_checks = all_date_checks.union(set(date_checks))

        errors = []
        # Do each of the unique checks (unique and unique_together)
        for unique_check in all_unique_checks:
            seen_data = set()
            for form in self.forms:
                # if the form doesn't have cleaned_data then we ignore it,
                # it's already invalid
                if not hasattr(form, "cleaned_data"):
                    continue
                # get each of the fields for which we have data on this form
                if [f for f in unique_check if f in form.cleaned_data and form.cleaned_data[f] is not None]:
                    # get the data itself
                    row_data = tuple([form.cleaned_data[field] for field in unique_check])
                    # if we've aready seen it then we have a uniqueness failure
                    if row_data in seen_data:
                        # poke error messages into the right places and mark
                        # the form as invalid
                        errors.append(self.get_unique_error_message(unique_check))
                        form._errors[NON_FIELD_ERRORS] = self.get_form_error()
                        del form.cleaned_data
                        break
                    # mark the data as seen
                    seen_data.add(row_data)
        # iterate over each of the date checks now
        for date_check in all_date_checks:
            seen_data = set()
            lookup, field, unique_for = date_check
            for form in self.forms:
                # if the form doesn't have cleaned_data then we ignore it,
                # it's already invalid
                if not hasattr(self, 'cleaned_data'):
                    continue
                # see if we have data for both fields
                if (form.cleaned_data and form.cleaned_data[field] is not None
                    and form.cleaned_data[unique_for] is not None):
                    # if it's a date lookup we need to get the data for all the fields
                    if lookup == 'date':
                        date = form.cleaned_data[unique_for]
                        date_data = (date.year, date.month, date.day)
                    # otherwise it's just the attribute on the date/datetime
                    # object
                    else:
                        date_data = (getattr(form.cleaned_data[unique_for], lookup),)
                    data = (form.cleaned_data[field],) + date_data
                    # if we've aready seen it then we have a uniqueness failure
                    if data in seen_data:
                        # poke error messages into the right places and mark
                        # the form as invalid
                        errors.append(self.get_date_error_message(date_check))
                        form._errors[NON_FIELD_ERRORS] = self.get_form_error()
                        del form.cleaned_data
                        break
                    seen_data.add(data)
        if errors:
            raise ValidationError(errors)

    def get_unique_error_message(self, unique_check):
        if len(unique_check) == 1:
            return ugettext("Please correct the duplicate data for %(field)s.") % {
                "field": unique_check[0],
            }
        else:
            return ugettext("Please correct the duplicate data for %(field)s, "
                "which must be unique.") % {
                    "field": get_text_list(unique_check, unicode(_("and"))),
                }

    def get_date_error_message(self, date_check):
        return ugettext("Please correct the duplicate data for %(field_name)s "
            "which must be unique for the %(lookup)s in %(date_field)s.") % {
            'field_name': date_check[1],
            'date_field': date_check[2],
            'lookup': unicode(date_check[0]),
        }

    def get_form_error(self):
        return ugettext("Please correct the duplicate values below.")

    def save_existing_objects(self, commit=True):
        self.changed_objects = []
        self.deleted_objects = []
        if not self.get_queryset():
            return []

        saved_instances = []
        for form in self.initial_forms:
            pk_name = self._pk_field.name
            raw_pk_value = form._raw_value(pk_name)

            # clean() for different types of PK fields can sometimes return
            # the model instance, and sometimes the PK. Handle either.
            pk_value = form.fields[pk_name].clean(raw_pk_value)
            pk_value = getattr(pk_value, 'pk', pk_value)

            obj = self._existing_object(pk_value)
            if self.can_delete:
                raw_delete_value = form._raw_value(DELETION_FIELD_NAME)
                should_delete = form.fields[DELETION_FIELD_NAME].clean(raw_delete_value)
                if should_delete:
                    self.deleted_objects.append(obj)
                    obj.delete()
                    continue
            if form.has_changed():
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
            if self.can_delete:
                raw_delete_value = form._raw_value(DELETION_FIELD_NAME)
                should_delete = form.fields[DELETION_FIELD_NAME].clean(raw_delete_value)
                if should_delete:
                    continue
            self.new_objects.append(self.save_new(form, commit=commit))
            if not commit:
                self.saved_forms.append(form)
        return self.new_objects

    def add_fields(self, form, index):
        """Add a hidden field for the object's primary key."""
        from django.db.models import AutoField, OneToOneField, ForeignKey
        self._pk_field = pk = self.model._meta.pk
        # If a pk isn't editable, then it won't be on the form, so we need to
        # add it here so we can tell which object is which when we get the
        # data back. Generally, pk.editable should be false, but for some
        # reason, auto_created pk fields and AutoField's editable attribute is
        # True, so check for that as well.
        def pk_is_not_editable(pk):
            return ((not pk.editable) or (pk.auto_created or isinstance(pk, AutoField))
                or (pk.rel and pk.rel.parent_link and pk_is_not_editable(pk.rel.to._meta.pk)))
        if pk_is_not_editable(pk) or pk.name not in form.fields:
            if form.is_bound:
                pk_value = form.instance.pk
            else:
                try:
                    if index is not None:
                        pk_value = self.get_queryset()[index].pk
                    else:
                        pk_value = None
                except IndexError:
                    pk_value = None
            if isinstance(pk, OneToOneField) or isinstance(pk, ForeignKey):
                qs = pk.rel.to._default_manager.get_query_set()
            else:
                qs = self.model._default_manager.get_query_set()
            qs = qs.using(form.instance._state.db)
            form.fields[self._pk_field.name] = ModelChoiceField(qs, initial=pk_value, required=False, widget=HiddenInput)
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
                 save_as_new=False, prefix=None, queryset=None):
        from django.db.models.fields.related import RelatedObject
        if instance is None:
            self.instance = self.fk.rel.to()
        else:
            self.instance = instance
        self.save_as_new = save_as_new
        # is there a better way to get the object descriptor?
        self.rel_name = RelatedObject(self.fk.rel.to, self.model, self.fk).get_accessor_name()
        if self.fk.rel.field_name == self.fk.rel.to._meta.pk.name:
            backlink_value = self.instance
        else:
            backlink_value = getattr(self.instance, self.fk.rel.field_name)
        if queryset is None:
            queryset = self.model._default_manager
        qs = queryset.filter(**{self.fk.name: backlink_value})
        super(BaseInlineFormSet, self).__init__(data, files, prefix=prefix,
                                                queryset=qs)

    def initial_form_count(self):
        if self.save_as_new:
            return 0
        return super(BaseInlineFormSet, self).initial_form_count()

    def total_form_count(self):
        if self.save_as_new:
            return super(BaseInlineFormSet, self).initial_form_count()
        return super(BaseInlineFormSet, self).total_form_count()

    def _construct_form(self, i, **kwargs):
        form = super(BaseInlineFormSet, self)._construct_form(i, **kwargs)
        if self.save_as_new:
            # Remove the primary key from the form's data, we are only
            # creating new instances
            form.data[form.add_prefix(self._pk_field.name)] = None

            # Remove the foreign key from the form's data
            form.data[form.add_prefix(self.fk.name)] = None

        # Set the fk value here so that the form can do it's validation.
        setattr(form.instance, self.fk.get_attname(), self.instance.pk)
        return form

    #@classmethod
    def get_default_prefix(cls):
        from django.db.models.fields.related import RelatedObject
        return RelatedObject(cls.fk.rel.to, cls.model, cls.fk).get_accessor_name()
    get_default_prefix = classmethod(get_default_prefix)

    def save_new(self, form, commit=True):
        # Use commit=False so we can assign the parent key afterwards, then
        # save the object.
        obj = form.save(commit=False)
        pk_value = getattr(self.instance, self.fk.rel.field_name)
        setattr(obj, self.fk.get_attname(), getattr(pk_value, 'pk', pk_value))
        if commit:
            obj.save()
        # form.save_m2m() can be called via the formset later on if commit=False
        if commit and hasattr(form, 'save_m2m'):
            form.save_m2m()
        return obj

    def add_fields(self, form, index):
        super(BaseInlineFormSet, self).add_fields(form, index)
        if self._pk_field == self.fk:
            name = self._pk_field.name
            kwargs = {'pk_field': True}
        else:
            # The foreign key field might not be on the form, so we poke at the
            # Model field to get the label, since we need that for error messages.
            name = self.fk.name
            kwargs = {
                'label': getattr(form.fields.get(name), 'label', capfirst(self.fk.verbose_name))
            }
            if self.fk.rel.field_name != self.fk.rel.to._meta.pk.name:
                kwargs['to_field'] = self.fk.rel.field_name

        form.fields[name] = InlineForeignKeyField(self.instance, **kwargs)

        # Add the generated field to form._meta.fields if it's defined to make
        # sure validation isn't skipped on that field.
        if form._meta.fields:
            if isinstance(form._meta.fields, tuple):
                form._meta.fields = list(form._meta.fields)
            form._meta.fields.append(self.fk.name)

    def get_unique_error_message(self, unique_check):
        unique_check = [field for field in unique_check if field != self.fk.name]
        return super(BaseInlineFormSet, self).get_unique_error_message(unique_check)

def _get_foreign_key(parent_model, model, fk_name=None, can_fail=False):
    """
    Finds and returns the ForeignKey from model to parent if there is one
    (returns None if can_fail is True and no such field exists). If fk_name is
    provided, assume it is the name of the ForeignKey field. Unles can_fail is
    True, an exception is raised if there is no ForeignKey from model to
    parent_model.
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
            if can_fail:
                return
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

class InlineForeignKeyHiddenInput(HiddenInput):
    def _has_changed(self, initial, data):
        return False

class InlineForeignKeyField(Field):
    """
    A basic integer field that deals with validating the given value to a
    given parent instance in an inline.
    """
    default_error_messages = {
        'invalid_choice': _(u'The inline foreign key did not match the parent instance primary key.'),
    }

    def __init__(self, parent_instance, *args, **kwargs):
        self.parent_instance = parent_instance
        self.pk_field = kwargs.pop("pk_field", False)
        self.to_field = kwargs.pop("to_field", None)
        if self.parent_instance is not None:
            if self.to_field:
                kwargs["initial"] = getattr(self.parent_instance, self.to_field)
            else:
                kwargs["initial"] = self.parent_instance.pk
        kwargs["required"] = False
        kwargs["widget"] = InlineForeignKeyHiddenInput
        super(InlineForeignKeyField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if value in EMPTY_VALUES:
            if self.pk_field:
                return None
            # if there is no value act as we did before.
            return self.parent_instance
        # ensure the we compare the values as equal types.
        if self.to_field:
            orig = getattr(self.parent_instance, self.to_field)
        else:
            orig = self.parent_instance.pk
        if force_unicode(value) != force_unicode(orig):
            raise ValidationError(self.error_messages['invalid_choice'])
        return self.parent_instance

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
                    self.choice(obj) for obj in self.queryset.all()
                ]
            for choice in self.field.choice_cache:
                yield choice
        else:
            for obj in self.queryset.all():
                yield self.choice(obj)

    def __len__(self):
        return len(self.queryset)

    def choice(self, obj):
        if self.field.to_field_name:
            key = obj.serializable_value(self.field.to_field_name)
        else:
            key = obj.pk
        return (key, self.field.label_from_instance(obj))


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
                 help_text=None, to_field_name=None, *args, **kwargs):
        if required and (initial is not None):
            self.empty_label = None
        else:
            self.empty_label = empty_label
        self.cache_choices = cache_choices

        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        Field.__init__(self, required, widget, label, initial, help_text,
                       *args, **kwargs)
        self.queryset = queryset
        self.choice_cache = None
        self.to_field_name = to_field_name

    def __deepcopy__(self, memo):
        result = super(ChoiceField, self).__deepcopy__(memo)
        # Need to force a new ModelChoiceIterator to be created, bug #11183
        result.queryset = result.queryset
        return result

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

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        try:
            key = self.to_field_name or 'pk'
            value = self.queryset.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value

    def validate(self, value):
        return Field.validate(self, value)

class ModelMultipleChoiceField(ModelChoiceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    widget = SelectMultiple
    hidden_widget = MultipleHiddenInput
    default_error_messages = {
        'list': _(u'Enter a list of values.'),
        'invalid_choice': _(u'Select a valid choice. %s is not one of the'
                            u' available choices.'),
        'invalid_pk_value': _(u'"%s" is not a valid value for a primary key.')
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
        for pk in value:
            try:
                self.queryset.filter(pk=pk)
            except ValueError:
                raise ValidationError(self.error_messages['invalid_pk_value'] % pk)
        qs = self.queryset.filter(pk__in=value)
        pks = set([force_unicode(o.pk) for o in qs])
        for val in value:
            if force_unicode(val) not in pks:
                raise ValidationError(self.error_messages['invalid_choice'] % val)
        return qs
