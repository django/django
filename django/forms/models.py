"""
Helper functions for creating Form classes from Django models
and database field objects.
"""

from itertools import chain

from django.core.exceptions import (
    NON_FIELD_ERRORS,
    FieldError,
    ImproperlyConfigured,
    ValidationError,
)
from django.core.validators import ProhibitNullCharactersValidator
from django.db.models.utils import AltersData
from django.forms.fields import ChoiceField, Field
from django.forms.forms import BaseForm, DeclarativeFieldsMetaclass
from django.forms.formsets import BaseFormSet, formset_factory
from django.forms.utils import ErrorList
from django.forms.widgets import (
    HiddenInput,
    MultipleHiddenInput,
    RadioSelect,
    SelectMultiple,
)
from django.utils.choices import BaseChoiceIterator
from django.utils.hashable import make_hashable
from django.utils.text import capfirst, get_text_list
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

__all__ = (
    "ModelForm",
    "BaseModelForm",
    "model_to_dict",
    "fields_for_model",
    "ModelChoiceField",
    "ModelMultipleChoiceField",
    "ALL_FIELDS",
    "BaseModelFormSet",
    "modelformset_factory",
    "BaseInlineFormSet",
    "inlineformset_factory",
    "modelform_factory",
)

ALL_FIELDS = "__all__"


def construct_instance(form, instance, fields=None, exclude=None):
    """
    Construct and return a model instance from the bound ``form``'s
    ``cleaned_data``, but do not save the returned instance to the database.
    """
    from django.db import models

    opts = instance._meta

    cleaned_data = form.cleaned_data
    file_field_list = []
    for f in opts.fields:
        if (
            not f.editable
            or isinstance(f, models.AutoField)
            or f.name not in cleaned_data
        ):
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        # Leave defaults for fields that aren't in POST data, except for
        # checkbox inputs because they don't appear in POST data if not checked.
        if (
            f.has_default()
            and form[f.name].field.widget.value_omitted_from_data(
                form.data, form.files, form.add_prefix(f.name)
            )
            and cleaned_data.get(f.name) in form[f.name].field.empty_values
        ):
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


# ModelForms #################################################################


def model_to_dict(instance, fields=None, exclude=None):
    """
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, return only the
    named.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if not getattr(f, "editable", False):
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = f.value_from_object(instance)
    return data


def apply_limit_choices_to_to_formfield(formfield):
    """Apply limit_choices_to to the formfield's queryset if needed."""
    from django.db.models import Exists, OuterRef, Q

    if hasattr(formfield, "queryset") and hasattr(formfield, "get_limit_choices_to"):
        limit_choices_to = formfield.get_limit_choices_to()
        if limit_choices_to:
            complex_filter = limit_choices_to
            if not isinstance(complex_filter, Q):
                complex_filter = Q(**limit_choices_to)
            complex_filter &= Q(pk=OuterRef("pk"))
            # Use Exists() to avoid potential duplicates.
            formfield.queryset = formfield.queryset.filter(
                Exists(formfield.queryset.model._base_manager.filter(complex_filter)),
            )


def fields_for_model(
    model,
    fields=None,
    exclude=None,
    widgets=None,
    formfield_callback=None,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    field_classes=None,
    *,
    apply_limit_choices_to=True,
    form_declared_fields=None,
):
    """
    Return a dictionary containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, return only the
    named fields.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named fields from the returned fields, even if they are listed in the
    ``fields`` argument.

    ``widgets`` is a dictionary of model field names mapped to a widget.

    ``formfield_callback`` is a callable that takes a model field and returns
    a form field.

    ``localized_fields`` is a list of names of fields which should be localized.

    ``labels`` is a dictionary of model field names mapped to a label.

    ``help_texts`` is a dictionary of model field names mapped to a help text.

    ``error_messages`` is a dictionary of model field names mapped to a
    dictionary of error messages.

    ``field_classes`` is a dictionary of model field names mapped to a form
    field class.

    ``apply_limit_choices_to`` is a boolean indicating if limit_choices_to
    should be applied to a field's queryset.

    ``form_declared_fields`` is a dictionary of form fields created directly on
    a form.
    """
    form_declared_fields = form_declared_fields or {}
    field_dict = {}
    ignored = []
    opts = model._meta
    # Avoid circular import
    from django.db.models import Field as ModelField

    sortable_private_fields = [
        f for f in opts.private_fields if isinstance(f, ModelField)
    ]
    for f in sorted(
        chain(opts.concrete_fields, sortable_private_fields, opts.many_to_many)
    ):
        if not getattr(f, "editable", False):
            if (
                fields is not None
                and f.name in fields
                and (exclude is None or f.name not in exclude)
            ):
                raise FieldError(
                    "'%s' cannot be specified for %s model form as it is a "
                    "non-editable field" % (f.name, model.__name__)
                )
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if f.name in form_declared_fields:
            field_dict[f.name] = form_declared_fields[f.name]
            continue

        kwargs = {}
        if widgets and f.name in widgets:
            kwargs["widget"] = widgets[f.name]
        if localized_fields == ALL_FIELDS or (
            localized_fields and f.name in localized_fields
        ):
            kwargs["localize"] = True
        if labels and f.name in labels:
            kwargs["label"] = labels[f.name]
        if help_texts and f.name in help_texts:
            kwargs["help_text"] = help_texts[f.name]
        if error_messages and f.name in error_messages:
            kwargs["error_messages"] = error_messages[f.name]
        if field_classes and f.name in field_classes:
            kwargs["form_class"] = field_classes[f.name]

        if formfield_callback is None:
            formfield = f.formfield(**kwargs)
        elif not callable(formfield_callback):
            raise TypeError("formfield_callback must be a function or callable")
        else:
            formfield = formfield_callback(f, **kwargs)

        if formfield:
            if apply_limit_choices_to:
                apply_limit_choices_to_to_formfield(formfield)
            field_dict[f.name] = formfield
        else:
            ignored.append(f.name)
    if fields:
        field_dict = {
            f: field_dict.get(f)
            for f in fields
            if (not exclude or f not in exclude) and f not in ignored
        }
    return field_dict


class ModelFormOptions:
    def __init__(self, options=None):
        self.model = getattr(options, "model", None)
        self.fields = getattr(options, "fields", None)
        self.exclude = getattr(options, "exclude", None)
        self.widgets = getattr(options, "widgets", None)
        self.localized_fields = getattr(options, "localized_fields", None)
        self.labels = getattr(options, "labels", None)
        self.help_texts = getattr(options, "help_texts", None)
        self.error_messages = getattr(options, "error_messages", None)
        self.field_classes = getattr(options, "field_classes", None)
        self.formfield_callback = getattr(options, "formfield_callback", None)


class ModelFormMetaclass(DeclarativeFieldsMetaclass):
    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)

        if bases == (BaseModelForm,):
            return new_class

        opts = new_class._meta = ModelFormOptions(getattr(new_class, "Meta", None))

        # We check if a string was passed to `fields` or `exclude`,
        # which is likely to be a mistake where the user typed ('foo') instead
        # of ('foo',)
        for opt in ["fields", "exclude", "localized_fields"]:
            value = getattr(opts, opt)
            if isinstance(value, str) and value != ALL_FIELDS:
                msg = (
                    "%(model)s.Meta.%(opt)s cannot be a string. "
                    "Did you mean to type: ('%(value)s',)?"
                    % {
                        "model": new_class.__name__,
                        "opt": opt,
                        "value": value,
                    }
                )
                raise TypeError(msg)

        if opts.model:
            # If a model is defined, extract form fields from it.
            if opts.fields is None and opts.exclude is None:
                raise ImproperlyConfigured(
                    "Creating a ModelForm without either the 'fields' attribute "
                    "or the 'exclude' attribute is prohibited; form %s "
                    "needs updating." % name
                )

            if opts.fields == ALL_FIELDS:
                # Sentinel for fields_for_model to indicate "get the list of
                # fields from the model"
                opts.fields = None

            fields = fields_for_model(
                opts.model,
                opts.fields,
                opts.exclude,
                opts.widgets,
                opts.formfield_callback,
                opts.localized_fields,
                opts.labels,
                opts.help_texts,
                opts.error_messages,
                opts.field_classes,
                # limit_choices_to will be applied during ModelForm.__init__().
                apply_limit_choices_to=False,
                form_declared_fields=new_class.declared_fields,
            )

            # make sure opts.fields doesn't specify an invalid field
            none_model_fields = {k for k, v in fields.items() if not v}
            missing_fields = none_model_fields.difference(new_class.declared_fields)
            if missing_fields:
                message = "Unknown field(s) (%s) specified for %s"
                message %= (", ".join(missing_fields), opts.model.__name__)
                raise FieldError(message)
            # Include all the other declared fields.
            fields.update(new_class.declared_fields)
        else:
            fields = new_class.declared_fields

        new_class.base_fields = fields

        return new_class


class BaseModelForm(BaseForm, AltersData):
    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=None,
        empty_permitted=False,
        instance=None,
        use_required_attribute=None,
        renderer=None,
    ):
        opts = self._meta
        if opts.model is None:
            raise ValueError("ModelForm has no model class specified.")
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
        # self._validate_unique will be set to True by BaseModelForm.clean().
        # It is False by default so overriding self.clean() and failing to call
        # super will stop validate_unique from being called.
        self._validate_unique = False
        super().__init__(
            data,
            files,
            auto_id,
            prefix,
            object_data,
            error_class,
            label_suffix,
            empty_permitted,
            use_required_attribute=use_required_attribute,
            renderer=renderer,
        )
        for formfield in self.fields.values():
            apply_limit_choices_to_to_formfield(formfield)

    def _get_validation_exclusions(self):
        """
        For backwards-compatibility, exclude several types of fields from model
        validation. See tickets #12507, #12521, #12553.
        """
        exclude = set()
        # Build up a list of fields that should be excluded from model field
        # validation and unique checks.
        for f in self.instance._meta.fields:
            field = f.name
            # Exclude fields that aren't on the form. The developer may be
            # adding these values to the model after form validation.
            if field not in self.fields:
                exclude.add(f.name)

            # Don't perform model validation on fields that were defined
            # manually on the form and excluded via the ModelForm's Meta
            # class. See #12901.
            elif self._meta.fields and field not in self._meta.fields:
                exclude.add(f.name)
            elif self._meta.exclude and field in self._meta.exclude:
                exclude.add(f.name)

            # Exclude fields that failed form validation. There's no need for
            # the model fields to validate them as well.
            elif field in self._errors:
                exclude.add(f.name)

            # Exclude empty fields that are not required by the form, if the
            # underlying model field is required. This keeps the model field
            # from raising a required error. Note: don't exclude the field from
            # validation if the model field allows blanks. If it does, the blank
            # value may be included in a unique check, so cannot be excluded
            # from validation.
            else:
                form_field = self.fields[field]
                field_value = self.cleaned_data.get(field)
                if (
                    not f.blank
                    and not form_field.required
                    and field_value in form_field.empty_values
                ):
                    exclude.add(f.name)
        return exclude

    def clean(self):
        self._validate_unique = True
        return self.cleaned_data

    def _update_errors(self, errors):
        # Override any validation error messages defined at the model level
        # with those defined at the form level.
        opts = self._meta

        # Allow the model generated by construct_instance() to raise
        # ValidationError and have them handled in the same way as others.
        if hasattr(errors, "error_dict"):
            error_dict = errors.error_dict
        else:
            error_dict = {NON_FIELD_ERRORS: errors}

        for field, messages in error_dict.items():
            if (
                field == NON_FIELD_ERRORS
                and opts.error_messages
                and NON_FIELD_ERRORS in opts.error_messages
            ):
                error_messages = opts.error_messages[NON_FIELD_ERRORS]
            elif field in self.fields:
                error_messages = self.fields[field].error_messages
            else:
                continue

            for message in messages:
                if (
                    isinstance(message, ValidationError)
                    and message.code in error_messages
                ):
                    message.message = error_messages[message.code]

        self.add_error(None, errors)

    def _post_clean(self):
        opts = self._meta

        exclude = self._get_validation_exclusions()

        # Foreign Keys being used to represent inline relationships
        # are excluded from basic field value validation. This is for two
        # reasons: firstly, the value may not be supplied (#12507; the
        # case of providing new values to the admin); secondly the
        # object being referred to may not yet fully exist (#12749).
        # However, these fields *must* be included in uniqueness checks,
        # so this can't be part of _get_validation_exclusions().
        for name, field in self.fields.items():
            if isinstance(field, InlineForeignKeyField):
                exclude.add(name)

        try:
            self.instance = construct_instance(
                self, self.instance, opts.fields, opts.exclude
            )
        except ValidationError as e:
            self._update_errors(e)

        try:
            self.instance.full_clean(exclude=exclude, validate_unique=False)
        except ValidationError as e:
            self._update_errors(e)

        # Validate uniqueness if needed.
        if self._validate_unique:
            self.validate_unique()

    def validate_unique(self):
        """
        Call the instance's validate_unique() method and update the form's
        validation errors if any were raised.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)

    def _save_m2m(self):
        """
        Save the many-to-many fields and generic relations for this form.
        """
        cleaned_data = self.cleaned_data
        exclude = self._meta.exclude
        fields = self._meta.fields
        opts = self.instance._meta
        # Note that for historical reasons we want to include also
        # private_fields here. (GenericRelation was previously a fake
        # m2m field).
        for f in chain(opts.many_to_many, opts.private_fields):
            if not hasattr(f, "save_form_data"):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                f.save_form_data(self.instance, cleaned_data[f.name])

    def save(self, commit=True):
        """
        Save this form's self.instance object if commit=True. Otherwise, add
        a save_m2m() method to the form which can be called after the instance
        is saved manually at a later time. Return the model instance.
        """
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate."
                % (
                    self.instance._meta.object_name,
                    "created" if self.instance._state.adding else "changed",
                )
            )
        if commit:
            # If committing, save the instance and the m2m data immediately.
            self.instance.save()
            self._save_m2m()
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.save_m2m = self._save_m2m
        return self.instance

    save.alters_data = True


class ModelForm(BaseModelForm, metaclass=ModelFormMetaclass):
    pass


def modelform_factory(
    model,
    form=ModelForm,
    fields=None,
    exclude=None,
    formfield_callback=None,
    widgets=None,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    field_classes=None,
):
    """
    Return a ModelForm containing form fields for the given model. You can
    optionally pass a `form` argument to use as a starting point for
    constructing the ModelForm.

    ``fields`` is an optional list of field names. If provided, include only
    the named fields in the returned fields. If omitted or '__all__', use all
    fields.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named fields from the returned fields, even if they are listed in the
    ``fields`` argument.

    ``widgets`` is a dictionary of model field names mapped to a widget.

    ``localized_fields`` is a list of names of fields which should be localized.

    ``formfield_callback`` is a callable that takes a model field and returns
    a form field.

    ``labels`` is a dictionary of model field names mapped to a label.

    ``help_texts`` is a dictionary of model field names mapped to a help text.

    ``error_messages`` is a dictionary of model field names mapped to a
    dictionary of error messages.

    ``field_classes`` is a dictionary of model field names mapped to a form
    field class.
    """
    # Create the inner Meta class. FIXME: ideally, we should be able to
    # construct a ModelForm without creating and passing in a temporary
    # inner class.

    # Build up a list of attributes that the Meta object will have.
    attrs = {"model": model}
    if fields is not None:
        attrs["fields"] = fields
    if exclude is not None:
        attrs["exclude"] = exclude
    if widgets is not None:
        attrs["widgets"] = widgets
    if localized_fields is not None:
        attrs["localized_fields"] = localized_fields
    if labels is not None:
        attrs["labels"] = labels
    if help_texts is not None:
        attrs["help_texts"] = help_texts
    if error_messages is not None:
        attrs["error_messages"] = error_messages
    if field_classes is not None:
        attrs["field_classes"] = field_classes

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    bases = (form.Meta,) if hasattr(form, "Meta") else ()
    Meta = type("Meta", bases, attrs)
    if formfield_callback:
        Meta.formfield_callback = staticmethod(formfield_callback)
    # Give this new form class a reasonable name.
    class_name = model.__name__ + "Form"

    # Class attributes for the new form class.
    form_class_attrs = {"Meta": Meta}

    if getattr(Meta, "fields", None) is None and getattr(Meta, "exclude", None) is None:
        raise ImproperlyConfigured(
            "Calling modelform_factory without defining 'fields' or "
            "'exclude' explicitly is prohibited."
        )

    # Instantiate type(form) in order to use the same metaclass as form.
    return type(form)(class_name, (form,), form_class_attrs)


# ModelFormSets ##############################################################


class BaseModelFormSet(BaseFormSet, AltersData):
    """
    A ``FormSet`` for editing a queryset and/or adding new objects to it.
    """

    model = None
    edit_only = False

    # Set of fields that must be unique among forms of this set.
    unique_fields = set()

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        queryset=None,
        *,
        initial=None,
        **kwargs,
    ):
        self.queryset = queryset
        self.initial_extra = initial
        super().__init__(
            **{
                "data": data,
                "files": files,
                "auto_id": auto_id,
                "prefix": prefix,
                **kwargs,
            }
        )

    def initial_form_count(self):
        """Return the number of forms that are required in this FormSet."""
        if not self.is_bound:
            return len(self.get_queryset())
        return super().initial_form_count()

    def _existing_object(self, pk):
        if not hasattr(self, "_object_dict"):
            self._object_dict = {o.pk: o for o in self.get_queryset()}
        return self._object_dict.get(pk)

    def _get_to_python(self, field):
        """
        If the field is a related field, fetch the concrete field's (that
        is, the ultimate pointed-to field's) to_python.
        """
        while field.remote_field is not None:
            field = field.remote_field.get_related_field()
        return field.to_python

    def _construct_form(self, i, **kwargs):
        pk_required = i < self.initial_form_count()
        if pk_required:
            if self.is_bound:
                pk_key = "%s-%s" % (self.add_prefix(i), self.model._meta.pk.name)
                try:
                    pk = self.data[pk_key]
                except KeyError:
                    # The primary key is missing. The user may have tampered
                    # with POST data.
                    pass
                else:
                    to_python = self._get_to_python(self.model._meta.pk)
                    try:
                        pk = to_python(pk)
                    except ValidationError:
                        # The primary key exists but is an invalid value. The
                        # user may have tampered with POST data.
                        pass
                    else:
                        kwargs["instance"] = self._existing_object(pk)
            else:
                kwargs["instance"] = self.get_queryset()[i]
        elif self.initial_extra:
            # Set initial values for extra forms
            try:
                kwargs["initial"] = self.initial_extra[i - self.initial_form_count()]
            except IndexError:
                pass
        form = super()._construct_form(i, **kwargs)
        if pk_required:
            form.fields[self.model._meta.pk.name].required = True
        return form

    def get_queryset(self):
        if not hasattr(self, "_queryset"):
            if self.queryset is not None:
                qs = self.queryset
            else:
                qs = self.model._default_manager.get_queryset()

            # If the queryset isn't already ordered we need to add an
            # artificial ordering here to make sure that all formsets
            # constructed from this queryset have the same form order.
            if not qs.ordered:
                qs = qs.order_by(self.model._meta.pk.name)

            # Removed queryset limiting here. As per discussion re: #13023
            # on django-dev, max_num should not prevent existing
            # related objects/inlines from being displayed.
            self._queryset = qs
        return self._queryset

    def save_new(self, form, commit=True):
        """Save and return a new model instance for the given form."""
        return form.save(commit=commit)

    def save_existing(self, form, obj, commit=True):
        """Save and return an existing model instance for the given form."""
        return form.save(commit=commit)

    def delete_existing(self, obj, commit=True):
        """Deletes an existing model instance."""
        if commit:
            obj.delete()

    def save(self, commit=True):
        """
        Save model instances for every form, adding and changing instances
        as necessary, and return the list of instances.
        """
        if not commit:
            self.saved_forms = []

            def save_m2m():
                for form in self.saved_forms:
                    form.save_m2m()

            self.save_m2m = save_m2m
        if self.edit_only:
            return self.save_existing_objects(commit)
        else:
            return self.save_existing_objects(commit) + self.save_new_objects(commit)

    save.alters_data = True

    def clean(self):
        self.validate_unique()

    def validate_unique(self):
        # Collect unique_checks and date_checks to run from all the forms.
        all_unique_checks = set()
        all_date_checks = set()
        forms_to_delete = self.deleted_forms
        valid_forms = [
            form
            for form in self.forms
            if form.is_valid() and form not in forms_to_delete
        ]
        for form in valid_forms:
            exclude = form._get_validation_exclusions()
            unique_checks, date_checks = form.instance._get_unique_checks(
                exclude=exclude,
                include_meta_constraints=True,
            )
            all_unique_checks.update(unique_checks)
            all_date_checks.update(date_checks)

        errors = []
        # Do each of the unique checks (unique and unique_together)
        for uclass, unique_check in all_unique_checks:
            seen_data = set()
            for form in valid_forms:
                # Get the data for the set of fields that must be unique among
                # the forms.
                row_data = (
                    field if field in self.unique_fields else form.cleaned_data[field]
                    for field in unique_check
                    if field in form.cleaned_data
                )
                # Reduce Model instances to their primary key values
                row_data = tuple(
                    (
                        d._get_pk_val()
                        if hasattr(d, "_get_pk_val")
                        # Prevent "unhashable type" errors later on.
                        else make_hashable(d)
                    )
                    for d in row_data
                )
                if row_data and None not in row_data:
                    # if we've already seen it then we have a uniqueness failure
                    if row_data in seen_data:
                        # poke error messages into the right places and mark
                        # the form as invalid
                        errors.append(self.get_unique_error_message(unique_check))
                        form._errors[NON_FIELD_ERRORS] = self.error_class(
                            [self.get_form_error()],
                            renderer=self.renderer,
                        )
                        # Remove the data from the cleaned_data dict since it
                        # was invalid.
                        for field in unique_check:
                            if field in form.cleaned_data:
                                del form.cleaned_data[field]
                    # mark the data as seen
                    seen_data.add(row_data)
        # iterate over each of the date checks now
        for date_check in all_date_checks:
            seen_data = set()
            uclass, lookup, field, unique_for = date_check
            for form in valid_forms:
                # see if we have data for both fields
                if (
                    form.cleaned_data
                    and form.cleaned_data[field] is not None
                    and form.cleaned_data[unique_for] is not None
                ):
                    # if it's a date lookup we need to get the data for all the fields
                    if lookup == "date":
                        date = form.cleaned_data[unique_for]
                        date_data = (date.year, date.month, date.day)
                    # otherwise it's just the attribute on the date/datetime
                    # object
                    else:
                        date_data = (getattr(form.cleaned_data[unique_for], lookup),)
                    data = (form.cleaned_data[field],) + date_data
                    # if we've already seen it then we have a uniqueness failure
                    if data in seen_data:
                        # poke error messages into the right places and mark
                        # the form as invalid
                        errors.append(self.get_date_error_message(date_check))
                        form._errors[NON_FIELD_ERRORS] = self.error_class(
                            [self.get_form_error()],
                            renderer=self.renderer,
                        )
                        # Remove the data from the cleaned_data dict since it
                        # was invalid.
                        del form.cleaned_data[field]
                    # mark the data as seen
                    seen_data.add(data)

        if errors:
            raise ValidationError(errors)

    def get_unique_error_message(self, unique_check):
        if len(unique_check) == 1:
            return gettext("Please correct the duplicate data for %(field)s.") % {
                "field": unique_check[0],
            }
        else:
            return gettext(
                "Please correct the duplicate data for %(field)s, which must be unique."
            ) % {
                "field": get_text_list(unique_check, _("and")),
            }

    def get_date_error_message(self, date_check):
        return gettext(
            "Please correct the duplicate data for %(field_name)s "
            "which must be unique for the %(lookup)s in %(date_field)s."
        ) % {
            "field_name": date_check[2],
            "date_field": date_check[3],
            "lookup": str(date_check[1]),
        }

    def get_form_error(self):
        return gettext("Please correct the duplicate values below.")

    def save_existing_objects(self, commit=True):
        self.changed_objects = []
        self.deleted_objects = []
        if not self.initial_forms:
            return []

        saved_instances = []
        forms_to_delete = self.deleted_forms
        for form in self.initial_forms:
            obj = form.instance
            # If the pk is None, it means either:
            # 1. The object is an unexpected empty model, created by invalid
            #    POST data such as an object outside the formset's queryset.
            # 2. The object was already deleted from the database.
            if not obj._is_pk_set():
                continue
            if form in forms_to_delete:
                self.deleted_objects.append(obj)
                self.delete_existing(obj, commit=commit)
            elif form.has_changed():
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
            if self.can_delete and self._should_delete_form(form):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
            if not commit:
                self.saved_forms.append(form)
        return self.new_objects

    def add_fields(self, form, index):
        """Add a hidden field for the object's primary key."""
        from django.db.models import AutoField, ForeignKey, OneToOneField

        self._pk_field = pk = self.model._meta.pk
        # If a pk isn't editable, then it won't be on the form, so we need to
        # add it here so we can tell which object is which when we get the
        # data back. Generally, pk.editable should be false, but for some
        # reason, auto_created pk fields and AutoField's editable attribute is
        # True, so check for that as well.

        def pk_is_not_editable(pk):
            return (
                (not pk.editable)
                or (pk.auto_created or isinstance(pk, AutoField))
                or (
                    pk.remote_field
                    and pk.remote_field.parent_link
                    and pk_is_not_editable(pk.remote_field.model._meta.pk)
                )
            )

        if pk_is_not_editable(pk) or pk.name not in form.fields:
            if form.is_bound:
                # If we're adding the related instance, ignore its primary key
                # as it could be an auto-generated default which isn't actually
                # in the database.
                pk_value = None if form.instance._state.adding else form.instance.pk
            else:
                try:
                    if index is not None:
                        pk_value = self.get_queryset()[index].pk
                    else:
                        pk_value = None
                except IndexError:
                    pk_value = None
            if isinstance(pk, (ForeignKey, OneToOneField)):
                qs = pk.remote_field.model._default_manager.get_queryset()
            else:
                qs = self.model._default_manager.get_queryset()
            qs = qs.using(form.instance._state.db)
            if form._meta.widgets:
                widget = form._meta.widgets.get(self._pk_field.name, HiddenInput)
            else:
                widget = HiddenInput
            form.fields[self._pk_field.name] = ModelChoiceField(
                qs, initial=pk_value, required=False, widget=widget
            )
        super().add_fields(form, index)


def modelformset_factory(
    model,
    form=ModelForm,
    formfield_callback=None,
    formset=BaseModelFormSet,
    extra=1,
    can_delete=False,
    can_order=False,
    max_num=None,
    fields=None,
    exclude=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    absolute_max=None,
    can_delete_extra=True,
    renderer=None,
    edit_only=False,
):
    """Return a FormSet class for the given Django model class."""
    meta = getattr(form, "Meta", None)
    if (
        getattr(meta, "fields", fields) is None
        and getattr(meta, "exclude", exclude) is None
    ):
        raise ImproperlyConfigured(
            "Calling modelformset_factory without defining 'fields' or "
            "'exclude' explicitly is prohibited."
        )

    form = modelform_factory(
        model,
        form=form,
        fields=fields,
        exclude=exclude,
        formfield_callback=formfield_callback,
        widgets=widgets,
        localized_fields=localized_fields,
        labels=labels,
        help_texts=help_texts,
        error_messages=error_messages,
        field_classes=field_classes,
    )
    FormSet = formset_factory(
        form,
        formset,
        extra=extra,
        min_num=min_num,
        max_num=max_num,
        can_order=can_order,
        can_delete=can_delete,
        validate_min=validate_min,
        validate_max=validate_max,
        absolute_max=absolute_max,
        can_delete_extra=can_delete_extra,
        renderer=renderer,
    )
    FormSet.model = model
    FormSet.edit_only = edit_only
    return FormSet


# InlineFormSets #############################################################


class BaseInlineFormSet(BaseModelFormSet):
    """A formset for child objects related to a parent."""

    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        save_as_new=False,
        prefix=None,
        queryset=None,
        **kwargs,
    ):
        if instance is None:
            self.instance = self.fk.remote_field.model()
        else:
            self.instance = instance
        self.save_as_new = save_as_new
        if queryset is None:
            queryset = self.model._default_manager
        if self.instance._is_pk_set():
            qs = queryset.filter(**{self.fk.name: self.instance})
        else:
            qs = queryset.none()
        self.unique_fields = {self.fk.name}
        super().__init__(data, files, prefix=prefix, queryset=qs, **kwargs)

        # Add the generated field to form._meta.fields if it's defined to make
        # sure validation isn't skipped on that field.
        if self.form._meta.fields and self.fk.name not in self.form._meta.fields:
            if isinstance(self.form._meta.fields, tuple):
                self.form._meta.fields = list(self.form._meta.fields)
            self.form._meta.fields.append(self.fk.name)

    def initial_form_count(self):
        if self.save_as_new:
            return 0
        return super().initial_form_count()

    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        if self.save_as_new:
            mutable = getattr(form.data, "_mutable", None)
            # Allow modifying an immutable QueryDict.
            if mutable is not None:
                form.data._mutable = True
            # Remove the primary key from the form's data, we are only
            # creating new instances
            form.data[form.add_prefix(self._pk_field.name)] = None
            # Remove the foreign key from the form's data
            form.data[form.add_prefix(self.fk.name)] = None
            if mutable is not None:
                form.data._mutable = mutable

        # Set the fk value here so that the form can do its validation.
        fk_value = self.instance.pk
        if self.fk.remote_field.field_name != self.fk.remote_field.model._meta.pk.name:
            fk_value = getattr(self.instance, self.fk.remote_field.field_name)
            fk_value = getattr(fk_value, "pk", fk_value)
        setattr(form.instance, self.fk.attname, fk_value)
        return form

    @classmethod
    def get_default_prefix(cls):
        return cls.fk.remote_field.get_accessor_name(model=cls.model).replace("+", "")

    def save_new(self, form, commit=True):
        # Ensure the latest copy of the related instance is present on each
        # form (it may have been saved after the formset was originally
        # instantiated).
        setattr(form.instance, self.fk.name, self.instance)
        return super().save_new(form, commit=commit)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if self._pk_field == self.fk:
            name = self._pk_field.name
            kwargs = {"pk_field": True}
        else:
            # The foreign key field might not be on the form, so we poke at the
            # Model field to get the label, since we need that for error messages.
            name = self.fk.name
            kwargs = {
                "label": getattr(
                    form.fields.get(name), "label", capfirst(self.fk.verbose_name)
                )
            }

        # The InlineForeignKeyField assumes that the foreign key relation is
        # based on the parent model's pk. If this isn't the case, set to_field
        # to correctly resolve the initial form value.
        if self.fk.remote_field.field_name != self.fk.remote_field.model._meta.pk.name:
            kwargs["to_field"] = self.fk.remote_field.field_name

        # If we're adding a new object, ignore a parent's auto-generated key
        # as it will be regenerated on the save request.
        if self.instance._state.adding:
            if kwargs.get("to_field") is not None:
                to_field = self.instance._meta.get_field(kwargs["to_field"])
            else:
                to_field = self.instance._meta.pk

            if to_field.has_default() and (
                # Don't ignore a parent's auto-generated key if it's not the
                # parent model's pk and form data is provided.
                to_field.attname == self.fk.remote_field.model._meta.pk.name
                or not form.data
            ):
                setattr(self.instance, to_field.attname, None)

        form.fields[name] = InlineForeignKeyField(self.instance, **kwargs)

    def get_unique_error_message(self, unique_check):
        unique_check = [field for field in unique_check if field != self.fk.name]
        return super().get_unique_error_message(unique_check)


def _get_foreign_key(parent_model, model, fk_name=None, can_fail=False):
    """
    Find and return the ForeignKey from model to parent if there is one
    (return None if can_fail is True and no such field exists). If fk_name is
    provided, assume it is the name of the ForeignKey field. Unless can_fail is
    True, raise an exception if there isn't a ForeignKey from model to
    parent_model.
    """
    # avoid circular import
    from django.db.models import ForeignKey

    opts = model._meta
    if fk_name:
        fks_to_parent = [f for f in opts.fields if f.name == fk_name]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
            all_parents = (*parent_model._meta.all_parents, parent_model)
            if (
                not isinstance(fk, ForeignKey)
                or (
                    # ForeignKey to proxy models.
                    fk.remote_field.model._meta.proxy
                    and fk.remote_field.model._meta.proxy_for_model not in all_parents
                )
                or (
                    # ForeignKey to concrete models.
                    not fk.remote_field.model._meta.proxy
                    and fk.remote_field.model != parent_model
                    and fk.remote_field.model not in all_parents
                )
            ):
                raise ValueError(
                    "fk_name '%s' is not a ForeignKey to '%s'."
                    % (fk_name, parent_model._meta.label)
                )
        elif not fks_to_parent:
            raise ValueError(
                "'%s' has no field named '%s'." % (model._meta.label, fk_name)
            )
    else:
        # Try to discover what the ForeignKey from model to parent_model is
        all_parents = (*parent_model._meta.all_parents, parent_model)
        fks_to_parent = [
            f
            for f in opts.fields
            if isinstance(f, ForeignKey)
            and (
                f.remote_field.model == parent_model
                or f.remote_field.model in all_parents
                or (
                    f.remote_field.model._meta.proxy
                    and f.remote_field.model._meta.proxy_for_model in all_parents
                )
            )
        ]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
        elif not fks_to_parent:
            if can_fail:
                return
            raise ValueError(
                "'%s' has no ForeignKey to '%s'."
                % (
                    model._meta.label,
                    parent_model._meta.label,
                )
            )
        else:
            raise ValueError(
                "'%s' has more than one ForeignKey to '%s'. You must specify "
                "a 'fk_name' attribute."
                % (
                    model._meta.label,
                    parent_model._meta.label,
                )
            )
    return fk


def inlineformset_factory(
    parent_model,
    model,
    form=ModelForm,
    formset=BaseInlineFormSet,
    fk_name=None,
    fields=None,
    exclude=None,
    extra=3,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    absolute_max=None,
    can_delete_extra=True,
    renderer=None,
    edit_only=False,
):
    """
    Return an ``InlineFormSet`` for the given kwargs.

    ``fk_name`` must be provided if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    fk = _get_foreign_key(parent_model, model, fk_name=fk_name)
    # enforce a max_num=1 when the foreign key to the parent model is unique.
    if fk.unique:
        max_num = 1
    kwargs = {
        "form": form,
        "formfield_callback": formfield_callback,
        "formset": formset,
        "extra": extra,
        "can_delete": can_delete,
        "can_order": can_order,
        "fields": fields,
        "exclude": exclude,
        "min_num": min_num,
        "max_num": max_num,
        "widgets": widgets,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "localized_fields": localized_fields,
        "labels": labels,
        "help_texts": help_texts,
        "error_messages": error_messages,
        "field_classes": field_classes,
        "absolute_max": absolute_max,
        "can_delete_extra": can_delete_extra,
        "renderer": renderer,
        "edit_only": edit_only,
    }
    FormSet = modelformset_factory(model, **kwargs)
    FormSet.fk = fk
    return FormSet


# Fields #####################################################################


class InlineForeignKeyField(Field):
    """
    A basic integer field that deals with validating the given value to a
    given parent instance in an inline.
    """

    widget = HiddenInput
    default_error_messages = {
        "invalid_choice": _("The inline value did not match the parent instance."),
    }

    def __init__(self, parent_instance, *args, pk_field=False, to_field=None, **kwargs):
        self.parent_instance = parent_instance
        self.pk_field = pk_field
        self.to_field = to_field
        if self.parent_instance is not None:
            if self.to_field:
                kwargs["initial"] = getattr(self.parent_instance, self.to_field)
            else:
                kwargs["initial"] = self.parent_instance.pk
        kwargs["required"] = False
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if value in self.empty_values:
            if self.pk_field:
                return None
            # if there is no value act as we did before.
            return self.parent_instance
        # ensure the we compare the values as equal types.
        if self.to_field:
            orig = getattr(self.parent_instance, self.to_field)
        else:
            orig = self.parent_instance.pk
        if str(value) != str(orig):
            raise ValidationError(
                self.error_messages["invalid_choice"], code="invalid_choice"
            )
        return self.parent_instance

    def has_changed(self, initial, data):
        return False


class ModelChoiceIteratorValue:
    def __init__(self, value, instance):
        self.value = value
        self.instance = instance

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if isinstance(other, ModelChoiceIteratorValue):
            other = other.value
        return self.value == other


class ModelChoiceIterator(BaseChoiceIterator):
    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        queryset = self.queryset
        # Can't use iterator() when queryset uses prefetch_related()
        if not queryset._prefetch_related_lookups:
            queryset = queryset.iterator()
        for obj in queryset:
            yield self.choice(obj)

    def __len__(self):
        # count() adds a query but uses less memory since the QuerySet results
        # won't be cached. In most cases, the choices will only be iterated on,
        # and __len__() won't be called.
        return self.queryset.count() + (1 if self.field.empty_label is not None else 0)

    def __bool__(self):
        return self.field.empty_label is not None or self.queryset.exists()

    def choice(self, obj):
        return (
            ModelChoiceIteratorValue(self.field.prepare_value(obj), obj),
            self.field.label_from_instance(obj),
        )


class ModelChoiceField(ChoiceField):
    """A ChoiceField whose choices are a model QuerySet."""

    # This class is a subclass of ChoiceField for purity, but it doesn't
    # actually use any of ChoiceField's implementation.
    default_error_messages = {
        "invalid_choice": _(
            "Select a valid choice. That choice is not one of the available choices."
        ),
    }
    iterator = ModelChoiceIterator

    def __init__(
        self,
        queryset,
        *,
        empty_label="---------",
        required=True,
        widget=None,
        label=None,
        initial=None,
        help_text="",
        to_field_name=None,
        limit_choices_to=None,
        blank=False,
        **kwargs,
    ):
        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        Field.__init__(
            self,
            required=required,
            widget=widget,
            label=label,
            initial=initial,
            help_text=help_text,
            **kwargs,
        )
        if (required and initial is not None) or (
            isinstance(self.widget, RadioSelect) and not blank
        ):
            self.empty_label = None
        else:
            self.empty_label = empty_label
        self.queryset = queryset
        self.limit_choices_to = limit_choices_to  # limit the queryset later.
        self.to_field_name = to_field_name

    def validate_no_null_characters(self, value):
        non_null_character_validator = ProhibitNullCharactersValidator()
        return non_null_character_validator(value)

    def get_limit_choices_to(self):
        """
        Return ``limit_choices_to`` for this form field.

        If it is a callable, invoke it and return the result.
        """
        if callable(self.limit_choices_to):
            return self.limit_choices_to()
        return self.limit_choices_to

    def __deepcopy__(self, memo):
        result = super(ChoiceField, self).__deepcopy__(memo)
        # Need to force a new ModelChoiceIterator to be created, bug #11183
        if self.queryset is not None:
            result.queryset = self.queryset.all()
        return result

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = None if queryset is None else queryset.all()
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    # this method will be used to create object labels by the QuerySetIterator.
    # Override it to customize the label.
    def label_from_instance(self, obj):
        """
        Convert objects into strings and generate the labels for the choices
        presented by this object. Subclasses can override this method to
        customize the display of the choices.
        """
        return str(obj)

    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, "_choices"):
            return self._choices

        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh ModelChoiceIterator that has not been
        # consumed. Note that we're instantiating a new ModelChoiceIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        return self.iterator(self)

    choices = property(_get_choices, ChoiceField.choices.fset)

    def prepare_value(self, value):
        if hasattr(value, "_meta"):
            if self.to_field_name:
                return value.serializable_value(self.to_field_name)
            else:
                return value.pk
        return super().prepare_value(value)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        self.validate_no_null_characters(value)
        try:
            key = self.to_field_name or "pk"
            if isinstance(value, self.queryset.model):
                value = getattr(value, key)
            value = self.queryset.get(**{key: value})
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )
        return value

    def validate(self, value):
        return Field.validate(self, value)

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        initial_value = initial if initial is not None else ""
        data_value = data if data is not None else ""
        return str(self.prepare_value(initial_value)) != str(data_value)


class ModelMultipleChoiceField(ModelChoiceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""

    widget = SelectMultiple
    hidden_widget = MultipleHiddenInput
    default_error_messages = {
        "invalid_list": _("Enter a list of values."),
        "invalid_choice": _(
            "Select a valid choice. %(value)s is not one of the available choices."
        ),
        "invalid_pk_value": _("“%(pk)s” is not a valid value."),
    }

    def __init__(self, queryset, **kwargs):
        super().__init__(queryset, empty_label=None, **kwargs)

    def to_python(self, value):
        if not value:
            return []
        return list(self._check_values(value))

    def clean(self, value):
        value = self.prepare_value(value)
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")
        elif not self.required and not value:
            return self.queryset.none()
        if not isinstance(value, (list, tuple)):
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            )
        qs = self._check_values(value)
        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return qs

    def _check_values(self, value):
        """
        Given a list of possible PK values, return a QuerySet of the
        corresponding objects. Raise a ValidationError if a given value is
        invalid (not a valid PK, not in the queryset, etc.)
        """
        key = self.to_field_name or "pk"
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            )
        for pk in value:
            self.validate_no_null_characters(pk)
            try:
                self.queryset.filter(**{key: pk})
            except (ValueError, TypeError):
                raise ValidationError(
                    self.error_messages["invalid_pk_value"],
                    code="invalid_pk_value",
                    params={"pk": pk},
                )
        qs = self.queryset.filter(**{"%s__in" % key: value})
        pks = {str(getattr(o, key)) for o in qs}
        for val in value:
            if str(val) not in pks:
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": val},
                )
        return qs

    def prepare_value(self, value):
        if (
            hasattr(value, "__iter__")
            and not isinstance(value, str)
            and not hasattr(value, "_meta")
        ):
            prepare_value = super().prepare_value
            return [prepare_value(v) for v in value]
        return super().prepare_value(value)

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_set = {str(value) for value in self.prepare_value(initial)}
        data_set = {str(value) for value in data}
        return data_set != initial_set


def modelform_defines_fields(form_class):
    return hasattr(form_class, "_meta") and (
        form_class._meta.fields is not None or form_class._meta.exclude is not None
    )
