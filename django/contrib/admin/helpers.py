from __future__ import unicode_literals

import warnings

from django import forms
from django.conf import settings
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.admin.utils import (
    display_for_field, flatten_fieldsets, help_text_for_field, label_for_field,
    lookup_field,
)
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ManyToManyRel
from django.forms.utils import flatatt
from django.template.defaultfilters import capfirst, linebreaksbr
from django.utils import six
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.encoding import force_text, smart_text
from django.utils.functional import cached_property
from django.utils.html import conditional_escape, format_html
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
        self.form, self.fieldsets = form, fieldsets
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
            yield Fieldset(
                self.form, name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                **options
            )

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
        self.classes = ' '.join(classes)
        self.description = description
        self.model_admin = model_admin
        self.readonly_fields = readonly_fields

    def _media(self):
        if 'collapse' in self.classes:
            extra = '' if settings.DEBUG else '.min'
            js = ['jquery%s.js' % extra,
                  'jquery.init.js',
                  'collapse%s.js' % extra]
            return forms.Media(js=[static('admin/js/%s' % url) for url in js])
        return forms.Media()
    media = property(_media)

    def __iter__(self):
        for field in self.fields:
            yield Fieldline(self.form, field, self.readonly_fields, model_admin=self.model_admin)


class Fieldline(object):
    def __init__(self, form, field, readonly_fields=None, model_admin=None):
        self.form = form  # A django.forms.Form instance
        if not hasattr(field, "__iter__") or isinstance(field, six.text_type):
            self.fields = [field]
        else:
            self.fields = field
        self.has_visible_field = not all(field in self.form.fields and
                                         self.form.fields[field].widget.is_hidden
                                         for field in self.fields)
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
        return mark_safe(
            '\n'.join(self.form[f].errors.as_ul()
            for f in self.fields if f not in self.readonly_fields).strip('\n')
        )


class AdminField(object):
    def __init__(self, form, field, is_first):
        self.field = form[field]  # A django.forms.BoundField instance
        self.is_first = is_first  # Whether this field is first on the line
        self.is_checkbox = isinstance(self.field.field.widget, forms.CheckboxInput)

    def label_tag(self):
        classes = []
        contents = conditional_escape(force_text(self.field.label))
        if self.is_checkbox:
            classes.append('vCheckboxLabel')

        if self.field.field.required:
            classes.append('required')
        if not self.is_first:
            classes.append('inline')
        attrs = {'class': ' '.join(classes)} if classes else {}
        # checkboxes should not have a label suffix as the checkbox appears
        # to the left of the label.
        return self.field.label_tag(contents=mark_safe(contents), attrs=attrs,
                                    label_suffix='' if self.is_checkbox else None)

    def errors(self):
        return mark_safe(self.field.errors.as_ul())


class AdminReadonlyField(object):
    def __init__(self, form, field, is_first, model_admin=None):
        # Make self.field look a little bit like a field. This means that
        # {{ field.name }} must be a useful class name to identify the field.
        # For convenience, store other field-related data here too.
        if callable(field):
            class_name = field.__name__ if field.__name__ != '<lambda>' else ''
        else:
            class_name = field

        if form._meta.labels and class_name in form._meta.labels:
            label = form._meta.labels[class_name]
        else:
            label = label_for_field(field, form._meta.model, model_admin)

        if form._meta.help_texts and class_name in form._meta.help_texts:
            help_text = form._meta.help_texts[class_name]
        else:
            help_text = help_text_for_field(class_name, form._meta.model)

        self.field = {
            'name': class_name,
            'label': label,
            'help_text': help_text,
            'field': field,
        }
        self.form = form
        self.model_admin = model_admin
        self.is_first = is_first
        self.is_checkbox = False
        self.is_readonly = True

    def label_tag(self):
        attrs = {}
        if not self.is_first:
            attrs["class"] = "inline"
        label = self.field['label']
        return format_html('<label{}>{}:</label>',
                           flatatt(attrs),
                           capfirst(force_text(label)))

    def contents(self):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        field, obj, model_admin = self.field['field'], self.form.instance, self.model_admin
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
                    result_repr = smart_text(value)
                    if getattr(attr, "allow_tags", False):
                        result_repr = mark_safe(result_repr)
                    else:
                        result_repr = linebreaksbr(result_repr)
            else:
                if isinstance(f.rel, ManyToManyRel) and value is not None:
                    result_repr = ", ".join(map(six.text_type, value.all()))
                else:
                    result_repr = display_for_field(value, f)
        return conditional_escape(result_repr)


class InlineAdminFormSet(object):
    """
    A wrapper around an inline formset for use in the admin system.
    """
    def __init__(self, inline, formset, fieldsets, prepopulated_fields=None,
            readonly_fields=None, model_admin=None):
        self.opts = inline
        self.formset = formset
        self.fieldsets = fieldsets
        self.model_admin = model_admin
        if readonly_fields is None:
            readonly_fields = ()
        self.readonly_fields = readonly_fields
        if prepopulated_fields is None:
            prepopulated_fields = {}
        self.prepopulated_fields = prepopulated_fields

    def __iter__(self):
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            view_on_site_url = self.opts.get_view_on_site_url(original)
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.prepopulated_fields, original, self.readonly_fields,
                model_admin=self.opts, view_on_site_url=view_on_site_url)
        for form in self.formset.extra_forms:
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.prepopulated_fields, None, self.readonly_fields,
                model_admin=self.opts)
        yield InlineAdminForm(self.formset, self.formset.empty_form,
            self.fieldsets, self.prepopulated_fields, None,
            self.readonly_fields, model_admin=self.opts)

    def fields(self):
        fk = getattr(self.formset, "fk", None)
        for i, field_name in enumerate(flatten_fieldsets(self.fieldsets)):
            if fk and fk.name == field_name:
                continue
            if field_name in self.readonly_fields:
                yield {
                    'label': label_for_field(field_name, self.opts.model, self.opts),
                    'widget': {
                        'is_hidden': False
                    },
                    'required': False,
                    'help_text': help_text_for_field(field_name, self.opts.model),
                }
            else:
                yield self.formset.form.base_fields[field_name]

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
      readonly_fields=None, model_admin=None, view_on_site_url=None):
        self.formset = formset
        self.model_admin = model_admin
        self.original = original
        self.show_url = original and view_on_site_url is not None
        self.absolute_url = view_on_site_url
        super(InlineAdminForm, self).__init__(form, fieldsets, prepopulated_fields,
            readonly_fields, model_admin)

    @cached_property
    def original_content_type_id(self):
        warnings.warn(
            'InlineAdminForm.original_content_type_id is deprecated and will be '
            'removed in Django 1.10. If you were using this attribute to construct '
            'the "view on site" URL, use the `absolute_url` attribute instead.',
            RemovedInDjango110Warning, stacklevel=2
        )
        if self.original is not None:
            # Since this module gets imported in the application's root package,
            # it cannot import models from other applications at the module level.
            from django.contrib.contenttypes.models import ContentType
            return ContentType.objects.get_for_model(self.original).pk
        raise AttributeError

    def __iter__(self):
        for name, options in self.fieldsets:
            yield InlineFieldset(self.formset, self.form, name,
                self.readonly_fields, model_admin=self.model_admin, **options)

    def needs_explicit_pk_field(self):
        # Auto fields are editable (oddly), so need to check for auto or non-editable pk
        if self.form._meta.model._meta.has_auto_field or not self.form._meta.model._meta.pk.editable:
            return True
        # Also search any parents for an auto field. (The pk info is propagated to child
        # models so that does not need to be checked in parents.)
        for parent in self.form._meta.model._meta.get_parent_list():
            if parent._meta.has_auto_field:
                return True
        return False

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


class AdminErrorList(forms.utils.ErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        super(AdminErrorList, self).__init__()

        if form.is_bound:
            self.extend(list(six.itervalues(form.errors)))
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(list(six.itervalues(errors_in_inline_form)))
