# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.apps import apps
from django.conf import settings
from django.contrib.admin.utils import (
    NotRelationField, flatten, get_fields_from_path,
)
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.forms.models import (
    BaseModelForm, BaseModelFormSet, _get_foreign_key,
)
from django.template.engine import Engine


def check_admin_app(**kwargs):
    from django.contrib.admin.sites import system_check_errors

    return system_check_errors


def check_dependencies(**kwargs):
    """
    Check that the admin's dependencies are correctly installed.
    """
    errors = []
    # contrib.contenttypes must be installed.
    if not apps.is_installed('django.contrib.contenttypes'):
        missing_app = checks.Error(
            "'django.contrib.contenttypes' must be in INSTALLED_APPS in order "
            "to use the admin application.",
            id="admin.E401",
        )
        errors.append(missing_app)
    # The auth context processor must be installed if using the default
    # authentication backend.
    try:
        default_template_engine = Engine.get_default()
    except Exception:
        # Skip this non-critical check:
        # 1. if the user has a non-trivial TEMPLATES setting and Django
        #    can't find a default template engine
        # 2. if anything goes wrong while loading template engines, in
        #    order to avoid raising an exception from a confusing location
        # Catching ImproperlyConfigured suffices for 1. but 2. requires
        # catching all exceptions.
        pass
    else:
        if ('django.contrib.auth.context_processors.auth'
                not in default_template_engine.context_processors and
                'django.contrib.auth.backends.ModelBackend' in settings.AUTHENTICATION_BACKENDS):
            missing_template = checks.Error(
                "'django.contrib.auth.context_processors.auth' must be in "
                "TEMPLATES in order to use the admin application.",
                id="admin.E402"
            )
            errors.append(missing_template)
    return errors


class BaseModelAdminChecks(object):

    def check(self, admin_obj, **kwargs):
        errors = []
        errors.extend(self._check_raw_id_fields(admin_obj))
        errors.extend(self._check_fields(admin_obj))
        errors.extend(self._check_fieldsets(admin_obj))
        errors.extend(self._check_exclude(admin_obj))
        errors.extend(self._check_form(admin_obj))
        errors.extend(self._check_filter_vertical(admin_obj))
        errors.extend(self._check_filter_horizontal(admin_obj))
        errors.extend(self._check_radio_fields(admin_obj))
        errors.extend(self._check_prepopulated_fields(admin_obj))
        errors.extend(self._check_view_on_site_url(admin_obj))
        errors.extend(self._check_ordering(admin_obj))
        errors.extend(self._check_readonly_fields(admin_obj))
        return errors

    def _check_raw_id_fields(self, obj):
        """ Check that `raw_id_fields` only contains field names that are listed
        on the model. """

        if not isinstance(obj.raw_id_fields, (list, tuple)):
            return must_be('a list or tuple', option='raw_id_fields', obj=obj, id='admin.E001')
        else:
            return list(chain(*[
                self._check_raw_id_fields_item(obj, obj.model, field_name, 'raw_id_fields[%d]' % index)
                for index, field_name in enumerate(obj.raw_id_fields)
            ]))

    def _check_raw_id_fields_item(self, obj, model, field_name, label):
        """ Check an item of `raw_id_fields`, i.e. check that field named
        `field_name` exists in model `model` and is a ForeignKey or a
        ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label,
                                          model=model, obj=obj, id='admin.E002')
        else:
            if not field.many_to_many and not isinstance(field, models.ForeignKey):
                return must_be('a foreign key or a many-to-many field',
                               option=label, obj=obj, id='admin.E003')
            else:
                return []

    def _check_fields(self, obj):
        """ Check that `fields` only refer to existing fields, doesn't contain
        duplicates. Check if at most one of `fields` and `fieldsets` is defined.
        """

        if obj.fields is None:
            return []
        elif not isinstance(obj.fields, (list, tuple)):
            return must_be('a list or tuple', option='fields', obj=obj, id='admin.E004')
        elif obj.fieldsets:
            return [
                checks.Error(
                    "Both 'fieldsets' and 'fields' are specified.",
                    obj=obj.__class__,
                    id='admin.E005',
                )
            ]
        fields = flatten(obj.fields)
        if len(fields) != len(set(fields)):
            return [
                checks.Error(
                    "The value of 'fields' contains duplicate field(s).",
                    obj=obj.__class__,
                    id='admin.E006',
                )
            ]

        return list(chain(*[
            self._check_field_spec(obj, obj.model, field_name, 'fields')
            for field_name in obj.fields
        ]))

    def _check_fieldsets(self, obj):
        """ Check that fieldsets is properly formatted and doesn't contain
        duplicates. """

        if obj.fieldsets is None:
            return []
        elif not isinstance(obj.fieldsets, (list, tuple)):
            return must_be('a list or tuple', option='fieldsets', obj=obj, id='admin.E007')
        else:
            return list(chain(*[
                self._check_fieldsets_item(obj, obj.model, fieldset, 'fieldsets[%d]' % index)
                for index, fieldset in enumerate(obj.fieldsets)
            ]))

    def _check_fieldsets_item(self, obj, model, fieldset, label):
        """ Check an item of `fieldsets`, i.e. check that this is a pair of a
        set name and a dictionary containing "fields" key. """

        if not isinstance(fieldset, (list, tuple)):
            return must_be('a list or tuple', option=label, obj=obj, id='admin.E008')
        elif len(fieldset) != 2:
            return must_be('of length 2', option=label, obj=obj, id='admin.E009')
        elif not isinstance(fieldset[1], dict):
            return must_be('a dictionary', option='%s[1]' % label, obj=obj, id='admin.E010')
        elif 'fields' not in fieldset[1]:
            return [
                checks.Error(
                    "The value of '%s[1]' must contain the key 'fields'." % label,
                    obj=obj.__class__,
                    id='admin.E011',
                )
            ]
        elif not isinstance(fieldset[1]['fields'], (list, tuple)):
            return must_be('a list or tuple', option="%s[1]['fields']" % label, obj=obj, id='admin.E008')

        fields = flatten(fieldset[1]['fields'])
        if len(fields) != len(set(fields)):
            return [
                checks.Error(
                    "There are duplicate field(s) in '%s[1]'." % label,
                    obj=obj.__class__,
                    id='admin.E012',
                )
            ]
        return list(chain(*[
            self._check_field_spec(obj, model, fieldset_fields, '%s[1]["fields"]' % label)
            for fieldset_fields in fieldset[1]['fields']
        ]))

    def _check_field_spec(self, obj, model, fields, label):
        """ `fields` should be an item of `fields` or an item of
        fieldset[1]['fields'] for any `fieldset` in `fieldsets`. It should be a
        field name or a tuple of field names. """

        if isinstance(fields, tuple):
            return list(chain(*[
                self._check_field_spec_item(obj, model, field_name, "%s[%d]" % (label, index))
                for index, field_name in enumerate(fields)
            ]))
        else:
            return self._check_field_spec_item(obj, model, fields, label)

    def _check_field_spec_item(self, obj, model, field_name, label):
        if field_name in obj.readonly_fields:
            # Stuff can be put in fields that isn't actually a model field if
            # it's in readonly_fields, readonly_fields will handle the
            # validation of such things.
            return []
        else:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                # If we can't find a field on the model that matches, it could
                # be an extra field on the form.
                return []
            else:
                if (isinstance(field, models.ManyToManyField) and
                        not field.remote_field.through._meta.auto_created):
                    return [
                        checks.Error(
                            "The value of '%s' cannot include the ManyToManyField '%s', "
                            "because that field manually specifies a relationship model."
                            % (label, field_name),
                            obj=obj.__class__,
                            id='admin.E013',
                        )
                    ]
                else:
                    return []

    def _check_exclude(self, obj):
        """ Check that exclude is a sequence without duplicates. """

        if obj.exclude is None:  # default value is None
            return []
        elif not isinstance(obj.exclude, (list, tuple)):
            return must_be('a list or tuple', option='exclude', obj=obj, id='admin.E014')
        elif len(obj.exclude) > len(set(obj.exclude)):
            return [
                checks.Error(
                    "The value of 'exclude' contains duplicate field(s).",
                    obj=obj.__class__,
                    id='admin.E015',
                )
            ]
        else:
            return []

    def _check_form(self, obj):
        """ Check that form subclasses BaseModelForm. """

        if hasattr(obj, 'form') and not issubclass(obj.form, BaseModelForm):
            return must_inherit_from(parent='BaseModelForm', option='form',
                                     obj=obj, id='admin.E016')
        else:
            return []

    def _check_filter_vertical(self, obj):
        """ Check that filter_vertical is a sequence of field names. """

        if not hasattr(obj, 'filter_vertical'):
            return []
        elif not isinstance(obj.filter_vertical, (list, tuple)):
            return must_be('a list or tuple', option='filter_vertical', obj=obj, id='admin.E017')
        else:
            return list(chain(*[
                self._check_filter_item(obj, obj.model, field_name, "filter_vertical[%d]" % index)
                for index, field_name in enumerate(obj.filter_vertical)
            ]))

    def _check_filter_horizontal(self, obj):
        """ Check that filter_horizontal is a sequence of field names. """

        if not hasattr(obj, 'filter_horizontal'):
            return []
        elif not isinstance(obj.filter_horizontal, (list, tuple)):
            return must_be('a list or tuple', option='filter_horizontal', obj=obj, id='admin.E018')
        else:
            return list(chain(*[
                self._check_filter_item(obj, obj.model, field_name, "filter_horizontal[%d]" % index)
                for index, field_name in enumerate(obj.filter_horizontal)
            ]))

    def _check_filter_item(self, obj, model, field_name, label):
        """ Check one item of `filter_vertical` or `filter_horizontal`, i.e.
        check that given field exists and is a ManyToManyField. """

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label,
                                          model=model, obj=obj, id='admin.E019')
        else:
            if not field.many_to_many:
                return must_be('a many-to-many field', option=label, obj=obj, id='admin.E020')
            else:
                return []

    def _check_radio_fields(self, obj):
        """ Check that `radio_fields` is a dictionary. """

        if not hasattr(obj, 'radio_fields'):
            return []
        elif not isinstance(obj.radio_fields, dict):
            return must_be('a dictionary', option='radio_fields', obj=obj, id='admin.E021')
        else:
            return list(chain(*[
                self._check_radio_fields_key(obj, obj.model, field_name, 'radio_fields') +
                self._check_radio_fields_value(obj, val, 'radio_fields["%s"]' % field_name)
                for field_name, val in obj.radio_fields.items()
            ]))

    def _check_radio_fields_key(self, obj, model, field_name, label):
        """ Check that a key of `radio_fields` dictionary is name of existing
        field and that the field is a ForeignKey or has `choices` defined. """

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label,
                                          model=model, obj=obj, id='admin.E022')
        else:
            if not (isinstance(field, models.ForeignKey) or field.choices):
                return [
                    checks.Error(
                        "The value of '%s' refers to '%s', which is not an "
                        "instance of ForeignKey, and does not have a 'choices' definition." % (
                            label, field_name
                        ),
                        obj=obj.__class__,
                        id='admin.E023',
                    )
                ]
            else:
                return []

    def _check_radio_fields_value(self, obj, val, label):
        """ Check type of a value of `radio_fields` dictionary. """

        from django.contrib.admin.options import HORIZONTAL, VERTICAL

        if val not in (HORIZONTAL, VERTICAL):
            return [
                checks.Error(
                    "The value of '%s' must be either admin.HORIZONTAL or admin.VERTICAL." % label,
                    obj=obj.__class__,
                    id='admin.E024',
                )
            ]
        else:
            return []

    def _check_view_on_site_url(self, obj):
        if hasattr(obj, 'view_on_site'):
            if not callable(obj.view_on_site) and not isinstance(obj.view_on_site, bool):
                return [
                    checks.Error(
                        "The value of 'view_on_site' must be a callable or a boolean value.",
                        obj=obj.__class__,
                        id='admin.E025',
                    )
                ]
            else:
                return []
        else:
            return []

    def _check_prepopulated_fields(self, obj):
        """ Check that `prepopulated_fields` is a dictionary containing allowed
        field types. """

        if not hasattr(obj, 'prepopulated_fields'):
            return []
        elif not isinstance(obj.prepopulated_fields, dict):
            return must_be('a dictionary', option='prepopulated_fields', obj=obj, id='admin.E026')
        else:
            return list(chain(*[
                self._check_prepopulated_fields_key(obj, obj.model, field_name, 'prepopulated_fields') +
                self._check_prepopulated_fields_value(obj, obj.model, val, 'prepopulated_fields["%s"]' % field_name)
                for field_name, val in obj.prepopulated_fields.items()
            ]))

    def _check_prepopulated_fields_key(self, obj, model, field_name, label):
        """ Check a key of `prepopulated_fields` dictionary, i.e. check that it
        is a name of existing field and the field is one of the allowed types.
        """

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label,
                                          model=model, obj=obj, id='admin.E027')
        else:
            if isinstance(field, (models.DateTimeField, models.ForeignKey, models.ManyToManyField)):
                return [
                    checks.Error(
                        "The value of '%s' refers to '%s', which must not be a DateTimeField, "
                        "a ForeignKey, a OneToOneField, or a ManyToManyField." % (label, field_name),
                        obj=obj.__class__,
                        id='admin.E028',
                    )
                ]
            else:
                return []

    def _check_prepopulated_fields_value(self, obj, model, val, label):
        """ Check a value of `prepopulated_fields` dictionary, i.e. it's an
        iterable of existing fields. """

        if not isinstance(val, (list, tuple)):
            return must_be('a list or tuple', option=label, obj=obj, id='admin.E029')
        else:
            return list(chain(*[
                self._check_prepopulated_fields_value_item(obj, model, subfield_name, "%s[%r]" % (label, index))
                for index, subfield_name in enumerate(val)
            ]))

    def _check_prepopulated_fields_value_item(self, obj, model, field_name, label):
        """ For `prepopulated_fields` equal to {"slug": ("title",)},
        `field_name` is "title". """

        try:
            model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label, model=model, obj=obj, id='admin.E030')
        else:
            return []

    def _check_ordering(self, obj):
        """ Check that ordering refers to existing fields or is random. """

        # ordering = None
        if obj.ordering is None:  # The default value is None
            return []
        elif not isinstance(obj.ordering, (list, tuple)):
            return must_be('a list or tuple', option='ordering', obj=obj, id='admin.E031')
        else:
            return list(chain(*[
                self._check_ordering_item(obj, obj.model, field_name, 'ordering[%d]' % index)
                for index, field_name in enumerate(obj.ordering)
            ]))

    def _check_ordering_item(self, obj, model, field_name, label):
        """ Check that `ordering` refers to existing fields. """

        if field_name == '?' and len(obj.ordering) != 1:
            return [
                checks.Error(
                    "The value of 'ordering' has the random ordering marker '?', "
                    "but contains other fields as well.",
                    hint='Either remove the "?", or remove the other fields.',
                    obj=obj.__class__,
                    id='admin.E032',
                )
            ]
        elif field_name == '?':
            return []
        elif LOOKUP_SEP in field_name:
            # Skip ordering in the format field1__field2 (FIXME: checking
            # this format would be nice, but it's a little fiddly).
            return []
        else:
            if field_name.startswith('-'):
                field_name = field_name[1:]

            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist:
                return refer_to_missing_field(field=field_name, option=label, model=model, obj=obj, id='admin.E033')
            else:
                return []

    def _check_readonly_fields(self, obj):
        """ Check that readonly_fields refers to proper attribute or field. """

        if obj.readonly_fields == ():
            return []
        elif not isinstance(obj.readonly_fields, (list, tuple)):
            return must_be('a list or tuple', option='readonly_fields', obj=obj, id='admin.E034')
        else:
            return list(chain(*[
                self._check_readonly_fields_item(obj, obj.model, field_name, "readonly_fields[%d]" % index)
                for index, field_name in enumerate(obj.readonly_fields)
            ]))

    def _check_readonly_fields_item(self, obj, model, field_name, label):
        if callable(field_name):
            return []
        elif hasattr(obj, field_name):
            return []
        elif hasattr(model, field_name):
            return []
        else:
            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist:
                return [
                    checks.Error(
                        "The value of '%s' is not a callable, an attribute of '%s', or an attribute of '%s.%s'." % (
                            label, obj.__class__.__name__, model._meta.app_label, model._meta.object_name
                        ),
                        obj=obj.__class__,
                        id='admin.E035',
                    )
                ]
            else:
                return []


class ModelAdminChecks(BaseModelAdminChecks):

    def check(self, admin_obj, **kwargs):
        errors = super(ModelAdminChecks, self).check(admin_obj)
        errors.extend(self._check_save_as(admin_obj))
        errors.extend(self._check_save_on_top(admin_obj))
        errors.extend(self._check_inlines(admin_obj))
        errors.extend(self._check_list_display(admin_obj))
        errors.extend(self._check_list_display_links(admin_obj))
        errors.extend(self._check_list_filter(admin_obj))
        errors.extend(self._check_list_select_related(admin_obj))
        errors.extend(self._check_list_per_page(admin_obj))
        errors.extend(self._check_list_max_show_all(admin_obj))
        errors.extend(self._check_list_editable(admin_obj))
        errors.extend(self._check_search_fields(admin_obj))
        errors.extend(self._check_date_hierarchy(admin_obj))
        return errors

    def _check_save_as(self, obj):
        """ Check save_as is a boolean. """

        if not isinstance(obj.save_as, bool):
            return must_be('a boolean', option='save_as',
                           obj=obj, id='admin.E101')
        else:
            return []

    def _check_save_on_top(self, obj):
        """ Check save_on_top is a boolean. """

        if not isinstance(obj.save_on_top, bool):
            return must_be('a boolean', option='save_on_top',
                           obj=obj, id='admin.E102')
        else:
            return []

    def _check_inlines(self, obj):
        """ Check all inline model admin classes. """

        if not isinstance(obj.inlines, (list, tuple)):
            return must_be('a list or tuple', option='inlines', obj=obj, id='admin.E103')
        else:
            return list(chain(*[
                self._check_inlines_item(obj, obj.model, item, "inlines[%d]" % index)
                for index, item in enumerate(obj.inlines)
            ]))

    def _check_inlines_item(self, obj, model, inline, label):
        """ Check one inline model admin. """
        inline_label = '.'.join([inline.__module__, inline.__name__])

        from django.contrib.admin.options import InlineModelAdmin

        if not issubclass(inline, InlineModelAdmin):
            return [
                checks.Error(
                    "'%s' must inherit from 'InlineModelAdmin'." % inline_label,
                    obj=obj.__class__,
                    id='admin.E104',
                )
            ]
        elif not inline.model:
            return [
                checks.Error(
                    "'%s' must have a 'model' attribute." % inline_label,
                    obj=obj.__class__,
                    id='admin.E105',
                )
            ]
        elif not issubclass(inline.model, models.Model):
            return must_be('a Model', option='%s.model' % inline_label, obj=obj, id='admin.E106')
        else:
            return inline(model, obj.admin_site).check()

    def _check_list_display(self, obj):
        """ Check that list_display only contains fields or usable attributes.
        """

        if not isinstance(obj.list_display, (list, tuple)):
            return must_be('a list or tuple', option='list_display', obj=obj, id='admin.E107')
        else:
            return list(chain(*[
                self._check_list_display_item(obj, obj.model, item, "list_display[%d]" % index)
                for index, item in enumerate(obj.list_display)
            ]))

    def _check_list_display_item(self, obj, model, item, label):
        if callable(item):
            return []
        elif hasattr(obj, item):
            return []
        elif hasattr(model, item):
            # getattr(model, item) could be an X_RelatedObjectsDescriptor
            try:
                field = model._meta.get_field(item)
            except FieldDoesNotExist:
                try:
                    field = getattr(model, item)
                except AttributeError:
                    field = None

            if field is None:
                return [
                    checks.Error(
                        "The value of '%s' refers to '%s', which is not a "
                        "callable, an attribute of '%s', or an attribute or method on '%s.%s'." % (
                            label, item, obj.__class__.__name__, model._meta.app_label, model._meta.object_name
                        ),
                        obj=obj.__class__,
                        id='admin.E108',
                    )
                ]
            elif isinstance(field, models.ManyToManyField):
                return [
                    checks.Error(
                        "The value of '%s' must not be a ManyToManyField." % label,
                        obj=obj.__class__,
                        id='admin.E109',
                    )
                ]
            else:
                return []
        else:
            try:
                model._meta.get_field(item)
            except FieldDoesNotExist:
                return [
                    # This is a deliberate repeat of E108; there's more than one path
                    # required to test this condition.
                    checks.Error(
                        "The value of '%s' refers to '%s', which is not a callable, "
                        "an attribute of '%s', or an attribute or method on '%s.%s'." % (
                            label, item, obj.__class__.__name__, model._meta.app_label, model._meta.object_name
                        ),
                        obj=obj.__class__,
                        id='admin.E108',
                    )
                ]
            else:
                return []

    def _check_list_display_links(self, obj):
        """ Check that list_display_links is a unique subset of list_display.
        """
        from django.contrib.admin.options import ModelAdmin

        if obj.list_display_links is None:
            return []
        elif not isinstance(obj.list_display_links, (list, tuple)):
            return must_be('a list, a tuple, or None', option='list_display_links', obj=obj, id='admin.E110')
        # Check only if ModelAdmin.get_list_display() isn't overridden.
        elif obj.get_list_display.__code__ is ModelAdmin.get_list_display.__code__:
            # Use obj.get_list_display.__func__ is ModelAdmin.get_list_display
            # when dropping PY2.
            return list(chain(*[
                self._check_list_display_links_item(obj, field_name, "list_display_links[%d]" % index)
                for index, field_name in enumerate(obj.list_display_links)
            ]))
        return []

    def _check_list_display_links_item(self, obj, field_name, label):
        if field_name not in obj.list_display:
            return [
                checks.Error(
                    "The value of '%s' refers to '%s', which is not defined in 'list_display'." % (
                        label, field_name
                    ),
                    obj=obj.__class__,
                    id='admin.E111',
                )
            ]
        else:
            return []

    def _check_list_filter(self, obj):
        if not isinstance(obj.list_filter, (list, tuple)):
            return must_be('a list or tuple', option='list_filter', obj=obj, id='admin.E112')
        else:
            return list(chain(*[
                self._check_list_filter_item(obj, obj.model, item, "list_filter[%d]" % index)
                for index, item in enumerate(obj.list_filter)
            ]))

    def _check_list_filter_item(self, obj, model, item, label):
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
                return must_inherit_from(parent='ListFilter', option=label,
                                         obj=obj, id='admin.E113')
            # ...  but not a FieldListFilter.
            elif issubclass(item, FieldListFilter):
                return [
                    checks.Error(
                        "The value of '%s' must not inherit from 'FieldListFilter'." % label,
                        obj=obj.__class__,
                        id='admin.E114',
                    )
                ]
            else:
                return []
        elif isinstance(item, (tuple, list)):
            # item is option #2
            field, list_filter_class = item
            if not issubclass(list_filter_class, FieldListFilter):
                return must_inherit_from(parent='FieldListFilter', option='%s[1]' % label, obj=obj, id='admin.E115')
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
                        "The value of '%s' refers to '%s', which does not refer to a Field." % (label, field),
                        obj=obj.__class__,
                        id='admin.E116',
                    )
                ]
            else:
                return []

    def _check_list_select_related(self, obj):
        """ Check that list_select_related is a boolean, a list or a tuple. """

        if not isinstance(obj.list_select_related, (bool, list, tuple)):
            return must_be('a boolean, tuple or list', option='list_select_related', obj=obj, id='admin.E117')
        else:
            return []

    def _check_list_per_page(self, obj):
        """ Check that list_per_page is an integer. """

        if not isinstance(obj.list_per_page, int):
            return must_be('an integer', option='list_per_page', obj=obj, id='admin.E118')
        else:
            return []

    def _check_list_max_show_all(self, obj):
        """ Check that list_max_show_all is an integer. """

        if not isinstance(obj.list_max_show_all, int):
            return must_be('an integer', option='list_max_show_all', obj=obj, id='admin.E119')
        else:
            return []

    def _check_list_editable(self, obj):
        """ Check that list_editable is a sequence of editable fields from
        list_display without first element. """

        if not isinstance(obj.list_editable, (list, tuple)):
            return must_be('a list or tuple', option='list_editable', obj=obj, id='admin.E120')
        else:
            return list(chain(*[
                self._check_list_editable_item(obj, obj.model, item, "list_editable[%d]" % index)
                for index, item in enumerate(obj.list_editable)
            ]))

    def _check_list_editable_item(self, obj, model, field_name, label):
        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return refer_to_missing_field(field=field_name, option=label, model=model, obj=obj, id='admin.E121')
        else:
            if field_name not in obj.list_display:
                return [
                    checks.Error(
                        "The value of '%s' refers to '%s', which is not "
                        "contained in 'list_display'." % (label, field_name),
                        obj=obj.__class__,
                        id='admin.E122',
                    )
                ]
            elif obj.list_display_links and field_name in obj.list_display_links:
                return [
                    checks.Error(
                        "The value of '%s' cannot be in both 'list_editable' and 'list_display_links'." % field_name,
                        obj=obj.__class__,
                        id='admin.E123',
                    )
                ]
            # If list_display[0] is in list_editable, check that
            # list_display_links is set. See #22792 and #26229 for use cases.
            elif (obj.list_display[0] == field_name and not obj.list_display_links and
                    obj.list_display_links is not None):
                return [
                    checks.Error(
                        "The value of '%s' refers to the first field in 'list_display' ('%s'), "
                        "which cannot be used unless 'list_display_links' is set." % (
                            label, obj.list_display[0]
                        ),
                        obj=obj.__class__,
                        id='admin.E124',
                    )
                ]
            elif not field.editable:
                return [
                    checks.Error(
                        "The value of '%s' refers to '%s', which is not editable through the admin." % (
                            label, field_name
                        ),
                        obj=obj.__class__,
                        id='admin.E125',
                    )
                ]
            else:
                return []

    def _check_search_fields(self, obj):
        """ Check search_fields is a sequence. """

        if not isinstance(obj.search_fields, (list, tuple)):
            return must_be('a list or tuple', option='search_fields', obj=obj, id='admin.E126')
        else:
            return []

    def _check_date_hierarchy(self, obj):
        """ Check that date_hierarchy refers to DateField or DateTimeField. """

        if obj.date_hierarchy is None:
            return []
        else:
            try:
                field = get_fields_from_path(obj.model, obj.date_hierarchy)[-1]
            except (NotRelationField, FieldDoesNotExist):
                return [
                    checks.Error(
                        "The value of 'date_hierarchy' refers to '%s', which "
                        "does not refer to a Field." % obj.date_hierarchy,
                        obj=obj.__class__,
                        id='admin.E127',
                    )
                ]
            else:
                if not isinstance(field, (models.DateField, models.DateTimeField)):
                    return must_be('a DateField or DateTimeField', option='date_hierarchy', obj=obj, id='admin.E128')
                else:
                    return []


class InlineModelAdminChecks(BaseModelAdminChecks):

    def check(self, inline_obj, **kwargs):
        errors = super(InlineModelAdminChecks, self).check(inline_obj)
        parent_model = inline_obj.parent_model
        errors.extend(self._check_relation(inline_obj, parent_model))
        errors.extend(self._check_exclude_of_parent_model(inline_obj, parent_model))
        errors.extend(self._check_extra(inline_obj))
        errors.extend(self._check_max_num(inline_obj))
        errors.extend(self._check_min_num(inline_obj))
        errors.extend(self._check_formset(inline_obj))
        return errors

    def _check_exclude_of_parent_model(self, obj, parent_model):
        # Do not perform more specific checks if the base checks result in an
        # error.
        errors = super(InlineModelAdminChecks, self)._check_exclude(obj)
        if errors:
            return []

        # Skip if `fk_name` is invalid.
        if self._check_relation(obj, parent_model):
            return []

        if obj.exclude is None:
            return []

        fk = _get_foreign_key(parent_model, obj.model, fk_name=obj.fk_name)
        if fk.name in obj.exclude:
            return [
                checks.Error(
                    "Cannot exclude the field '%s', because it is the foreign key "
                    "to the parent model '%s.%s'." % (
                        fk.name, parent_model._meta.app_label, parent_model._meta.object_name
                    ),
                    obj=obj.__class__,
                    id='admin.E201',
                )
            ]
        else:
            return []

    def _check_relation(self, obj, parent_model):
        try:
            _get_foreign_key(parent_model, obj.model, fk_name=obj.fk_name)
        except ValueError as e:
            return [checks.Error(e.args[0], obj=obj.__class__, id='admin.E202')]
        else:
            return []

    def _check_extra(self, obj):
        """ Check that extra is an integer. """

        if not isinstance(obj.extra, int):
            return must_be('an integer', option='extra', obj=obj, id='admin.E203')
        else:
            return []

    def _check_max_num(self, obj):
        """ Check that max_num is an integer. """

        if obj.max_num is None:
            return []
        elif not isinstance(obj.max_num, int):
            return must_be('an integer', option='max_num', obj=obj, id='admin.E204')
        else:
            return []

    def _check_min_num(self, obj):
        """ Check that min_num is an integer. """

        if obj.min_num is None:
            return []
        elif not isinstance(obj.min_num, int):
            return must_be('an integer', option='min_num', obj=obj, id='admin.E205')
        else:
            return []

    def _check_formset(self, obj):
        """ Check formset is a subclass of BaseModelFormSet. """

        if not issubclass(obj.formset, BaseModelFormSet):
            return must_inherit_from(parent='BaseModelFormSet', option='formset', obj=obj, id='admin.E206')
        else:
            return []


def must_be(type, option, obj, id):
    return [
        checks.Error(
            "The value of '%s' must be %s." % (option, type),
            obj=obj.__class__,
            id=id,
        ),
    ]


def must_inherit_from(parent, option, obj, id):
    return [
        checks.Error(
            "The value of '%s' must inherit from '%s'." % (option, parent),
            obj=obj.__class__,
            id=id,
        ),
    ]


def refer_to_missing_field(field, option, model, obj, id):
    return [
        checks.Error(
            "The value of '%s' refers to '%s', which is not an attribute of '%s.%s'." % (
                option, field, model._meta.app_label, model._meta.object_name
            ),
            obj=obj.__class__,
            id=id,
        ),
    ]
