try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.forms.models import BaseModelForm, BaseModelFormSet, fields_for_model
from django.contrib.admin.options import flatten_fieldsets, BaseModelAdmin
from django.contrib.admin.options import HORIZONTAL, VERTICAL

def validate(cls, model):
    """
    Does basic ModelAdmin option validation. Calls custom validation
    classmethod in the end if it is provided in cls. The signature of the
    custom validation classmethod should be: def validate(cls, model).
    """
    opts = model._meta
    _validate_base(cls, model)

    # currying is expensive, use wrappers instead
    def _check_istuplew(label, obj):
        _check_istuple(cls, label, obj)

    def _check_isdictw(label, obj):
        _check_isdict(cls, label, obj)

    def _check_field_existsw(label, field):
        return _check_field_exists(cls, model, opts, label, field)

    def _check_attr_existsw(label, field):
        return _check_attr_exists(cls, model, opts, label, field)

    # list_display
    if hasattr(cls, 'list_display'):
        _check_istuplew('list_display', cls.list_display)
        for idx, field in enumerate(cls.list_display):
            if not callable(field):
                if not hasattr(cls, field):
                    if not hasattr(model, field):
                        try:
                            return opts.get_field(field)
                        except models.FieldDoesNotExist:
                            raise ImproperlyConfigured("%s.list_display[%d], %r is "
                                "not a callable or an attribute of %r or found in the model %r."
                                % (cls.__name__, idx, field, cls.__name__, model._meta.object_name))
                        f = _check_attr_existsw("list_display[%d]" % idx, field)
                        if isinstance(f, models.ManyToManyField):
                            raise ImproperlyConfigured("`%s.list_display[%d]`, `%s` is a "
                                "ManyToManyField which is not supported."
                                % (cls.__name__, idx, field))

    # list_display_links
    if hasattr(cls, 'list_display_links'):
        _check_istuplew('list_display_links', cls.list_display_links)
        for idx, field in enumerate(cls.list_display_links):
            _check_attr_existsw('list_display_links[%d]' % idx, field)
            if field not in cls.list_display:
                raise ImproperlyConfigured("`%s.list_display_links[%d]`"
                        "refers to `%s` which is not defined in `list_display`."
                        % (cls.__name__, idx, field))

    # list_filter
    if hasattr(cls, 'list_filter'):
        _check_istuplew('list_filter', cls.list_filter)
        for idx, field in enumerate(cls.list_filter):
            _check_field_existsw('list_filter[%d]' % idx, field)

    # list_per_page = 100
    if hasattr(cls, 'list_per_page') and not isinstance(cls.list_per_page, int):
        raise ImproperlyConfigured("`%s.list_per_page` should be a integer."
                % cls.__name__)

    # search_fields = ()
    if hasattr(cls, 'search_fields'):
        _check_istuplew('search_fields', cls.search_fields)
        
    # date_hierarchy = None
    if cls.date_hierarchy:
        f = _check_field_existsw('date_hierarchy', cls.date_hierarchy)
        if not isinstance(f, (models.DateField, models.DateTimeField)):
            raise ImproperlyConfigured("`%s.date_hierarchy is "
                    "neither an instance of DateField nor DateTimeField."
                    % cls.__name__)

    # ordering = None
    if cls.ordering:
        _check_istuplew('ordering', cls.ordering)
        for idx, field in enumerate(cls.ordering):
            if field == '?' and len(cls.ordering) != 1:
                raise ImproperlyConfigured("`%s.ordering` has the random "
                        "ordering marker `?`, but contains other fields as "
                        "well. Please either remove `?` or the other fields."
                        % cls.__name__)
            if field == '?':
                continue
            if field.startswith('-'):
                field = field[1:]
            # Skip ordering in the format field1__field2 (FIXME: checking
            # this format would be nice, but it's a little fiddly).
            if '__' in field:
                continue
            _check_field_existsw('ordering[%d]' % idx, field)

    # list_select_related = False
    # save_as = False
    # save_on_top = False
    for attr in ('list_select_related', 'save_as', 'save_on_top'):
        if not isinstance(getattr(cls, attr), bool):
            raise ImproperlyConfigured("`%s.%s` should be a boolean."
                    % (cls.__name__, attr))

    # inlines = []
    if hasattr(cls, 'inlines'):
        _check_istuplew('inlines', cls.inlines)
        for idx, inline in enumerate(cls.inlines):
            if not issubclass(inline, BaseModelAdmin):
                raise ImproperlyConfigured("`%s.inlines[%d]` does not inherit "
                        "from BaseModelAdmin." % (cls.__name__, idx))
            if not inline.model:
                raise ImproperlyConfigured("`model` is a required attribute "
                        "of `%s.inlines[%d]`." % (cls.__name__, idx))
            if not issubclass(inline.model, models.Model):
                raise ImproperlyConfigured("`%s.inlines[%d].model` does not "
                        "inherit from models.Model." % (cls.__name__, idx))
            _validate_base(inline, inline.model)
            _validate_inline(inline)
            
def _validate_inline(cls):
    # model is already verified to exist and be a Model
    if cls.fk_name: # default value is None
        f = _check_field_exists(cls, cls.model, cls.model._meta,
                'fk_name', cls.fk_name)
        if not isinstance(f, models.ForeignKey):
            raise ImproperlyConfigured("`%s.fk_name is not an instance of "
                    "models.ForeignKey." % cls.__name__)
    # extra = 3
    # max_num = 0
    for attr in ('extra', 'max_num'):
        if not isinstance(getattr(cls, attr), int):
            raise ImproperlyConfigured("`%s.%s` should be a integer."
                    % (cls.__name__, attr))

    # formset
    if hasattr(cls, 'formset') and not issubclass(cls.formset, BaseModelFormSet):
        raise ImproperlyConfigured("`%s.formset` does not inherit from "
                "BaseModelFormSet." % cls.__name__)

def _validate_base(cls, model):
    opts = model._meta
    # currying is expensive, use wrappers instead
    def _check_istuplew(label, obj):
        _check_istuple(cls, label, obj)

    def _check_isdictw(label, obj):
        _check_isdict(cls, label, obj)

    def _check_field_existsw(label, field):
        return _check_field_exists(cls, model, opts, label, field)
    
    def _check_form_field_existsw(label, field):
        return _check_form_field_exists(cls, model, opts, label, field)

    # raw_id_fields
    if hasattr(cls, 'raw_id_fields'):
        _check_istuplew('raw_id_fields', cls.raw_id_fields)
        for idx, field in enumerate(cls.raw_id_fields):
            f = _check_field_existsw('raw_id_fields', field)
            if not isinstance(f, (models.ForeignKey, models.ManyToManyField)):
                raise ImproperlyConfigured("`%s.raw_id_fields[%d]`, `%s` must "
                        "be either a ForeignKey or ManyToManyField."
                        % (cls.__name__, idx, field))

    # fields
    if cls.fields: # default value is None
        _check_istuplew('fields', cls.fields)
        for field in cls.fields:
            _check_form_field_existsw('fields', field)
        if cls.fieldsets:
            raise ImproperlyConfigured('Both fieldsets and fields are specified in %s.' % cls.__name__)
        if len(cls.fields) > len(set(cls.fields)):
            raise ImproperlyConfigured('There are duplicate field(s) in %s.fields' % cls.__name__)

    # fieldsets
    if cls.fieldsets: # default value is None
        _check_istuplew('fieldsets', cls.fieldsets)
        for idx, fieldset in enumerate(cls.fieldsets):
            _check_istuplew('fieldsets[%d]' % idx, fieldset)
            if len(fieldset) != 2:
                raise ImproperlyConfigured("`%s.fieldsets[%d]` does not "
                        "have exactly two elements." % (cls.__name__, idx))
            _check_isdictw('fieldsets[%d][1]' % idx, fieldset[1])
            if 'fields' not in fieldset[1]:
                raise ImproperlyConfigured("`fields` key is required in "
                        "%s.fieldsets[%d][1] field options dict."
                        % (cls.__name__, idx))
        flattened_fieldsets = flatten_fieldsets(cls.fieldsets)
        if len(flattened_fieldsets) > len(set(flattened_fieldsets)):
            raise ImproperlyConfigured('There are duplicate field(s) in %s.fieldsets' % cls.__name__)
        for field in flattened_fieldsets:
            _check_form_field_existsw("fieldsets[%d][1]['fields']" % idx, field)

    # form
    if hasattr(cls, 'form') and not issubclass(cls.form, BaseModelForm):
        raise ImproperlyConfigured("%s.form does not inherit from "
                "BaseModelForm." % cls.__name__)

    # filter_vertical
    if hasattr(cls, 'filter_vertical'):
        _check_istuplew('filter_vertical', cls.filter_vertical)
        for idx, field in enumerate(cls.filter_vertical):
            f = _check_field_existsw('filter_vertical', field)
            if not isinstance(f, models.ManyToManyField):
                raise ImproperlyConfigured("`%s.filter_vertical[%d]` must be "
                    "a ManyToManyField." % (cls.__name__, idx))

    # filter_horizontal
    if hasattr(cls, 'filter_horizontal'):
        _check_istuplew('filter_horizontal', cls.filter_horizontal)
        for idx, field in enumerate(cls.filter_horizontal):
            f = _check_field_existsw('filter_horizontal', field)
            if not isinstance(f, models.ManyToManyField):
                raise ImproperlyConfigured("`%s.filter_horizontal[%d]` must be "
                    "a ManyToManyField." % (cls.__name__, idx))

    # radio_fields
    if hasattr(cls, 'radio_fields'):
        _check_isdictw('radio_fields', cls.radio_fields)
        for field, val in cls.radio_fields.items():
            f = _check_field_existsw('radio_fields', field)
            if not (isinstance(f, models.ForeignKey) or f.choices):
                raise ImproperlyConfigured("`%s.radio_fields['%s']` "
                        "is neither an instance of ForeignKey nor does "
                        "have choices set." % (cls.__name__, field))
            if not val in (HORIZONTAL, VERTICAL):
                raise ImproperlyConfigured("`%s.radio_fields['%s']` "
                        "is neither admin.HORIZONTAL nor admin.VERTICAL."
                        % (cls.__name__, field))

    # prepopulated_fields
    if hasattr(cls, 'prepopulated_fields'):
        _check_isdictw('prepopulated_fields', cls.prepopulated_fields)
        for field, val in cls.prepopulated_fields.items():
            f = _check_field_existsw('prepopulated_fields', field)
            if isinstance(f, (models.DateTimeField, models.ForeignKey,
                models.ManyToManyField)):
                raise ImproperlyConfigured("`%s.prepopulated_fields['%s']` "
                        "is either a DateTimeField, ForeignKey or "
                        "ManyToManyField. This isn't allowed."
                        % (cls.__name__, field))
            _check_istuplew("prepopulated_fields['%s']" % field, val)
            for idx, f in enumerate(val):
                _check_field_existsw("prepopulated_fields['%s'][%d]"
                        % (f, idx), f)

def _check_istuple(cls, label, obj):
    if not isinstance(obj, (list, tuple)):
        raise ImproperlyConfigured("`%s.%s` must be a "
                "list or tuple." % (cls.__name__, label))

def _check_isdict(cls, label, obj):
    if not isinstance(obj, dict):
        raise ImproperlyConfigured("`%s.%s` must be a dictionary."
                % (cls.__name__, label))

def _check_field_exists(cls, model, opts, label, field):
    try:
        return opts.get_field(field)
    except models.FieldDoesNotExist:
        raise ImproperlyConfigured("`%s.%s` refers to "
                "field `%s` that is missing from model `%s`."
                % (cls.__name__, label, field, model.__name__))

def _check_form_field_exists(cls, model, opts, label, field):
    if hasattr(cls.form, 'base_fields'):
        try:
            cls.form.base_fields[field]
        except KeyError:
            raise ImproperlyConfigured("`%s.%s` refers to field `%s` that "
                "is missing from the form." % (cls.__name__, label, field))
    else:
        fields = fields_for_model(model)
        try:
            fields[field]
        except KeyError:
            raise ImproperlyConfigured("`%s.%s` refers to field `%s` that "
                "is missing from the form." % (cls.__name__, label, field))

def _check_attr_exists(cls, model, opts, label, field):
    try:
        return opts.get_field(field)
    except models.FieldDoesNotExist:
        if not hasattr(model, field):
            raise ImproperlyConfigured("`%s.%s` refers to "
                    "`%s` that is neither a field, method or property "
                    "of model `%s`."
                    % (cls.__name__, label, field, model.__name__))
        return getattr(model, field)
