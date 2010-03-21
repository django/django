from django import forms
from django.conf import settings
from django.contrib.admin.util import flatten_fieldsets, lookup_field
from django.contrib.admin.util import display_for_field, label_for_field
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ManyToManyRel
from django.forms.util import flatatt
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


ACTION_CHECKBOX_NAME = '_selected_action'

class ActionForm(forms.Form):
    action = forms.ChoiceField(label=_('Action:'))
    select_across = forms.BooleanField(label='', required=False, initial=0,
        widget=forms.HiddenInput({'class': 'select-across'}))

checkbox = forms.CheckboxInput({'class': 'action-select'}, lambda value: False)

class AdminForm(object):
    def __init__(self, form, fieldsets, prepopulated_fields, readonly_fields=None, model_admin=None):
        self.form, self.fieldsets = form, normalize_fieldsets(fieldsets)
        self.prepopulated_fields = [{
            'field': form[field_name],
            'dependencies': [form[f] for f in dependencies]
        } for field_name, dependencies in prepopulated_fields.items()]
        self.model_admin = model_admin
        if readonly_fields is None:
            readonly_fields = ()
        self.readonly_fields = readonly_fields

    def __iter__(self):
        for name, options in self.fieldsets:
            yield Fieldset(self.form, name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                **options
            )

    def first_field(self):
        try:
            fieldset_name, fieldset_options = self.fieldsets[0]
            field_name = fieldset_options['fields'][0]
            if not isinstance(field_name, basestring):
                field_name = field_name[0]
            return self.form[field_name]
        except (KeyError, IndexError):
            pass
        try:
            return iter(self.form).next()
        except StopIteration:
            return None

    def _media(self):
        media = self.form.media
        for fs in self:
            media = media + fs.media
        return media
    media = property(_media)

class Fieldset(object):
    def __init__(self, form, name=None, readonly_fields=(), fields=(), classes=(),
      description=None, model_admin=None):
        self.form = form
        self.name, self.fields = name, fields
        self.classes = u' '.join(classes)
        self.description = description
        self.model_admin = model_admin
        self.readonly_fields = readonly_fields

    def _media(self):
        if 'collapse' in self.classes:
            return forms.Media(js=['%sjs/collapse.min.js' % settings.ADMIN_MEDIA_PREFIX])
        return forms.Media()
    media = property(_media)

    def __iter__(self):
        for field in self.fields:
            yield Fieldline(self.form, field, self.readonly_fields, model_admin=self.model_admin)

class Fieldline(object):
    def __init__(self, form, field, readonly_fields=None, model_admin=None):
        self.form = form # A django.forms.Form instance
        if not hasattr(field, "__iter__"):
            self.fields = [field]
        else:
            self.fields = field
        self.model_admin = model_admin
        if readonly_fields is None:
            readonly_fields = ()
        self.readonly_fields = readonly_fields

    def __iter__(self):
        for i, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield AdminReadonlyField(self.form, field, is_first=(i == 0),
                    model_admin=self.model_admin)
            else:
                yield AdminField(self.form, field, is_first=(i == 0))

    def errors(self):
        return mark_safe(u'\n'.join([self.form[f].errors.as_ul() for f in self.fields if f not in self.readonly_fields]).strip('\n'))

class AdminField(object):
    def __init__(self, form, field, is_first):
        self.field = form[field] # A django.forms.BoundField instance
        self.is_first = is_first # Whether this field is first on the line
        self.is_checkbox = isinstance(self.field.field.widget, forms.CheckboxInput)

    def label_tag(self):
        classes = []
        if self.is_checkbox:
            classes.append(u'vCheckboxLabel')
            contents = force_unicode(escape(self.field.label))
        else:
            contents = force_unicode(escape(self.field.label)) + u':'
        if self.field.field.required:
            classes.append(u'required')
        if not self.is_first:
            classes.append(u'inline')
        attrs = classes and {'class': u' '.join(classes)} or {}
        return self.field.label_tag(contents=contents, attrs=attrs)

class AdminReadonlyField(object):
    def __init__(self, form, field, is_first, model_admin=None):
        self.field = field
        self.form = form
        self.model_admin = model_admin
        self.is_first = is_first
        self.is_checkbox = False
        self.is_readonly = True

    def label_tag(self):
        attrs = {}
        if not self.is_first:
            attrs["class"] = "inline"
        name = forms.forms.pretty_name(
            label_for_field(self.field, self.model_admin.model, self.model_admin)
        )
        contents = force_unicode(escape(name)) + u":"
        return mark_safe('<label%(attrs)s>%(contents)s</label>' % {
            "attrs": flatatt(attrs),
            "contents": contents,
        })

    def contents(self):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        field, obj, model_admin = self.field, self.form.instance, self.model_admin
        try:
            f, attr, value = lookup_field(field, obj, model_admin)
        except (AttributeError, ValueError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                boolean = getattr(attr, "boolean", False)
                if boolean:
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_unicode(value)
                    if getattr(attr, "allow_tags", False):
                        result_repr = mark_safe(result_repr)
            else:
                if value is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                elif isinstance(f.rel, ManyToManyRel):
                    result_repr = ", ".join(map(unicode, value.all()))
                else:
                    result_repr = display_for_field(value, f)
        return conditional_escape(result_repr)

class InlineAdminFormSet(object):
    """
    A wrapper around an inline formset for use in the admin system.
    """
    def __init__(self, inline, formset, fieldsets, readonly_fields=None, model_admin=None):
        self.opts = inline
        self.formset = formset
        self.fieldsets = fieldsets
        self.model_admin = model_admin
        if readonly_fields is None:
            readonly_fields = ()
        self.readonly_fields = readonly_fields

    def __iter__(self):
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, original, self.readonly_fields,
                model_admin=self.model_admin)
        for form in self.formset.extra_forms:
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, None, self.readonly_fields,
                model_admin=self.model_admin)
        yield InlineAdminForm(self.formset, self.formset.empty_form,
            self.fieldsets, self.opts.prepopulated_fields, None,
            self.readonly_fields, model_admin=self.model_admin)

    def fields(self):
        fk = getattr(self.formset, "fk", None)
        for i, field in enumerate(flatten_fieldsets(self.fieldsets)):
            if fk and fk.name == field:
                continue
            if field in self.readonly_fields:
                label = label_for_field(field, self.opts.model, self.model_admin)
                yield (False, forms.forms.pretty_name(label))
            else:
                field = self.formset.form.base_fields[field]
                yield (field.widget.is_hidden, field.label)

    def _media(self):
        media = self.opts.media + self.formset.media
        for fs in self:
            media = media + fs.media
        return media
    media = property(_media)

class InlineAdminForm(AdminForm):
    """
    A wrapper around an inline form for use in the admin system.
    """
    def __init__(self, formset, form, fieldsets, prepopulated_fields, original,
      readonly_fields=None, model_admin=None):
        self.formset = formset
        self.model_admin = model_admin
        self.original = original
        if original is not None:
            self.original_content_type_id = ContentType.objects.get_for_model(original).pk
        self.show_url = original and hasattr(original, 'get_absolute_url')
        super(InlineAdminForm, self).__init__(form, fieldsets, prepopulated_fields,
            readonly_fields)

    def __iter__(self):
        for name, options in self.fieldsets:
            yield InlineFieldset(self.formset, self.form, name,
                self.readonly_fields, model_admin=self.model_admin, **options)

    def has_auto_field(self):
        if self.form._meta.model._meta.has_auto_field:
            return True
        # Also search any parents for an auto field.
        for parent in self.form._meta.model._meta.get_parent_list():
            if parent._meta.has_auto_field:
                return True
        return False

    def field_count(self):
        # tabular.html uses this function for colspan value.
        num_of_fields = 0
        if self.has_auto_field():
            num_of_fields += 1
        num_of_fields += len(self.fieldsets[0][1]["fields"])
        if self.formset.can_order:
            num_of_fields += 1
        if self.formset.can_delete:
            num_of_fields += 1
        return num_of_fields

    def pk_field(self):
        return AdminField(self.form, self.formset._pk_field.name, False)

    def fk_field(self):
        fk = getattr(self.formset, "fk", None)
        if fk:
            return AdminField(self.form, fk.name, False)
        else:
            return ""

    def deletion_field(self):
        from django.forms.formsets import DELETION_FIELD_NAME
        return AdminField(self.form, DELETION_FIELD_NAME, False)

    def ordering_field(self):
        from django.forms.formsets import ORDERING_FIELD_NAME
        return AdminField(self.form, ORDERING_FIELD_NAME, False)

class InlineFieldset(Fieldset):
    def __init__(self, formset, *args, **kwargs):
        self.formset = formset
        super(InlineFieldset, self).__init__(*args, **kwargs)

    def __iter__(self):
        fk = getattr(self.formset, "fk", None)
        for field in self.fields:
            if fk and fk.name == field:
                continue
            yield Fieldline(self.form, field, self.readonly_fields,
                model_admin=self.model_admin)

class AdminErrorList(forms.util.ErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        if form.is_bound:
            self.extend(form.errors.values())
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(errors_in_inline_form.values())

def normalize_fieldsets(fieldsets):
    """
    Make sure the keys in fieldset dictionaries are strings. Returns the
    normalized data.
    """
    result = []
    for name, options in fieldsets:
        result.append((name, normalize_dictionary(options)))
    return result

def normalize_dictionary(data_dict):
    """
    Converts all the keys in "data_dict" to strings. The keys must be
    convertible using str().
    """
    for key, value in data_dict.items():
        if not isinstance(key, str):
            del data_dict[key]
            data_dict[str(key)] = value
    return data_dict

