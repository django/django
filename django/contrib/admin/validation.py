from django.contrib.admin.utils import NotRelationField, get_fields_from_path
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.forms.models import (
    BaseModelForm, BaseModelFormSet, _get_foreign_key,
)

"""
Does basic ModelAdmin option validation. Calls custom validation
classmethod in the end if it is provided in cls. The signature of the
custom validation classmethod should be: def validate(cls, model).
"""

__all__ = ['BaseValidator', 'InlineValidator']


class BaseValidator(object):

    def validate(self, cls, model):
        for m in dir(self):
            if m.startswith('validate_'):
                getattr(self, m)(cls, model)

    def check_field_spec(self, cls, model, flds, label):
        """
        Validate the fields specification in `flds` from a ModelAdmin subclass
        `cls` for the `model` model. Use `label` for reporting problems to the user.

        The fields specification can be a ``fields`` option or a ``fields``
        sub-option from a ``fieldsets`` option component.
        """
        for fields in flds:
            # The entry in fields might be a tuple. If it is a standalone
            # field, make it into a tuple to make processing easier.
            if type(fields) != tuple:
                fields = (fields,)
            for field in fields:
                if field in cls.readonly_fields:
                    # Stuff can be put in fields that isn't actually a
                    # model field if it's in readonly_fields,
                    # readonly_fields will handle the validation of such
                    # things.
                    continue
                try:
                    f = model._meta.get_field(field)
                except FieldDoesNotExist:
                    # If we can't find a field on the model that matches, it could be an
                    # extra field on the form; nothing to check so move on to the next field.
                    continue
                if isinstance(f, models.ManyToManyField) and not f.rel.through._meta.auto_created:
                    raise ImproperlyConfigured("'%s.%s' "
                        "can't include the ManyToManyField field '%s' because "
                        "'%s' manually specifies a 'through' model." % (
                            cls.__name__, label, field, field))

    def validate_raw_id_fields(self, cls, model):
        " Validate that raw_id_fields only contains field names that are listed on the model. "
        if hasattr(cls, 'raw_id_fields'):
            check_isseq(cls, 'raw_id_fields', cls.raw_id_fields)
            for idx, field in enumerate(cls.raw_id_fields):
                f = get_field(cls, model, 'raw_id_fields', field)
                if not isinstance(f, (models.ForeignKey, models.ManyToManyField)):
                    raise ImproperlyConfigured("'%s.raw_id_fields[%d]', '%s' must "
                            "be either a ForeignKey or ManyToManyField."
                            % (cls.__name__, idx, field))

    def validate_fields(self, cls, model):
        " Validate that fields only refer to existing fields, doesn't contain duplicates. "
        # fields
        if cls.fields:  # default value is None
            check_isseq(cls, 'fields', cls.fields)
            self.check_field_spec(cls, model, cls.fields, 'fields')
            if cls.fieldsets:
                raise ImproperlyConfigured('Both fieldsets and fields are specified in %s.' % cls.__name__)
            if len(cls.fields) > len(set(cls.fields)):
                raise ImproperlyConfigured('There are duplicate field(s) in %s.fields' % cls.__name__)

    def validate_fieldsets(self, cls, model):
        " Validate that fieldsets is properly formatted and doesn't contain duplicates. "
        from django.contrib.admin.options import flatten_fieldsets
        if cls.fieldsets:  # default value is None
            check_isseq(cls, 'fieldsets', cls.fieldsets)
            for idx, fieldset in enumerate(cls.fieldsets):
                check_isseq(cls, 'fieldsets[%d]' % idx, fieldset)
                if len(fieldset) != 2:
                    raise ImproperlyConfigured("'%s.fieldsets[%d]' does not "
                            "have exactly two elements." % (cls.__name__, idx))
                check_isdict(cls, 'fieldsets[%d][1]' % idx, fieldset[1])
                if 'fields' not in fieldset[1]:
                    raise ImproperlyConfigured("'fields' key is required in "
                            "%s.fieldsets[%d][1] field options dict."
                            % (cls.__name__, idx))
                self.check_field_spec(cls, model, fieldset[1]['fields'], "fieldsets[%d][1]['fields']" % idx)
            flattened_fieldsets = flatten_fieldsets(cls.fieldsets)
            if len(flattened_fieldsets) > len(set(flattened_fieldsets)):
                raise ImproperlyConfigured('There are duplicate field(s) in %s.fieldsets' % cls.__name__)

    def validate_exclude(self, cls, model):
        " Validate that exclude is a sequence without duplicates. "
        if cls.exclude:  # default value is None
            check_isseq(cls, 'exclude', cls.exclude)
            if len(cls.exclude) > len(set(cls.exclude)):
                raise ImproperlyConfigured('There are duplicate field(s) in %s.exclude' % cls.__name__)

    def validate_form(self, cls, model):
        " Validate that form subclasses BaseModelForm. "
        if hasattr(cls, 'form') and not issubclass(cls.form, BaseModelForm):
            raise ImproperlyConfigured("%s.form does not inherit from "
                    "BaseModelForm." % cls.__name__)

    def validate_filter_vertical(self, cls, model):
        " Validate that filter_vertical is a sequence of field names. "
        if hasattr(cls, 'filter_vertical'):
            check_isseq(cls, 'filter_vertical', cls.filter_vertical)
            for idx, field in enumerate(cls.filter_vertical):
                f = get_field(cls, model, 'filter_vertical', field)
                if not isinstance(f, models.ManyToManyField):
                    raise ImproperlyConfigured("'%s.filter_vertical[%d]' must be "
                        "a ManyToManyField." % (cls.__name__, idx))

    def validate_filter_horizontal(self, cls, model):
        " Validate that filter_horizontal is a sequence of field names. "
        if hasattr(cls, 'filter_horizontal'):
            check_isseq(cls, 'filter_horizontal', cls.filter_horizontal)
            for idx, field in enumerate(cls.filter_horizontal):
                f = get_field(cls, model, 'filter_horizontal', field)
                if not isinstance(f, models.ManyToManyField):
                    raise ImproperlyConfigured("'%s.filter_horizontal[%d]' must be "
                        "a ManyToManyField." % (cls.__name__, idx))

    def validate_radio_fields(self, cls, model):
        " Validate that radio_fields is a dictionary of choice or foreign key fields. "
        from django.contrib.admin.options import HORIZONTAL, VERTICAL
        if hasattr(cls, 'radio_fields'):
            check_isdict(cls, 'radio_fields', cls.radio_fields)
            for field, val in cls.radio_fields.items():
                f = get_field(cls, model, 'radio_fields', field)
                if not (isinstance(f, models.ForeignKey) or f.choices):
                    raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                            "is neither an instance of ForeignKey nor does "
                            "have choices set." % (cls.__name__, field))
                if val not in (HORIZONTAL, VERTICAL):
                    raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                            "is neither admin.HORIZONTAL nor admin.VERTICAL."
                            % (cls.__name__, field))

    def validate_prepopulated_fields(self, cls, model):
        " Validate that prepopulated_fields if a dictionary  containing allowed field types. "
        # prepopulated_fields
        if hasattr(cls, 'prepopulated_fields'):
            check_isdict(cls, 'prepopulated_fields', cls.prepopulated_fields)
            for field, val in cls.prepopulated_fields.items():
                f = get_field(cls, model, 'prepopulated_fields', field)
                if isinstance(f, (models.DateTimeField, models.ForeignKey,
                        models.ManyToManyField)):
                    raise ImproperlyConfigured("'%s.prepopulated_fields['%s']' "
                            "is either a DateTimeField, ForeignKey or "
                            "ManyToManyField. This isn't allowed."
                            % (cls.__name__, field))
                check_isseq(cls, "prepopulated_fields['%s']" % field, val)
                for idx, f in enumerate(val):
                    get_field(cls, model, "prepopulated_fields['%s'][%d]" % (field, idx), f)

    def validate_view_on_site_url(self, cls, model):
        if hasattr(cls, 'view_on_site'):
            if not callable(cls.view_on_site) and not isinstance(cls.view_on_site, bool):
                raise ImproperlyConfigured("%s.view_on_site is not a callable or a boolean value." % cls.__name__)

    def validate_ordering(self, cls, model):
        " Validate that ordering refers to existing fields or is random. "
        # ordering = None
        if cls.ordering:
            check_isseq(cls, 'ordering', cls.ordering)
            for idx, field in enumerate(cls.ordering):
                if field == '?' and len(cls.ordering) != 1:
                    raise ImproperlyConfigured("'%s.ordering' has the random "
                            "ordering marker '?', but contains other fields as "
                            "well. Please either remove '?' or the other fields."
                            % cls.__name__)
                if field == '?':
                    continue
                if field.startswith('-'):
                    field = field[1:]
                # Skip ordering in the format field1__field2 (FIXME: checking
                # this format would be nice, but it's a little fiddly).
                if '__' in field:
                    continue
                get_field(cls, model, 'ordering[%d]' % idx, field)

    def validate_readonly_fields(self, cls, model):
        " Validate that readonly_fields refers to proper attribute or field. "
        if hasattr(cls, "readonly_fields"):
            check_isseq(cls, "readonly_fields", cls.readonly_fields)
            for idx, field in enumerate(cls.readonly_fields):
                if not callable(field):
                    if not hasattr(cls, field):
                        if not hasattr(model, field):
                            try:
                                model._meta.get_field(field)
                            except FieldDoesNotExist:
                                raise ImproperlyConfigured(
                                    "%s.readonly_fields[%d], %r is not a callable or "
                                    "an attribute of %r or found in the model %r."
                                    % (cls.__name__, idx, field, cls.__name__, model._meta.object_name)
                                )


class ModelAdminValidator(BaseValidator):
    def validate_save_as(self, cls, model):
        " Validate save_as is a boolean. "
        check_type(cls, 'save_as', bool)

    def validate_save_on_top(self, cls, model):
        " Validate save_on_top is a boolean. "
        check_type(cls, 'save_on_top', bool)

    def validate_inlines(self, cls, model):
        " Validate inline model admin classes. "
        from django.contrib.admin.options import BaseModelAdmin
        if hasattr(cls, 'inlines'):
            check_isseq(cls, 'inlines', cls.inlines)
            for idx, inline in enumerate(cls.inlines):
                if not issubclass(inline, BaseModelAdmin):
                    raise ImproperlyConfigured("'%s.inlines[%d]' does not inherit "
                            "from BaseModelAdmin." % (cls.__name__, idx))
                if not inline.model:
                    raise ImproperlyConfigured("'model' is a required attribute "
                            "of '%s.inlines[%d]'." % (cls.__name__, idx))
                if not issubclass(inline.model, models.Model):
                    raise ImproperlyConfigured("'%s.inlines[%d].model' does not "
                            "inherit from models.Model." % (cls.__name__, idx))
                inline.validate(inline.model)
                self.check_inline(inline, model)

    def check_inline(self, cls, parent_model):
        " Validate inline class's fk field is not excluded. "
        fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name, can_fail=True)
        if hasattr(cls, 'exclude') and cls.exclude:
            if fk and fk.name in cls.exclude:
                raise ImproperlyConfigured("%s cannot exclude the field "
                        "'%s' - this is the foreign key to the parent model "
                        "%s.%s." % (cls.__name__, fk.name, parent_model._meta.app_label, parent_model.__name__))

    def validate_list_display(self, cls, model):
        " Validate that list_display only contains fields or usable attributes. "
        if hasattr(cls, 'list_display'):
            check_isseq(cls, 'list_display', cls.list_display)
            for idx, field in enumerate(cls.list_display):
                if not callable(field):
                    if not hasattr(cls, field):
                        if not hasattr(model, field):
                            try:
                                model._meta.get_field(field)
                            except FieldDoesNotExist:
                                raise ImproperlyConfigured(
                                    "%s.list_display[%d], %r is not a callable or "
                                    "an attribute of %r or found in the model %r."
                                    % (cls.__name__, idx, field, cls.__name__, model._meta.object_name)
                                )
                        else:
                            # getattr(model, field) could be an X_RelatedObjectsDescriptor
                            f = fetch_attr(cls, model, "list_display[%d]" % idx, field)
                            if isinstance(f, models.ManyToManyField):
                                raise ImproperlyConfigured(
                                    "'%s.list_display[%d]', '%s' is a ManyToManyField "
                                    "which is not supported."
                                    % (cls.__name__, idx, field)
                                )

    def validate_list_display_links(self, cls, model):
        " Validate that list_display_links either is None or a unique subset of list_display."
        if hasattr(cls, 'list_display_links'):
            if cls.list_display_links is None:
                return
            check_isseq(cls, 'list_display_links', cls.list_display_links)
            for idx, field in enumerate(cls.list_display_links):
                if field not in cls.list_display:
                    raise ImproperlyConfigured("'%s.list_display_links[%d]' "
                            "refers to '%s' which is not defined in 'list_display'."
                            % (cls.__name__, idx, field))

    def validate_list_filter(self, cls, model):
        """
        Validate that list_filter is a sequence of one of three options:
            1: 'field' - a basic field filter, possibly w/ relationships (eg, 'field__rel')
            2: ('field', SomeFieldListFilter) - a field-based list filter class
            3: SomeListFilter - a non-field list filter class
        """
        from django.contrib.admin import ListFilter, FieldListFilter
        if hasattr(cls, 'list_filter'):
            check_isseq(cls, 'list_filter', cls.list_filter)
            for idx, item in enumerate(cls.list_filter):
                if callable(item) and not isinstance(item, models.Field):
                    # If item is option 3, it should be a ListFilter...
                    if not issubclass(item, ListFilter):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' is '%s'"
                                " which is not a descendant of ListFilter."
                                % (cls.__name__, idx, item.__name__))
                    # ...  but not a FieldListFilter.
                    if issubclass(item, FieldListFilter):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' is '%s'"
                                " which is of type FieldListFilter but is not"
                                " associated with a field name."
                                % (cls.__name__, idx, item.__name__))
                else:
                    if isinstance(item, (tuple, list)):
                        # item is option #2
                        field, list_filter_class = item
                        if not issubclass(list_filter_class, FieldListFilter):
                            raise ImproperlyConfigured("'%s.list_filter[%d][1]'"
                                " is '%s' which is not of type FieldListFilter."
                                % (cls.__name__, idx, list_filter_class.__name__))
                    else:
                        # item is option #1
                        field = item
                    # Validate the field string
                    try:
                        get_fields_from_path(model, field)
                    except (NotRelationField, FieldDoesNotExist):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' refers to '%s'"
                                " which does not refer to a Field."
                                % (cls.__name__, idx, field))

    def validate_list_select_related(self, cls, model):
        " Validate that list_select_related is a boolean, a list or a tuple. "
        list_select_related = getattr(cls, 'list_select_related', None)
        if list_select_related:
            types = (bool, tuple, list)
            if not isinstance(list_select_related, types):
                raise ImproperlyConfigured("'%s.list_select_related' should be "
                                           "either a bool, a tuple or a list" %
                                           cls.__name__)

    def validate_list_per_page(self, cls, model):
        " Validate that list_per_page is an integer. "
        check_type(cls, 'list_per_page', int)

    def validate_list_max_show_all(self, cls, model):
        " Validate that list_max_show_all is an integer. "
        check_type(cls, 'list_max_show_all', int)

    def validate_list_editable(self, cls, model):
        """
        Validate that list_editable is a sequence of editable fields from
        list_display without first element.
        """
        if hasattr(cls, 'list_editable') and cls.list_editable:
            check_isseq(cls, 'list_editable', cls.list_editable)
            for idx, field_name in enumerate(cls.list_editable):
                try:
                    field = model._meta.get_field(field_name)
                except FieldDoesNotExist:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                        "field, '%s', not defined on %s.%s."
                        % (cls.__name__, idx, field_name, model._meta.app_label, model.__name__))
                if field_name not in cls.list_display:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to "
                        "'%s' which is not defined in 'list_display'."
                        % (cls.__name__, idx, field_name))
                if cls.list_display_links is not None:
                    if field_name in cls.list_display_links:
                        raise ImproperlyConfigured("'%s' cannot be in both '%s.list_editable'"
                            " and '%s.list_display_links'"
                            % (field_name, cls.__name__, cls.__name__))
                    if not cls.list_display_links and cls.list_display[0] in cls.list_editable:
                        raise ImproperlyConfigured("'%s.list_editable[%d]' refers to"
                            " the first field in list_display, '%s', which can't be"
                            " used unless list_display_links is set."
                            % (cls.__name__, idx, cls.list_display[0]))
                if not field.editable:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                        "field, '%s', which isn't editable through the admin."
                        % (cls.__name__, idx, field_name))

    def validate_search_fields(self, cls, model):
        " Validate search_fields is a sequence. "
        if hasattr(cls, 'search_fields'):
            check_isseq(cls, 'search_fields', cls.search_fields)

    def validate_date_hierarchy(self, cls, model):
        " Validate that date_hierarchy refers to DateField or DateTimeField. "
        if cls.date_hierarchy:
            f = get_field(cls, model, 'date_hierarchy', cls.date_hierarchy)
            if not isinstance(f, (models.DateField, models.DateTimeField)):
                raise ImproperlyConfigured("'%s.date_hierarchy is "
                        "neither an instance of DateField nor DateTimeField."
                        % cls.__name__)


class InlineValidator(BaseValidator):
    def validate_fk_name(self, cls, model):
        " Validate that fk_name refers to a ForeignKey. "
        if cls.fk_name:  # default value is None
            f = get_field(cls, model, 'fk_name', cls.fk_name)
            if not isinstance(f, models.ForeignKey):
                raise ImproperlyConfigured("'%s.fk_name is not an instance of "
                        "models.ForeignKey." % cls.__name__)

    def validate_extra(self, cls, model):
        " Validate that extra is an integer. "
        check_type(cls, 'extra', int)

    def validate_max_num(self, cls, model):
        " Validate that max_num is an integer. "
        check_type(cls, 'max_num', int)

    def validate_formset(self, cls, model):
        " Validate formset is a subclass of BaseModelFormSet. "
        if hasattr(cls, 'formset') and not issubclass(cls.formset, BaseModelFormSet):
            raise ImproperlyConfigured("'%s.formset' does not inherit from "
                    "BaseModelFormSet." % cls.__name__)


def check_type(cls, attr, type_):
    if getattr(cls, attr, None) is not None and not isinstance(getattr(cls, attr), type_):
        raise ImproperlyConfigured("'%s.%s' should be a %s."
                % (cls.__name__, attr, type_.__name__))


def check_isseq(cls, label, obj):
    if not isinstance(obj, (list, tuple)):
        raise ImproperlyConfigured("'%s.%s' must be a list or tuple." % (cls.__name__, label))


def check_isdict(cls, label, obj):
    if not isinstance(obj, dict):
        raise ImproperlyConfigured("'%s.%s' must be a dictionary." % (cls.__name__, label))


def get_field(cls, model, label, field):
    try:
        return model._meta.get_field(field)
    except FieldDoesNotExist:
        raise ImproperlyConfigured("'%s.%s' refers to field '%s' that is missing from model '%s.%s'."
                % (cls.__name__, label, field, model._meta.app_label, model.__name__))


def fetch_attr(cls, model, label, field):
    try:
        return model._meta.get_field(field)
    except FieldDoesNotExist:
        pass
    try:
        return getattr(model, field)
    except AttributeError:
        raise ImproperlyConfigured(
            "'%s.%s' refers to '%s' that is neither a field, method or "
            "property of model '%s.%s'."
            % (cls.__name__, label, field, model._meta.app_label, model.__name__)
        )
