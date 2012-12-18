"""
Form Widget classes specific to the Django admin site.
"""
from __future__ import unicode_literals

import copy

from django import forms
from django.contrib.admin.templatetags.admin_static import static
from django.core.urlresolvers import reverse
from django.forms.widgets import RadioFieldRenderer
from django.forms.util import flatatt
from django.utils.html import escape, format_html, format_html_join, smart_urlquote
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils import six


class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    @property
    def media(self):
        js = ["core.js", "SelectBox.js", "SelectFilter2.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(FilteredSelectMultiple, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs['class'] = 'selectfilter'
        if self.is_stacked:
            attrs['class'] += 'stacked'
        output = [super(FilteredSelectMultiple, self).render(name, value, attrs, choices)]
        output.append('<script type="text/javascript">addEvent(window, "load", function(e) {')
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append('SelectFilter.init("id_%s", "%s", %s, "%s"); });</script>\n'
            % (name, self.verbose_name.replace('"', '\\"'), int(self.is_stacked), static('admin/')))
        return mark_safe(''.join(output))

class AdminDateWidget(forms.DateInput):

    @property
    def media(self):
        js = ["calendar.js", "admin/DateTimeShortcuts.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vDateField', 'size': '10'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminDateWidget, self).__init__(attrs=final_attrs, format=format)

class AdminTimeWidget(forms.TimeInput):

    @property
    def media(self):
        js = ["calendar.js", "admin/DateTimeShortcuts.js"]
        return forms.Media(js=[static("admin/js/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vTimeField', 'size': '8'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTimeWidget, self).__init__(attrs=final_attrs, format=format)

class AdminSplitDateTime(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    def __init__(self, attrs=None):
        widgets = [AdminDateWidget, AdminTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def format_output(self, rendered_widgets):
        return format_html('<p class="datetime">{0} {1}<br />{2} {3}</p>',
                           _('Date:'), rendered_widgets[0],
                           _('Time:'), rendered_widgets[1])

class AdminRadioFieldRenderer(RadioFieldRenderer):
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return format_html('<ul{0}>\n{1}\n</ul>',
                           flatatt(self.attrs),
                           format_html_join('\n', '<li>{0}</li>',
                                            ((force_text(w),) for w in self)))

class AdminRadioSelect(forms.RadioSelect):
    renderer = AdminRadioFieldRenderer

class AdminFileWidget(forms.ClearableFileInput):
    template_with_initial = ('<p class="file-upload">%s</p>'
                            % forms.ClearableFileInput.template_with_initial)
    template_with_clear = ('<span class="clearable-file-input">%s</span>'
                           % forms.ClearableFileInput.template_with_clear)

def url_params_from_lookup_dict(lookups):
    """
    Converts the type of lookups specified in a ForeignKey limit_choices_to
    attribute to a dictionary of query parameters
    """
    params = {}
    if lookups and hasattr(lookups, 'items'):
        items = []
        for k, v in lookups.items():
            if isinstance(v, (tuple, list)):
                v = ','.join([str(x) for x in v])
            elif isinstance(v, bool):
                # See django.db.fields.BooleanField.get_prep_lookup
                v = ('0', '1')[v]
            else:
                v = six.text_type(v)
            items.append((k, v))
        params.update(dict(items))
    return params

class ForeignKeyRawIdWidget(forms.TextInput):
    """
    A Widget for displaying ForeignKeys in the "raw_id" interface rather than
    in a <select> box.
    """
    def __init__(self, rel, admin_site, attrs=None, using=None):
        self.rel = rel
        self.admin_site = admin_site
        self.db = using
        super(ForeignKeyRawIdWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        rel_to = self.rel.to
        if attrs is None:
            attrs = {}
        extra = []
        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse('admin:%s_%s_changelist' %
                                    (rel_to._meta.app_label,
                                    rel_to._meta.module_name),
                                    current_app=self.admin_site.name)

            params = self.url_parameters()
            if params:
                url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
            else:
                url = ''
            if "class" not in attrs:
                attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript code looks for this hook.
            # TODO: "lookup_id_" is hard-coded here. This should instead use
            # the correct API to determine the ID dynamically.
            extra.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);"> '
                            % (related_url, url, name))
            extra.append('<img src="%s" width="16" height="16" alt="%s" /></a>'
                            % (static('admin/img/selector-search.gif'), _('Lookup')))
        output = [super(ForeignKeyRawIdWidget, self).render(name, value, attrs)] + extra
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(''.join(output))

    def base_url_parameters(self):
        return url_params_from_lookup_dict(self.rel.limit_choices_to)

    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
            return '&nbsp;<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, self.rel.to.DoesNotExist):
            return ''

class ManyToManyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ManyToMany ids in the "raw_id" interface rather than
    in a <select multiple> box.
    """
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        if self.rel.to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            attrs['class'] = 'vManyToManyRawIdAdminField'
        if value:
            value = ','.join([force_text(v) for v in value])
        else:
            value = ''
        return super(ManyToManyRawIdWidget, self).render(name, value, attrs)

    def url_parameters(self):
        return self.base_url_parameters()

    def label_for_value(self, value):
        return ''

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return value.split(',')

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        for pk1, pk2 in zip(initial, data):
            if force_text(pk1) != force_text(pk2):
                return True
        return False

class RelatedFieldWidgetWrapper(forms.Widget):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """
    def __init__(self, widget, rel, admin_site, can_add_related=None):
        self.is_hidden = widget.is_hidden
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.rel = rel
        # Backwards compatible check for whether a user can add related
        # objects.
        if can_add_related is None:
            can_add_related = rel.to in admin_site._registry
        self.can_add_related = can_add_related
        # so we can check if the related object is registered with this AdminSite
        self.admin_site = admin_site

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    @property
    def media(self):
        return self.widget.media

    def render(self, name, value, *args, **kwargs):
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        self.widget.choices = self.choices
        output = [self.widget.render(name, value, *args, **kwargs)]
        if self.can_add_related:
            related_url = reverse('admin:%s_%s_add' % info, current_app=self.admin_site.name)
            # TODO: "add_id_" is hard-coded here. This should instead use the
            # correct API to determine the ID dynamically.
            output.append('<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> '
                          % (related_url, name))
            output.append('<img src="%s" width="10" height="10" alt="%s"/></a>'
                          % (static('admin/img/icon_addlink.gif'), _('Add Another')))
        return mark_safe(''.join(output))

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
        return self.attrs

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def _has_changed(self, initial, data):
        return self.widget._has_changed(initial, data)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)

class AdminTextareaWidget(forms.Textarea):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vLargeTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextareaWidget, self).__init__(attrs=final_attrs)

class AdminTextInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextInputWidget, self).__init__(attrs=final_attrs)

class AdminURLFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vURLField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminURLFieldWidget, self).__init__(attrs=final_attrs)

    def render(self, name, value, attrs=None):
        html = super(AdminURLFieldWidget, self).render(name, value, attrs)
        if value:
            value = force_text(self._format_value(value))
            final_attrs = {'href': mark_safe(smart_urlquote(value))}
            html = format_html(
                '<p class="url">{0} <a {1}>{2}</a><br />{3} {4}</p>',
                _('Currently:'), flatatt(final_attrs), value,
                _('Change:'), html
            )
        return html


class AdminIntegerFieldWidget(forms.TextInput):
    class_name = 'vIntegerField'

    def __init__(self, attrs=None):
        final_attrs = {'class': self.class_name}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminIntegerFieldWidget, self).__init__(attrs=final_attrs)

class AdminBigIntegerFieldWidget(AdminIntegerFieldWidget):
    class_name = 'vBigIntegerField'

class AdminCommaSeparatedIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vCommaSeparatedIntegerField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminCommaSeparatedIntegerFieldWidget, self).__init__(attrs=final_attrs)
