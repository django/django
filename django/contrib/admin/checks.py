# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import checks
from django.db import models
from django.forms.models import BaseModelForm


# This check is registered in __init__.py file.
def check_model_admin(**kwargs):
    return []


# Mixin for BaseModelAdmin
class BaseModelAdminChecks(object):

    @classmethod
    def check(cls, model, **kwargs):
        # Before we can introspect models, they need to be fully loaded so that
        # inter-relations are set up correctly. We force that here.
        models.get_apps()

        errors = []
        errors.extend(cls._check_raw_id_fields(model))
        errors.extend(cls._check_fields(model))
        errors.extend(cls._check_fieldsets(model))
        errors.extend(cls._check_exclude(model))
        errors.extend(cls._check_form(model))
        errors.extend(cls._check_filter_vertical(model))
        errors.extend(cls._check_filter_horizontal(model))
        errors.extend(cls._check_radio_fields(model))
        errors.extend(cls._check_prepopulated_fields(model))
        errors.extend(cls._check_ordering(model))
        errors.extend(cls._check_readonly_fields(model))
        return errors

    @classmethod
    def _check_raw_id_fields(cls, model):
        """ Check that `raw_id_fields` only contains field names that are listed
        on the model. """

        if not hasattr(cls, 'raw_id_fields'):
            return []

        elif not isinstance(cls.raw_id_fields, (list, tuple)):
            return [
                checks.Error(
                    '"raw_id_fields" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for index, field_name in enumerate(cls.raw_id_fields)
                for error in cls._check_raw_id_fields_item(model, field_name, 'raw_id_fields[%d]' % index)
            ]

    @classmethod
    def _check_raw_id_fields_item(cls, model, field_name, label):
        """ Check an item of `raw_id_fields`, i.e. check that field named
        `field_name` exists in model `model` and is a ForeignKey or a
        ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
            if not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                raise ValueError

        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s" that is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model.__name__),
                    hint=None,
                    obj=cls,
                )
            ]

        except ValueError:
            return [
                checks.Error(
                    '"%s" must be a ForeignKey or a ManyToManyField.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_fields(cls, model):
        """ Check that `fields` only refer to existing fields, doesn't contain
        duplicates. Check if at most one of `fields` and `fieldsets` is defined.
        """

        if cls.fields is None:
            return []

        elif not isinstance(cls.fields, (list, tuple)):
            return [
                checks.Error(
                    '"fields" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        elif cls.fieldsets:
            return [
                checks.Error(
                    'Both "fieldsets" and "fields" are specified.',
                    hint=None,
                    obj=cls,
                )
            ]

        elif len(cls.fields) != len(set(cls.fields)):
            return [
                checks.Error(
                    'There are duplicate field(s) in "fields".',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for field_name in cls.fields
                for error in cls._check_field_spec(model, field_name, 'fields')]

    @classmethod
    def _check_fieldsets(cls, model):
        """ Check that fieldsets is properly formatted and doesn't contain
        duplicates. """

        if cls.fieldsets is None:
            return []

        elif not isinstance(cls.fieldsets, (list, tuple)):
            return [
                checks.Error(
                    '"fieldsets" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                    for index, fieldset in enumerate(cls.fieldsets)
                    for error in cls._check_fieldsets_item(model, fieldset, 'fieldsets[%d]' % index)]

    @classmethod
    def _check_fieldsets_item(cls, model, fieldset, label):
        """ Check an item of `fieldsets`, i.e. check that this is a pair of a
        set name and a dictionary containing "fields" key. """

        if isinstance(fieldset, (list, tuple)):
            return [
                checks.Error(
                    '"%s" must be a list or tuple.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        elif len(fieldset) != 2:
            return [
                checks.Error(
                    '"%s" must be a sequence of pairs.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        elif not isinstance(fieldset[1], dict):
            return [
                checks.Error(
                    '"%s[1]" must be a dictionary.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        elif 'fields' not in fieldset[1]:
            return [
                checks.Error(
                    '"%s[1]" must contain "fields" key.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            label = '"%s[1][\'fields\']"' % label
            return [error
                for fields in fieldset[1]['fields']
                for error in cls._check_field_spec(model, fields, label)]

    @classmethod
    def _check_field_spec(cls, model, fields, label):
        """ `fields` should be an item of `fields` or an item of
        fieldset[1]['fields'] for any `fieldset` in `fieldsets`. It should be a
        field name or a tuple of field names. """

        if isinstance(fields, tuple):
            return [error
                for index, field_name in enumerate(fields)
                for error in cls._check_field_spec_item(model, field_name, "%s[%d]" % (label, index))]

        else:
            return [error for error in cls._check_field_spec_item(model, fields, label)]

    @classmethod
    def _check_field_spec_item(cls, model, field_name, label):
        if field_name in cls.readonly_fields:
            # Stuff can be put in fields that isn't actually a model field if
            # it's in readonly_fields, readonly_fields will handle the
            # validation of such things.
            return []

        else:
            try:
                field = model._meta.get_field(field_name)
                if (isinstance(field, models.ManyToManyField) and
                        not field.rel.through._meta.auto_created):
                    raise ValueError

            except models.FieldDoesNotExist:
                # If we can't find a field on the model that matches, it could
                # be an extra field on the form.
                return []

            except ValueError:
                return [
                    checks.Error(
                        '"%s" cannot include the ManyToManyField "%s", '
                            'because "%s" manually specifies relationship model.'
                            % (label, field_name, field_name),
                        hint=None,
                        obj=cls,
                    )
                ]

            else:
                return []

    @classmethod
    def _check_exclude(cls, model):
        """ Check that exclude is a sequence without duplicates. """

        if cls.exclude is None:  # default value is None
            return []

        elif not isinstance(cls.exclude, (list, tuple)):
            return [
                checks.Error(
                    '"exclude" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        elif len(cls.exclude) > len(set(cls.exclude)):
            return [
                checks.Error(
                    '"exclude" contains duplicate field(s).',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_form(cls, model):
        """ Check that form subclasses BaseModelForm. """

        if hasattr(cls, 'form') and not issubclass(cls.form, BaseModelForm):
            return [
                checks.Error(
                    '"form" does not inherit from "BaseModelForm.%s"'
                        % cls.__name__,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_filter_vertical(cls, model):
        """ Check that filter_vertical is a sequence of field names. """

        if not hasattr(cls, 'filter_vertical'):
            return []

        elif not isinstance(cls.filter_vertical, (list, tuple)):
            return [
                checks.Error(
                    '"filter_vertical" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for index, field_name in enumerate(cls.filter_vertical)
                for error in cls._check_filter_item(model, field_name, "filter_vertical[%d]" % index)]

    @classmethod
    def _check_filter_horizontal(cls, model):
        """ Check that filter_horizontal is a sequence of field names. """

        if not hasattr(cls, 'filter_horizontal'):
            return []

        elif not isinstance(cls.filter_horizontal, (list, tuple)):
            return [
                checks.Error(
                    '"filter_horizontal" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for index, field_name in enumerate(cls.filter_horizontal)
                for error in cls._check_filter_item(model, field_name, "filter_horizontal[%d]" % index)]

    @classmethod
    def _check_filter_item(cls, model, field_name, label):
        """ Check one item of `filter_vertical` or `filter_horizontal`, i.e.
        check that given field exists and is a ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
            if not isinstance(field, models.ManyToManyField):
                raise ValueError

        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s" that is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label,
                            model._meta.object_name)
                )
            ]

        except ValueError:
            return [
                checks.Error(
                    '"%s" must be a ManyToManyField.'
                        % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_radio_fields(cls, model):
        """ Check that `radio_fields` is a dictionary. """

        if not hasattr(cls, 'radio_fields'):
            return []

        elif not isinstance(cls.radio_fields, dict):
            return [
                checks.Error(
                    '"radio_fields" must be a dictionary.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for field_name, val in cls.radio_fields.items()
                for error in (cls._check_radio_fields_key(model, field_name, 'radio_fields[%r]' % field_name) +
                              cls._check_radio_fields_value(model, val, 'radio_fields[%r]' % field_name))]

    @classmethod
    def _check_radio_fields_key(cls, model, field_name, label):
        """ Check that a key of `radio_fields` dictionary is name of existing
        field and that the field is a ForeignKey or has `choices` defined. """

        try:
            field = model._meta.get_field(field_name)
            if not (isinstance(field, models.ForeignKey) or field.choices):
                raise ValueError

        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to "%s" field that '
                        'is missing from model %s.%s.'
                        % (label, field_name,
                            model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                )
            ]

        except ValueError:
            return [
                checks.Error(
                    '"%s" is neither an instance '
                        'of ForeignKey nor does have choices set.'
                        % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_radio_fields_value(cls, model, val, label):
        """ Check type of a value of `radio_fields` dictionary. """

        from django.contrib.admin.options import HORIZONTAL, VERTICAL

        if val not in (HORIZONTAL, VERTICAL):
            return [
                checks.Error(
                    '"%s" is neither admin.HORIZONTAL nor admin.VERTICAL.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_prepopulated_fields(cls, model):
        """ Check that `prepopulated_fields` is a dictionary containing allowed
        field types. """

        if not hasattr(cls, 'prepopulated_fields'):
            return []

        elif not isinstance(cls.prepopulated_fields, dict):
            return [
                checks.Error(
                    '"prepopulated_fields" must be a dictionary.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for field_name, val in cls.prepopulated_fields.items()
                for error in (cls._check_prepopulated_fields_key(model, field_name, 'prepopulated_fields[%r]' % field_name) +
                              cls._check_prepopulated_fields_value(model, val, 'prepopulated_fields[%r]' % field_name))]

    @classmethod
    def _check_prepopulated_fields_key(cls, model, field_name, label):
        """ Check a key of `prepopulated_fields` dictionary, i.e. check that it
        is a name of existing field and the field is one of the allowed types.
        """

        forbidden_field_types = (
            models.DateTimeField,
            models.ForeignKey,
            models.ManyToManyField
        )

        try:
            field = model._meta.get_field(field_name)
            if isinstance(field, forbidden_field_types):
                raise ValueError

        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to "%s" field that '
                        'is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                )
            ]

        except ValueError:
            return [
                checks.Error(
                    '"%s" is either a DateTimeField, ForeignKey or ManyToManyField. '
                        'This is not allowed.'
                        % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_prepopulated_fields_value(cls, model, val, label):
        """ Check a value of `prepopulated_fields` dictionary, i.e. it's an
        iterable of existing fields. """

        if not isinstance(val, (list, tuple)):
            return [
                checks.Error(
                    '"%s" must be a list or tuple.' % label,
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for index, subfield_name in enumerate(val)
                for error in cls._check_prepopulated_fields_value_item(
                        model, subfield_name, "%s[%r]" % (label, index))]

    @classmethod
    def _check_prepopulated_fields_value_item(cls, model, field_name, label):
        """ For `prepopulated_fields` equal to {"slug": ("title",)},
        `field_name` is "title". """

        try:
            model._meta.get_field(field_name)

        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s" that is missing from model %s.%s.'
                        % (label, field_name,
                            model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return []

    @classmethod
    def _check_ordering(cls, model):
        """ Check that ordering refers to existing fields or is random. """

        # ordering = None
        if cls.ordering is None:  # The default value is None
            return []

        elif not isinstance(cls.ordering, (list, tuple)):
            return [
                checks.Error(
                    '"ordering" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                )
            ]

        else:
            return [error
                for index, field_name in enumerate(cls.ordering)
                for error in cls._check_ordering_item(model, field_name, 'ordering[%d]' % index)]

    @classmethod
    def _check_ordering_item(cls, model, field_name, label):
        """ Check that `ordering` refers to existing fields. """

        if field_name == '?' and len(cls.ordering) != 1:
            return [
                checks.Error(
                    '"ordering" has the random ordering marker "?", but contains '
                        'other fields as well.',
                    hint='Remove "?" marker or the other fields.',
                    obj=cls,
                )
            ]

        elif field_name == '?':
            return []

        elif '__' in field_name:
            # Skip ordering in the format field1__field2 (FIXME: checking
            # this format would be nice, but it's a little fiddly).
            return []

        else:
            if field_name.startswith('-'):
                field_name = field_name[1:]

            try:
                model._meta.get_field(field_name)

            except models.FieldDoesNotExist:
                return [
                    checks.Error(
                        '"%s" refers to field "%s" that is missing from model %s.%s.'
                            % (label, field_name,
                                model._meta.app_label, model._meta.object_name),
                        hint=None,
                        obj=cls,
                    )
                ]

            else:
                return []

    @classmethod
    def _check_readonly_fields(cls, model):
        """ Check that readonly_fields refers to proper attribute or field. """

        return []

        if hasattr(cls, "readonly_fields"):
            #check_isseq(cls, "readonly_fields", cls.readonly_fields)
            for idx, field in enumerate(cls.readonly_fields):
                if not callable(field):
                    if not hasattr(cls, field):
                        if not hasattr(model, field):
                            try:
                                model._meta.get_field(field)
                            except models.FieldDoesNotExist:
                                pass
                                #raise ImproperlyConfigured("%s.readonly_fields[%d], %r is not a callable or an attribute of %r or found in the model %r."
                                #    % (cls.__name__, idx, field, cls.__name__, model._meta.object_name))

        return []

