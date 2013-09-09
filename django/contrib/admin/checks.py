# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.contrib.admin.util import get_fields_from_path, NotRelationField
from django.core import checks
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import BaseModelForm, _get_foreign_key, BaseModelFormSet


@checks.register()
def check_admin_app(**kwargs):
    from django.contrib.admin.sites import site

    return list(chain(*[
        model_admin.check(model, **kwargs)
        for model, model_admin in site._registry.items()
    ]))


class BaseModelAdminChecks(object):

    def __init__(self):
        # Before we can introspect models, they need to be fully loaded so that
        # inter-relations are set up correctly. We force that here.
        models.get_apps()

    def check(self, cls, model, **kwargs):
        errors = []
        errors.extend(self._check_raw_id_fields(cls, model))
        errors.extend(self._check_fields(cls, model))
        errors.extend(self._check_fieldsets(cls, model))
        errors.extend(self._check_exclude(cls, model))
        errors.extend(self._check_form(cls, model))
        errors.extend(self._check_filter_vertical(cls, model))
        errors.extend(self._check_filter_horizontal(cls, model))
        errors.extend(self._check_radio_fields(cls, model))
        errors.extend(self._check_prepopulated_fields(cls, model))
        errors.extend(self._check_ordering(cls, model))
        errors.extend(self._check_readonly_fields(cls, model))
        return errors

    def _check_raw_id_fields(self, cls, model):
        """ Check that `raw_id_fields` only contains field names that are listed
        on the model. """

        if not isinstance(cls.raw_id_fields, (list, tuple)):
            return [
                checks.Error(
                    '"raw_id_fields" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E001',
                ),
            ]
        else:
            return list(chain(*[
                self._check_raw_id_fields_item(cls, model, field_name, 'raw_id_fields[%d]' % index)
                for index, field_name in enumerate(cls.raw_id_fields)
            ]))

    def _check_raw_id_fields_item(self, cls, model, field_name, label):
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
                    '"%s" refers to field "%s", which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model.__name__),
                    hint=None,
                    obj=cls,
                    id='admin.E002',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    '"%s" must be a ForeignKey or ManyToManyField.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E003',
                )
            ]
        else:
            return []

    def _check_fields(self, cls, model):
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
                    id='admin.E004',
                )
            ]
        elif cls.fieldsets:
            return [
                checks.Error(
                    'Both "fieldsets" and "fields" are specified.',
                    hint=None,
                    obj=cls,
                    id='admin.E005',
                )
            ]
        elif len(cls.fields) != len(set(cls.fields)):
            return [
                checks.Error(
                    'There are duplicate field(s) in "fields".',
                    hint=None,
                    obj=cls,
                    id='admin.E006',
                )
            ]
        else:
            return list(chain(*[
                self._check_field_spec(cls, model, field_name, 'fields')
                for field_name in cls.fields
            ]))

    def _check_fieldsets(self, cls, model):
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
                    id='admin.E007',
                )
            ]
        else:
            return list(chain(*[
                self._check_fieldsets_item(cls, model, fieldset, 'fieldsets[%d]' % index)
                for index, fieldset in enumerate(cls.fieldsets)
            ]))

    def _check_fieldsets_item(self, cls, model, fieldset, label):
        """ Check an item of `fieldsets`, i.e. check that this is a pair of a
        set name and a dictionary containing "fields" key. """

        if not isinstance(fieldset, (list, tuple)):
            return [
                checks.Error(
                    '"%s" must be a list or tuple.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E008',
                )
            ]
        elif len(fieldset) != 2:
            return [
                checks.Error(
                    '"%s" must be a pair.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E009',
                )
            ]
        elif not isinstance(fieldset[1], dict):
            return [
                checks.Error(
                    '"%s[1]" must be a dictionary.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E010',
                )
            ]
        elif 'fields' not in fieldset[1]:
            return [
                checks.Error(
                    '"%s[1]" must contain "fields" key.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E011',
                )
            ]
        elif len(fieldset[1]['fields']) != len(set(fieldset[1]['fields'])):
            return [
                checks.Error(
                    'There are duplicate field(s) in "%s[1]".' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E012',
                )
            ]
        else:
            return list(chain(*[
                self._check_field_spec(cls, model, fields, '%s[1][\'fields\']' % label)
                for fields in fieldset[1]['fields']
            ]))

    def _check_field_spec(self, cls, model, fields, label):
        """ `fields` should be an item of `fields` or an item of
        fieldset[1]['fields'] for any `fieldset` in `fieldsets`. It should be a
        field name or a tuple of field names. """

        if isinstance(fields, tuple):
            return list(chain(*[
                self._check_field_spec_item(cls, model, field_name, "%s[%d]" % (label, index))
                for index, field_name in enumerate(fields)
            ]))
        else:
            return self._check_field_spec_item(cls, model, fields, label)

    def _check_field_spec_item(self, cls, model, field_name, label):
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
                        id='admin.E013',
                    )
                ]
            else:
                return []

    def _check_exclude(self, cls, model):
        """ Check that exclude is a sequence without duplicates. """

        if cls.exclude is None:  # default value is None
            return []
        elif not isinstance(cls.exclude, (list, tuple)):
            return [
                checks.Error(
                    '"exclude" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E014',
                )
            ]
        elif len(cls.exclude) > len(set(cls.exclude)):
            return [
                checks.Error(
                    '"exclude" contains duplicate field(s).',
                    hint=None,
                    obj=cls,
                    id='admin.E015',
                )
            ]
        else:
            return []

    def _check_form(self, cls, model):
        """ Check that form subclasses BaseModelForm. """

        if hasattr(cls, 'form') and not issubclass(cls.form, BaseModelForm):
            return [
                checks.Error(
                    '"form" must inherit from BaseModelForm.',
                    hint=None,
                    obj=cls,
                    id='admin.E016',
                )
            ]
        else:
            return []

    def _check_filter_vertical(self, cls, model):
        """ Check that filter_vertical is a sequence of field names. """

        if not hasattr(cls, 'filter_vertical'):
            return []
        elif not isinstance(cls.filter_vertical, (list, tuple)):
            return [
                checks.Error(
                    '"filter_vertical" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E017',
                )
            ]
        else:
            return list(chain(*[
                self._check_filter_item(cls, model, field_name, "filter_vertical[%d]" % index)
                for index, field_name in enumerate(cls.filter_vertical)
            ]))

    def _check_filter_horizontal(self, cls, model):
        """ Check that filter_horizontal is a sequence of field names. """

        if not hasattr(cls, 'filter_horizontal'):
            return []
        elif not isinstance(cls.filter_horizontal, (list, tuple)):
            return [
                checks.Error(
                    '"filter_horizontal" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E018',
                )
            ]
        else:
            return list(chain(*[
                self._check_filter_item(cls, model, field_name, "filter_horizontal[%d]" % index)
                for index, field_name in enumerate(cls.filter_horizontal)
            ]))

    def _check_filter_item(self, cls, model, field_name, label):
        """ Check one item of `filter_vertical` or `filter_horizontal`, i.e.
        check that given field exists and is a ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
            if not isinstance(field, models.ManyToManyField):
                raise ValueError
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s", which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E019',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    '"%s" must be a ManyToManyField.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E020',
                )
            ]
        else:
            return []

    def _check_radio_fields(self, cls, model):
        """ Check that `radio_fields` is a dictionary. """

        if not hasattr(cls, 'radio_fields'):
            return []
        elif not isinstance(cls.radio_fields, dict):
            return [
                checks.Error(
                    '"radio_fields" must be a dictionary.',
                    hint=None,
                    obj=cls,
                    id='admin.E021',
                )
            ]
        else:
            return list(chain(*[
                self._check_radio_fields_key(cls, model, field_name, 'radio_fields') +
                self._check_radio_fields_value(cls, model, val, 'radio_fields[\'%s\']' % field_name)
                for field_name, val in cls.radio_fields.items()
            ]))

    def _check_radio_fields_key(self, cls, model, field_name, label):
        """ Check that a key of `radio_fields` dictionary is name of existing
        field and that the field is a ForeignKey or has `choices` defined. """

        try:
            field = model._meta.get_field(field_name)
            if not (isinstance(field, models.ForeignKey) or field.choices):
                raise ValueError
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to "%s" field, which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E022',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    '"%s" refers to "%s", which is neither an instance of ForeignKey nor does have choices set.'
                        % (label, field_name),
                    hint=None,
                    obj=cls,
                    id='admin.E023',
                )
            ]
        else:
            return []

    def _check_radio_fields_value(self, cls, model, val, label):
        """ Check type of a value of `radio_fields` dictionary. """

        from django.contrib.admin.options import HORIZONTAL, VERTICAL

        if val not in (HORIZONTAL, VERTICAL):
            return [
                checks.Error(
                    '"%s" is neither admin.HORIZONTAL nor admin.VERTICAL.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E024',
                )
            ]
        else:
            return []

    def _check_prepopulated_fields(self, cls, model):
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
                    id='admin.E025',
                )
            ]
        else:
            return list(chain(*[
                self._check_prepopulated_fields_key(cls, model, field_name, 'prepopulated_fields') +
                self._check_prepopulated_fields_value(cls, model, val, 'prepopulated_fields[\'%s\']' % field_name)
                for field_name, val in cls.prepopulated_fields.items()
            ]))

    def _check_prepopulated_fields_key(self, cls, model, field_name, label):
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
                    '"%s" refers to "%s" field, which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E026',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    '"%s" refers to "%s", which must be neither a DateTimeField, '
                        'ForeignKey nor ManyToManyField.'
                        % (label, field_name),
                    hint=None,
                    obj=cls,
                    id='admin.E027',
                )
            ]
        else:
            return []

    def _check_prepopulated_fields_value(self, cls, model, val, label):
        """ Check a value of `prepopulated_fields` dictionary, i.e. it's an
        iterable of existing fields. """

        if not isinstance(val, (list, tuple)):
            return [
                checks.Error(
                    '"%s" must be a list or tuple.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E028',
                )
            ]
        else:
            return list(chain(*[
                self._check_prepopulated_fields_value_item(cls, model, subfield_name, "%s[%r]" % (label, index))
                for index, subfield_name in enumerate(val)
            ]))

    def _check_prepopulated_fields_value_item(self, cls, model, field_name, label):
        """ For `prepopulated_fields` equal to {"slug": ("title",)},
        `field_name` is "title". """

        try:
            model._meta.get_field(field_name)
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s", which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E029',
                )
            ]
        else:
            return []

    def _check_ordering(self, cls, model):
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
                    id='admin.E030',
                )
            ]
        else:
            return list(chain(*[
                self._check_ordering_item(cls, model, field_name, 'ordering[%d]' % index)
                for index, field_name in enumerate(cls.ordering)
            ]))

    def _check_ordering_item(self, cls, model, field_name, label):
        """ Check that `ordering` refers to existing fields. """

        if field_name == '?' and len(cls.ordering) != 1:
            return [
                checks.Error(
                    '"ordering" has the random ordering marker "?", '
                        'but contains other fields as well.',
                    hint=None,
                    obj=cls,
                    id='admin.E031',
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
                        '"%s" refers to field "%s", which is missing from model %s.%s.'
                            % (label, field_name, model._meta.app_label, model._meta.object_name),
                        hint=None,
                        obj=cls,
                        id='admin.E032',
                    )
                ]
            else:
                return []

    def _check_readonly_fields(self, cls, model):
        """ Check that readonly_fields refers to proper attribute or field. """

        if cls.readonly_fields == ():
            return []
        elif not isinstance(cls.readonly_fields, (list, tuple)):
            return [
                checks.Error(
                    '"readonly_fields" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E033',
                )
            ]
        else:
            return list(chain(*[
                self._check_readonly_fields_item(cls, model, field_name, "readonly_fields[%d]" % index)
                for index, field_name in enumerate(cls.readonly_fields)
            ]))

    def _check_readonly_fields_item(self, cls, model, field_name, label):
        if callable(field_name):
            return []
        elif hasattr(cls, field_name):
            return []
        elif hasattr(model, field_name):
            return []
        else:
            try:
                model._meta.get_field(field_name)
            except models.FieldDoesNotExist:
                return [
                    checks.Error(
                        '"%s" is neither a callable nor an attribute of "%s" nor found in the model %s.%s.'
                            % (label, cls.__name__, model._meta.app_label, model._meta.object_name),
                        hint=None,
                        obj=cls,
                        id='admin.E034',
                    )
                ]
            else:
                return []


class ModelAdminChecks(BaseModelAdminChecks):

    def check(self, cls, model, **kwargs):
        errors = super(ModelAdminChecks, self).check(cls, model=model, **kwargs)
        errors.extend(self._check_save_as(cls, model))
        errors.extend(self._check_save_on_top(cls, model))
        errors.extend(self._check_inlines(cls, model))
        errors.extend(self._check_list_display(cls, model))
        errors.extend(self._check_list_display_links(cls, model))
        errors.extend(self._check_list_filter(cls, model))
        errors.extend(self._check_list_select_related(cls, model))
        errors.extend(self._check_list_per_page(cls, model))
        errors.extend(self._check_list_max_show_all(cls, model))
        errors.extend(self._check_list_editable(cls, model))
        errors.extend(self._check_search_fields(cls, model))
        errors.extend(self._check_date_hierarchy(cls, model))
        return errors

    def _check_save_as(self, cls, model):
        """ Check save_as is a boolean. """

        if not isinstance(cls.save_as, bool):
            return [
                checks.Error(
                    '"save_as" must be a boolean.',
                    hint=None,
                    obj=cls,
                    id='admin.E035',
                )
            ]
        else:
            return []

    def _check_save_on_top(self, cls, model):
        """ Check save_on_top is a boolean. """

        if not isinstance(cls.save_on_top, bool):
            return [
                checks.Error(
                    '"save_on_top" must be a boolean.',
                    hint=None,
                    obj=cls,
                    id='admin.E036',
                )
            ]
        else:
            return []

    def _check_inlines(self, cls, model):
        """ Check all inline model admin classes. """

        if not isinstance(cls.inlines, (list, tuple)):
            return [
                checks.Error(
                    '"inlines" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E037',
                )
            ]
        else:
            return list(chain(*[
                self._check_inlines_item(cls, model, item, "inlines[%d]" % index)
                for index, item in enumerate(cls.inlines)
            ]))

    def _check_inlines_item(self, cls, model, inline, label):
        """ Check one inline model admin. """

        from django.contrib.admin.options import BaseModelAdmin

        if not issubclass(inline, BaseModelAdmin):
            return [
                checks.Error(
                    '"%s" must inherit from BaseModelAdmin.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E038',
                )
            ]
        elif not inline.model:
            return [
                checks.Error(
                    '"model" is a required attribute of "%s".' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E039',
                )
            ]
        elif not issubclass(inline.model, models.Model):
            return [
                checks.Error(
                    '"%s.model" must be a Model.' % label,
                    hint=None,
                    obj=cls,
                    id='admin.E040',
                )
            ]
        else:
            return inline.check(model)

    def _check_list_display(self, cls, model):
        """ Check that list_display only contains fields or usable attributes.
        """

        if not isinstance(cls.list_display, (list, tuple)):
            return [
                checks.Error(
                    '"list_display" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E041',
                )
            ]
        else:
            return list(chain(*[
                self._check_list_display_item(cls, model, item, "list_display[%d]" % index)
                for index, item in enumerate(cls.list_display)
            ]))

    def _check_list_display_item(self, cls, model, item, label):
        if callable(item):
            return []
        elif hasattr(cls, item):
            return []
        elif hasattr(model, item):
            # getattr(model, item) could be an X_RelatedObjectsDescriptor
            try:
                field = model._meta.get_field(item)
            except models.FieldDoesNotExist:
                try:
                    field = getattr(model, item)
                except AttributeError:
                    field = None

            if field is None:
                return [
                    checks.Error(
                        '"%s" refers to "%s" that is neither a field, method nor a property of model %s.%s.'
                            % label, item, model._meta.app_label, model._meta.object_name,
                        hint=None,
                        obj=cls,
                        id='admin.E042',
                    )
                ]
            elif isinstance(field, models.ManyToManyField):
                return [
                    checks.Error(
                        '"%s" must not be a ManyToManyField.' % label,
                        hint=None,
                        obj=cls,
                        id='admin.E043',
                    )
                ]
            else:
                return []
        else:
            try:
                model._meta.get_field(item)
            except models.FieldDoesNotExist:
                return [
                    checks.Error(
                        '"%s" is neither a callable nor an attribute of "%s" nor found in model %s.%s.'
                            % (label, cls.__name__, model._meta.app_label, model._meta.object_name),
                        hint=None,
                        obj=cls,
                        id='admin.E044',
                    )
                ]
            else:
                return []

    def _check_list_display_links(self, cls, model):
        """ Check that list_display_links is a unique subset of list_display.
        """

        if not isinstance(cls.list_display_links, (list, tuple)):
            return [
                checks.Error(
                    '"list_display_links" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E045',
                )
            ]
        else:
            return list(chain(*[
                self._check_list_display_links_item(cls, model, field_name, "list_display_links[%d]" % index)
                for index, field_name in enumerate(cls.list_display_links)
            ]))

    def _check_list_display_links_item(self, cls, model, field_name, label):
        if field_name not in cls.list_display:
            return [
                checks.Error(
                    '"%s" refers to "%s", which is not defined in "list_display".'
                        % (label, field_name),
                    hint=None,
                    obj=cls,
                    id='admin.E046',
                )
            ]
        else:
            return []

    def _check_list_filter(self, cls, model):
        if not isinstance(cls.list_filter, (list, tuple)):
            return [
                checks.Error(
                    '"list_filter" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E047',
                )
            ]
        else:
            return list(chain(*[
                self._check_list_filter_item(cls, model, item, "list_filter[%d]" % index)
                for index, item in enumerate(cls.list_filter)
            ]))

    def _check_list_filter_item(self, cls, model, item, label):
        """
        Check one item of `list_filter`, i.e. check if it is one of three options:
        1. 'field' -- a basic field filter, possibly w/ relationships (e.g.
           'field__rel')
        2. ('field', SomeFieldListFilter) - a field-based list filter class
        3. SomeListFilter - a non-field list filter class
        """

        from django.contrib.admin import ListFilter, FieldListFilter

        if callable(item) and not isinstance(item, models.Field):
            # If item is option 3, it should be a ListFilter...
            if not issubclass(item, ListFilter):
                return [
                    checks.Error(
                        '"%s" must inherit from ListFilter.' % label,
                        hint=None,
                        obj=cls,
                        id='admin.E048',
                    )
                ]
            # ...  but not a FieldListFilter.
            elif issubclass(item, FieldListFilter):
                return [
                    checks.Error(
                        '"%s" must not inherit from FieldListFilter.' % label,
                        hint=None,
                        obj=cls,
                        id='admin.E049',
                    )
                ]
            else:
                return []
        elif isinstance(item, (tuple, list)):
            # item is option #2
            field, list_filter_class = item
            if not issubclass(list_filter_class, FieldListFilter):
                return [
                    checks.Error(
                        '"%s[1]" must inherit from FieldListFilter.' % label,
                        hint=None,
                        obj=cls,
                        id='admin.E050',
                    )
                ]
            else:
                return []
        else:
            # item is option #1
            field = item

            # Validate the field string
            try:
                get_fields_from_path(model, field)
            except (NotRelationField, FieldDoesNotExist):
                return [
                    checks.Error(
                        '"%s" refers to "%s", which does not refer to a Field.' % (label, field),
                        hint=None,
                        obj=cls,
                        id='admin.E051',
                    )
                ]
            else:
                return []

    def _check_list_select_related(self, cls, model):
        """ Check that list_select_related is a boolean, a list or a tuple. """

        if not isinstance(cls.list_select_related, (bool, list, tuple)):
            return [
                checks.Error(
                    '"list_select_related" must be a boolean, tuple or list.',
                    hint=None,
                    obj=cls,
                    id='admin.E052',
                )
            ]
        else:
            return []

    def _check_list_per_page(self, cls, model):
        """ Check that list_per_page is an integer. """

        if not isinstance(cls.list_per_page, int):
            return [
                checks.Error(
                    '"list_per_page" must be an integer.',
                    hint=None,
                    obj=cls,
                    id='admin.E053',
                )
            ]
        else:
            return []

    def _check_list_max_show_all(self, cls, model):
        """ Check that list_max_show_all is an integer. """

        if not isinstance(cls.list_max_show_all, int):
            return [
                checks.Error(
                    '"list_max_show_all" must be an integer.',
                    hint=None,
                    obj=cls,
                    id='admin.E054',
                )
            ]
        else:
            return []

    def _check_list_editable(self, cls, model):
        """ Check that list_editable is a sequence of editable fields from
        list_display without first element. """

        if not isinstance(cls.list_editable, (list, tuple)):
            return [
                checks.Error(
                    '"list_editable" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E055',
                )
            ]
        else:
            return list(chain(*[
                self._check_list_editable_item(cls, model, item, "list_editable[%d]" % index)
                for index, item in enumerate(cls.list_editable)
            ]))

    def _check_list_editable_item(self, cls, model, field_name, label):
        try:
            field = model._meta.get_field_by_name(field_name)[0]
        except models.FieldDoesNotExist:
            return [
                checks.Error(
                    '"%s" refers to field "%s", which is missing from model %s.%s.'
                        % (label, field_name, model._meta.app_label, model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E056',
                )
            ]
        else:
            if field_name not in cls.list_display:
                return [
                    checks.Error(
                        '"%s" refers to field "%s", which is not defined in "list_display".'
                            % (label, field_name),
                        hint=None,
                        obj=cls,
                        id='admin.E057',
                    )
                ]
            elif field_name in cls.list_display_links:
                return [
                    checks.Error(
                        '"%s" cannot be in both "list_editable" and "list_display_links".'
                            % field_name,
                        hint=None,
                        obj=cls,
                        id='admin.E058',
                    )
                ]
            elif not cls.list_display_links and cls.list_display[0] in cls.list_editable:
                return [
                    checks.Error(
                        '"%s" refers to the first field in list_display ("%s"), '
                            'which cannot be used unless list_display_links is set.'
                            % (label, cls.list_display[0]),
                        hint=None,
                        obj=cls,
                        id='admin.E059',
                    )
                ]
            elif not field.editable:
                return [
                    checks.Error(
                        '"%s" refers to field "%s", whih is not editable through the admin.'
                            % (label, field_name),
                        hint=None,
                        obj=cls,
                        id='admin.E060',
                    )
                ]

    def _check_search_fields(self, cls, model):
        """ Check search_fields is a sequence. """

        if not isinstance(cls.search_fields, (list, tuple)):
            return [
                checks.Error(
                    '"search_fields" must be a list or tuple.',
                    hint=None,
                    obj=cls,
                    id='admin.E061',
                )
            ]
        else:
            return []

    def _check_date_hierarchy(self, cls, model):
        """ Check that date_hierarchy refers to DateField or DateTimeField. """

        if cls.date_hierarchy is None:
            return []
        else:
            try:
                field = model._meta.get_field(cls.date_hierarchy)
                if not isinstance(field, (models.DateField, models.DateTimeField)):
                    raise ValueError
            except models.FieldDoesNotExist:
                return [
                    checks.Error(
                        '"date_hierarchy" refers to field "%s", which is missing from model %s.%s.'
                            % (cls.date_hierarchy, model._meta.app_label, model._meta.object_name),
                        hint=None,
                        obj=cls,
                        id='admin.E062',
                    )
                ]
            except ValueError:
                return [
                    checks.Error(
                        '"date_hierarchy" must be a DateField or DateTimeField.',
                        hint=None,
                        obj=cls,
                        id='admin.E063',
                    )
                ]
            else:
                return []


class InlineModelAdminChecks(BaseModelAdminChecks):

    def check(self, cls, parent_model, **kwargs):
        errors = super(InlineModelAdminChecks, self).check(cls, model=cls.model, **kwargs)
        errors.extend(self._check_fk_name(cls, parent_model))
        errors.extend(self._check_exclude_of_parent_model(cls, parent_model))
        errors.extend(self._check_extra(cls))
        errors.extend(self._check_max_num(cls))
        errors.extend(self._check_formset(cls))
        return errors

    def _check_exclude_of_parent_model(self, cls, parent_model):
        # Do not perform more specific checks if the base checks result in an
        # error.
        errors = super(InlineModelAdminChecks, self)._check_exclude(cls, parent_model)
        if errors:
            return []

        # Skip if `fk_name` is invalid.
        if self._check_fk_name(cls, parent_model):
            return []

        if cls.exclude is None:
            return []

        fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name)
        if fk.name in cls.exclude:
            return [
                checks.Error(
                    'Cannot exclude the field "%s", because it is the foreign key '
                        'to the parent model %s.%s.'
                        % (fk.name, parent_model._meta.app_label, parent_model._meta.object_name),
                    hint=None,
                    obj=cls,
                    id='admin.E064',
                )
            ]
        else:
            return []

    def _check_fk_name(self, cls, parent_model):
        try:
            _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name)
        except ValueError as e:
            return [
                checks.Error(
                    e.args[0],
                    hint=None,
                    obj=cls,
                    id='admin.E065',
                )
            ]
        else:
            return []

    def _check_extra(self, cls):
        """ Check that extra is an integer. """

        if not isinstance(cls.extra, int):
            return [
                checks.Error(
                    '"extra" must be an integer.',
                    hint=None,
                    obj=cls,
                    id='admin.E066',
                )
            ]
        else:
            return []

    def _check_max_num(self, cls):
        """ Check that max_num is an integer. """

        if cls.max_num is None:
            return []
        elif not isinstance(cls.max_num, int):
            return [
                checks.Error(
                    '"max_num" must be an integer.',
                    hint=None,
                    obj=cls,
                    id='admin.E067',
                )
            ]
        else:
            return []

    def _check_formset(self, cls):
        """ Check formset is a subclass of BaseModelFormSet. """

        if not issubclass(cls.formset, BaseModelFormSet):
            return [
                checks.Error(
                    '"formset" must inherit from BaseModelFormSet.',
                    hint=None,
                    obj=cls,
                    id='admin.E068',
                )
            ]
        else:
            return []
