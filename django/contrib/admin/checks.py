# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin.util import get_fields_from_path, NotRelationField
from django.core import checks
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import BaseModelForm, _get_foreign_key, BaseModelFormSet


# This check is registered in __init__.py file.
def check_model_admin(**kwargs):
    return []


def flatten(outer_list):
    return [item for inner_list in outer_list for item in inner_list]


# Mixin for BaseModelAdmin
class BaseModelAdminChecks(object):

    # A helper method.
    @classmethod
    def _error(cls, msg):

        return [
            checks.Error(
                msg,
                hint=None,
                obj=cls,
            )
        ]

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

        if not isinstance(cls.raw_id_fields, (list, tuple)):
            return cls._error('"raw_id_fields" must be a list or tuple.')
        else:
            return flatten(
                cls._check_raw_id_fields_item(model, field_name, 'raw_id_fields[%d]' % index)
                for index, field_name in enumerate(cls.raw_id_fields))

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
            return cls._error(
                '"%s" refers to field "%s", which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model.__name__))
        except ValueError:
            return cls._error('"%s" must be a ForeignKey or a ManyToManyField.' % label)
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
            return cls._error('"fields" must be a list or tuple.')
        elif cls.fieldsets:
            return cls._error('Both "fieldsets" and "fields" are specified.')
        elif len(cls.fields) != len(set(cls.fields)):
            return cls._error('There are duplicate field(s) in "fields".')
        else:
            return flatten(
                cls._check_field_spec(model, field_name, 'fields')
                for field_name in cls.fields)

    @classmethod
    def _check_fieldsets(cls, model):
        """ Check that fieldsets is properly formatted and doesn't contain
        duplicates. """

        if cls.fieldsets is None:
            return []
        elif not isinstance(cls.fieldsets, (list, tuple)):
            return cls._error('"fieldsets" must be a list or tuple.')
        else:
            return flatten(
                cls._check_fieldsets_item(model, fieldset, 'fieldsets[%d]' % index)
                for index, fieldset in enumerate(cls.fieldsets))

    @classmethod
    def _check_fieldsets_item(cls, model, fieldset, label):
        """ Check an item of `fieldsets`, i.e. check that this is a pair of a
        set name and a dictionary containing "fields" key. """

        if not isinstance(fieldset, (list, tuple)):
            return cls._error('"%s must be a list or tuple' % label)
        elif len(fieldset) != 2:
            return cls._error('"%s" must be a sequence of pairs.' % label)
        elif not isinstance(fieldset[1], dict):
            return cls._error('"%s[1]" must be a dictionary.' % label)
        elif 'fields' not in fieldset[1]:
            return cls._error('"%s[1]" must contain "fields" key.' % label)
        else:
            return flatten(
                cls._check_field_spec(model, fields, '%s[1][\'fields\']' % label)
                for fields in fieldset[1]['fields'])

    @classmethod
    def _check_field_spec(cls, model, fields, label):
        """ `fields` should be an item of `fields` or an item of
        fieldset[1]['fields'] for any `fieldset` in `fieldsets`. It should be a
        field name or a tuple of field names. """

        if isinstance(fields, tuple):
            return flatten(
                cls._check_field_spec_item(model, field_name, "%s[%d]" % (label, index))
                for index, field_name in enumerate(fields))
        else:
            return cls._check_field_spec_item(model, fields, label)

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
                return cls._error('"%s" cannot include the ManyToManyField "%s", '
                    'because "%s" manually specifies relationship model.'
                    % (label, field_name, field_name))
            else:
                return []

    @classmethod
    def _check_exclude(cls, model):
        """ Check that exclude is a sequence without duplicates. """

        if cls.exclude is None:  # default value is None
            return []
        elif not isinstance(cls.exclude, (list, tuple)):
            return cls._error('"exclude" must be a list or tuple.')
        elif len(cls.exclude) > len(set(cls.exclude)):
            return cls._error('"exclude" contains duplicate field(s).')
        else:
            return []

    @classmethod
    def _check_form(cls, model):
        """ Check that form subclasses BaseModelForm. """

        if hasattr(cls, 'form') and not issubclass(cls.form, BaseModelForm):
            return cls._error('"form" does not inherit from "BaseModelForm.%s"' % cls.__name__)
        else:
            return []

    @classmethod
    def _check_filter_vertical(cls, model):
        """ Check that filter_vertical is a sequence of field names. """

        if not hasattr(cls, 'filter_vertical'):
            return []
        elif not isinstance(cls.filter_vertical, (list, tuple)):
            return cls._error('"filter_vertical" must be a list or tuple.')
        else:
            return flatten(
                cls._check_filter_item(model, field_name, "filter_vertical[%d]" % index)
                for index, field_name in enumerate(cls.filter_vertical))

    @classmethod
    def _check_filter_horizontal(cls, model):
        """ Check that filter_horizontal is a sequence of field names. """

        if not hasattr(cls, 'filter_horizontal'):
            return []
        elif not isinstance(cls.filter_horizontal, (list, tuple)):
            return cls._error('"filter_horizontal" must be a list or tuple.')
        else:
            return flatten(
                cls._check_filter_item(model, field_name, "filter_horizontal[%d]" % index)
                for index, field_name in enumerate(cls.filter_horizontal))

    @classmethod
    def _check_filter_item(cls, model, field_name, label):
        """ Check one item of `filter_vertical` or `filter_horizontal`, i.e.
        check that given field exists and is a ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
            if not isinstance(field, models.ManyToManyField):
                raise ValueError
        except models.FieldDoesNotExist:
            return cls._error(
                '"%s" refers to field "%s", which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model._meta.object_name))
        except ValueError:
            return cls._error('"%s" must be a ManyToManyField.' % label)
        else:
            return []

    @classmethod
    def _check_radio_fields(cls, model):
        """ Check that `radio_fields` is a dictionary. """

        if not hasattr(cls, 'radio_fields'):
            return []
        elif not isinstance(cls.radio_fields, dict):
            return cls._error('"radio_fields" must be a dictionary.')
        else:
            return flatten(
                cls._check_radio_fields_key(model, field_name, 'radio_fields[%r]' % field_name) +
                cls._check_radio_fields_value(model, val, 'radio_fields[%r]' % field_name)
                for field_name, val in cls.radio_fields.items())

    @classmethod
    def _check_radio_fields_key(cls, model, field_name, label):
        """ Check that a key of `radio_fields` dictionary is name of existing
        field and that the field is a ForeignKey or has `choices` defined. """

        try:
            field = model._meta.get_field(field_name)
            if not (isinstance(field, models.ForeignKey) or field.choices):
                raise ValueError
        except models.FieldDoesNotExist:
            return cls._error(
                '"%s" refers to "%s" field, which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model._meta.object_name))
        except ValueError:
            return cls._error('"%s" is neither an instance of ForeignKey '
                'nor does have choices set.' % label)
        else:
            return []

    @classmethod
    def _check_radio_fields_value(cls, model, val, label):
        """ Check type of a value of `radio_fields` dictionary. """

        from django.contrib.admin.options import HORIZONTAL, VERTICAL

        if val not in (HORIZONTAL, VERTICAL):
            return cls._error('"%s" is neither admin.HORIZONTAL nor admin.VERTICAL.' % label)
        else:
            return []

    @classmethod
    def _check_prepopulated_fields(cls, model):
        """ Check that `prepopulated_fields` is a dictionary containing allowed
        field types. """

        if not hasattr(cls, 'prepopulated_fields'):
            return []
        elif not isinstance(cls.prepopulated_fields, dict):
            return cls._error('"prepopulated_fields" must be a dictionary.')
        else:
            return flatten(
                cls._check_prepopulated_fields_key(model, field_name, 'prepopulated_fields[%r]' % field_name) +
                cls._check_prepopulated_fields_value(model, val, 'prepopulated_fields[%r]' % field_name)
                for field_name, val in cls.prepopulated_fields.items())

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
            return cls._error(
                '"%s" refers to "%s" field, which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model._meta.object_name))
        except ValueError:
            return cls._error('"%s" is either a DateTimeField, ForeignKey '
                'or ManyToManyField. This is not allowed.' % label)
        else:
            return []

    @classmethod
    def _check_prepopulated_fields_value(cls, model, val, label):
        """ Check a value of `prepopulated_fields` dictionary, i.e. it's an
        iterable of existing fields. """

        if not isinstance(val, (list, tuple)):
            return cls._error('"%s" must be a list or tuple.' % label)
        else:
            return flatten(
                cls._check_prepopulated_fields_value_item(model, subfield_name, "%s[%r]" % (label, index))
                for index, subfield_name in enumerate(val))

    @classmethod
    def _check_prepopulated_fields_value_item(cls, model, field_name, label):
        """ For `prepopulated_fields` equal to {"slug": ("title",)},
        `field_name` is "title". """

        try:
            model._meta.get_field(field_name)
        except models.FieldDoesNotExist:
            return cls._error(
                '"%s" refers to field "%s", which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model._meta.object_name))
        else:
            return []

    @classmethod
    def _check_ordering(cls, model):
        """ Check that ordering refers to existing fields or is random. """

        # ordering = None
        if cls.ordering is None:  # The default value is None
            return []
        elif not isinstance(cls.ordering, (list, tuple)):
            return cls._error('"ordering" must be a list or tuple.')
        else:
            return flatten(
                cls._check_ordering_item(model, field_name, 'ordering[%d]' % index)
                for index, field_name in enumerate(cls.ordering))

    @classmethod
    def _check_ordering_item(cls, model, field_name, label):
        """ Check that `ordering` refers to existing fields. """

        if field_name == '?' and len(cls.ordering) != 1:
            return cls._error('"ordering" has the random ordering marker "?", '
                'but contains other fields as well.')
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
                return cls._error(
                    '"%s" refers to field "%s", which is missing from model %s.%s.'
                    % (label, field_name, model._meta.app_label, model._meta.object_name))
            else:
                return []

    @classmethod
    def _check_readonly_fields(cls, model):
        """ Check that readonly_fields refers to proper attribute or field. """

        if cls.readonly_fields == ():
            return []
        elif not isinstance(cls.readonly_fields, (list, tuple)):
            return cls._error('"readonly_fields" must be a list or tuple.')
        else:
            return flatten(
                cls._check_readonly_fields_item(model, field_name, "readonly_fields[%d]" % index)
                for index, field_name in enumerate(cls.readonly_fields))

    @classmethod
    def _check_readonly_fields_item(cls, model, field_name, label):
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
                return cls._error(
                    '"%s" is neither a callable nor an attribute of "%s" nor found in the model %s.%s.'
                    % (label, cls.__name__, model._meta.app_label, model._meta.object_name))
            else:
                return []


# Mixin for ModelBase.
class ModelAdminChecks(BaseModelAdminChecks):

    @classmethod
    def check(cls, model, **kwargs):
        errors = super(ModelAdminChecks, cls).check(model=model, **kwargs)
        errors.extend(cls._check_save_as(model=model))
        errors.extend(cls._check_save_on_top(model=model))
        errors.extend(cls._check_inlines(model=model))
        errors.extend(cls._check_list_display(model=model))
        errors.extend(cls._check_list_display_links(model=model))
        errors.extend(cls._check_list_filter(model=model))
        errors.extend(cls._check_list_select_related(model=model))
        errors.extend(cls._check_list_per_page(model=model))
        errors.extend(cls._check_list_max_show_all(model=model))
        errors.extend(cls._check_list_editable(model=model))
        errors.extend(cls._check_search_fields(model=model))
        errors.extend(cls._check_date_hierarchy(model=model))
        return errors

    @classmethod
    def _check_save_as(cls, model):
        """ Check save_as is a boolean. """

        if not isinstance(cls.save_as, bool):
            return cls._error('"save_as" must be a boolean.')
        else:
            return []

    @classmethod
    def _check_save_on_top(cls, model):
        """ Check save_on_top is a boolean. """

        if not isinstance(cls.save_on_top, bool):
            return cls._error('"save_on_top" must be a boolean.')
        else:
            return []

    @classmethod
    def _check_inlines(cls, model):
        """ Check inline model admin classes. """

        if not isinstance(cls.inlines, (list, tuple)):
            return cls._error('"inlines" must be a list or tuple.')
        else:
            return flatten(
                cls._check_inlines_item(model, item, "inlines[%d]" % index)
                for index, item in enumerate(cls.inlines))

    @classmethod
    def _check_inlines_item(cls, model, inline, label):
        from django.contrib.admin.options import BaseModelAdmin

        if not issubclass(inline, BaseModelAdmin):
            return cls._error('"%s" must inherit from BaseModelAdmin.' % label)
        elif not inline.model:
            return cls._error('"model" is a required attribute of "%s".' % label)
        elif not issubclass(inline.model, models.Model):
            return cls._error('"%s.model" must be a Model."' % label)
        else:
            return inline.check(model)

    @classmethod
    def _check_list_display(cls, model):
        """ Check that list_display only contains fields or usable attributes.
        """

        if not isinstance(cls.list_display, (list, tuple)):
            return cls._error('"list_display" must be a list or tuple.')
        else:
            return flatten(
                cls._check_list_display_item(model, item, "list_diplay[%d]" % index)
                for index, item in enumerate(cls.list_display))

    @classmethod
    def _check_list_display_item(cls, model, item, label):
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
                return cls._error(
                    '"%s" refers to "%s" that is neither a field, method nor a property of model %s.%s.'
                    % label, item, model._meta.app_label, model._meta.object_name)
            elif isinstance(item, models.ManyToManyField):
                return cls._error('"%s" must not be a ManyToManyField.' % label)
            else:
                return []
        else:
            try:
                model._meta.get_field(item)
            except models.FieldDoesNotExist:
                return cls._error(
                    '"%s" is neither a callable nor an attribute of %r nor found in model %s.%s.'
                    % (label, cls.__name__, model._meta.app_label, model._meta.object_name))
            else:
                return []

    @classmethod
    def _check_list_display_links(cls, model):
        """ Check that list_display_links is a unique subset of list_display.
        """

        if not isinstance(cls.list_display_links, (list, tuple)):
            import ipdb; ipdb.set_trace()
            return cls._error('"list_display_links" must be a list or tuple')

        else:
            return flatten(
                cls._check_list_display_links_item(model, field_name, "list_display_links[%d]" % index)
                for index, field_name in enumerate(cls.list_display_links))

    @classmethod
    def _check_list_display_links_item(cls, model, field_name, label):
        if field_name not in cls.list_display:
            return cls._error(
                '"%s" refers to "%s", which is not defined in "list_display".'
                % (label, field_name))
        else:
            return []

    @classmethod
    def _check_list_filter(cls, model):
        """
        Check that list_filter is a sequence of one of three options:
            1: 'field' - a basic field filter, possibly w/ relationships (eg, 'field__rel')
            2: ('field', SomeFieldListFilter) - a field-based list filter class
            3: SomeListFilter - a non-field list filter class
        """

        if not isinstance(cls.list_filter, (list, tuple)):
            return cls._error('"list_filter" must be a list or tuple.')
        else:
            return flatten(
                cls._check_list_filter_item(model, item, "list_filter[%d]" % index)
                for index, item in enumerate(cls.list_filter))

    @classmethod
    def _check_list_filter_item(cls, model, item, label):
        from django.contrib.admin import ListFilter, FieldListFilter

        if callable(item) and not isinstance(item, models.Field):
            # If item is option 3, it should be a ListFilter...
            if not issubclass(item, ListFilter):
                return cls._error('"%s" must inherit from ListFilter.' % label)
            # ...  but not a FieldListFilter.
            elif issubclass(item, FieldListFilter):
                return cls._error('"%s" must not inherit from FieldListFilter.' % label)
            else:
                return []
        else:
            if isinstance(item, (tuple, list)):
                # item is option #2
                field, list_filter_class = item
                if not issubclass(list_filter_class, FieldListFilter):
                    return cls._error('"%s" must inherit from FieldListFilter.' % label)
                else:
                    return []
            else:
                # item is option #1
                field = item

                # Validate the field string
                try:
                    get_fields_from_path(model, field)
                except (NotRelationField, FieldDoesNotExist):
                    return cls._error('"%s" refers to "%s", which does not refer to a Field.' % (label, field))

    @classmethod
    def _check_list_select_related(cls, model):
        """ Check that list_select_related is a boolean, a list or a tuple. """

        if not isinstance(cls.list_select_related, (bool, list, tuple)):
            return cls._error('"list_select_related" must be a bool, tuple or list.')
        else:
            return []

    @classmethod
    def _check_list_per_page(cls, model):
        """ Check that list_per_page is an integer. """

        if not isinstance(cls.list_per_page, int):
            return cls._error('"list_per_page" must be an integer.')
        else:
            return []

    @classmethod
    def _check_list_max_show_all(cls, model):
        """ Check that list_max_show_all is an integer. """

        if not isinstance(cls.list_max_show_all, int):
            return cls._error('"list_max_show_all" must be an integer.')
        else:
            return []

    @classmethod
    def _check_list_editable(cls, model):
        """ Check that list_editable is a sequence of editable fields from
        list_display without first element. """

        if not isinstance(cls.list_editable, (list, tuple)):
            return cls._error('"list_editable" must be a list or tuple.')
        else:
            return flatten(
                cls._check_list_editable_item(model, item, "list_editable[%d]" % index)
                for index, item in enumerate(cls.list_editable))

    @classmethod
    def _check_list_editable_item(cls, model, field_name, label):
        try:
            field = model._meta.get_field_by_name(field_name)[0]
        except models.FieldDoesNotExist:
            return cls._error(
                '"%s" refers to field "%s", which is missing from model %s.%s.'
                % (label, field_name, model._meta.app_label, model._meta.object_name))
        else:
            if field_name not in cls.list_display:
                return cls._error('"%s" refers to field "%s", which is not defined in "list_display".' % (label, field_name))
            elif field_name in cls.list_display_links:
                return cls._error('"%s" cannot be in both "list_editable" and "list_display_links".' % field_name)
            elif not cls.list_display_links and cls.list_display[0] in cls.list_editable:
                return cls._error(
                    '"%s" refers to the first field in list_display ("%s"), which cannot be used unless list_display_links is set.'
                    % (label, cls.list_display[0]))
            elif not field.editable:
                return cls._error(
                    '"%s" refers to field "%s", whih is not editable through the admin.'
                    % (label, field_name))

    @classmethod
    def _check_search_fields(cls, model):
        """ Check search_fields is a sequence. """

        if not isinstance(cls.search_fields, (list, tuple)):
            return cls._error('"search_fields" must be a list or tuple.')
        else:
            return []

    @classmethod
    def _check_date_hierarchy(cls, model):
        """ Check that date_hierarchy refers to DateField or DateTimeField. """

        if cls.date_hierarchy is None:
            return []
        else:
            try:
                field = model._meta.get_field(cls.date_hierarchy)
                if not isinstance(field, (models.DateField, models.DateTimeField)):
                    raise ValueError
            except models.FieldDoesNotExist:
                return cls._error(
                    '"date_hierarchy" refers to field "%s", which is missing from model %s.%s.'
                    % (cls.date_hierarchy, model._meta.app_label, model._meta.object_name))
            except ValueError:
                return cls._error('"date_hierarchy" must be a DateField or DateTimeField.')
            else:
                return []


# Mixin for InlineModelAdmin
class InlineModelAdminChecks(BaseModelAdminChecks):

    @classmethod
    def check(cls, model, **kwargs):
        errors = super(InlineModelAdminChecks, cls).check(model=model, **kwargs)
        errors.extend(cls._check_inline(model))
        errors.extend(cls._check_fk_name())
        errors.extend(cls._check_extra())
        errors.extend(cls._check_max_num())
        errors.extend(cls._check_formset())
        return errors

    @classmethod
    def _check_inline(cls, parent_model):
        fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name, can_fail=True)
        if cls.exclude is None:
            return []
        elif fk and fk.name in cls.exclude:
            return cls._error(
                'Cannot exclude the field "%s", because it is the foreign key to the parent model %s.%s.'
                % (fk.name, parent_model._meta.app_label, parent_model._meta.object_name))
        else:
            return []

        """
        parent_model = cls.model
        fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name, can_fail=True)
        if hasattr(cls, 'exclude') and cls.exclude:
            if fk and fk.name in cls.exclude:
                raise ImproperlyConfigured("%s cannot exclude the field "
                        "'%s' - this is the foreign key to the parent model "
                        "%s.%s." % (cls.__name__, fk.name, parent_model._meta.app_label, parent_model.__name__))
        """

    @classmethod
    def _check_fk_name(cls):
        """ Check that fk_name refers to a ForeignKey. """

        if cls.fk_name is None:  # the default value is None
            return []
        else:
            try:
                field = cls.model._meta.get_field(cls.fk_name)
                if not isinstance(field, models.ForeignKey):
                    raise ValueError
            except models.FieldDoesNotExist:
                return cls._error(
                    '"fk_name" refers to field "%s", which is missing from model %s.%s.'
                    % (cls.fk_name, cls.model._meta.app_label, cls.model._meta.object_name))
            except ValueError:
                return cls._error('"fk_name" must be a ForeignKey.')
            else:
                return []

    @classmethod
    def _check_extra(cls):
        """ Check that extra is an integer. """

        if not isinstance(cls.extra, int):
            return cls._error('"extra" must be an integer.')
        else:
            return []

    @classmethod
    def _check_max_num(cls):
        """ Check that max_num is an integer. """

        if cls.max_num is None:
            return []
        elif not isinstance(cls.max_num, int):
            return cls._error('"max_num" must be an integer.')
        else:
            return []

    @classmethod
    def _check_formset(cls):
        """ Check formset is a subclass of BaseModelFormSet. """

        if not issubclass(cls.formset, BaseModelFormSet):
            return cls._error('"formset" must inherit from BaseModelFormSet.')
        else:
            return []
