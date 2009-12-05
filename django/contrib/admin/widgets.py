"""
Form Widget classes specific to the Django admin site.
"""

import copy

from django import forms
from django.forms.widgets import RadioFieldRenderer
from django.forms.util import flatatt
from django.utils.text import truncate_words
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.template.loader import render_to_string
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch

class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/core.js",
              settings.ADMIN_MEDIA_PREFIX + "js/SelectBox.js",
              settings.ADMIN_MEDIA_PREFIX + "js/SelectFilter2.js")

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(FilteredSelectMultiple, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        output = [super(FilteredSelectMultiple, self).render(name, value, attrs, choices)]
        output.append(u'<script type="text/javascript">addEvent(window, "load", function(e) {')
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append(u'SelectFilter.init("id_%s", "%s", %s, "%s"); });</script>\n' % \
            (name, self.verbose_name.replace('"', '\\"'), int(self.is_stacked), settings.ADMIN_MEDIA_PREFIX))
        return mark_safe(u''.join(output))

class AdminDateWidget(forms.TextInput):
    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/calendar.js",
              settings.ADMIN_MEDIA_PREFIX + "js/admin/DateTimeShortcuts.js")

    def __init__(self, attrs={}):
        super(AdminDateWidget, self).__init__(attrs={'class': 'vDateField', 'size': '10'})

class AdminTimeWidget(forms.TextInput):
    class Media:
        js = (settings.ADMIN_MEDIA_PREFIX + "js/calendar.js",
              settings.ADMIN_MEDIA_PREFIX + "js/admin/DateTimeShortcuts.js")

    def __init__(self, attrs={}):
        super(AdminTimeWidget, self).__init__(attrs={'class': 'vTimeField', 'size': '8'})

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
        return mark_safe(u'<p class="datetime">%s %s<br />%s %s</p>' % \
            (_('Date:'), rendered_widgets[0], _('Time:'), rendered_widgets[1]))

class AdminRadioFieldRenderer(RadioFieldRenderer):
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul%s>\n%s\n</ul>' % (
            flatatt(self.attrs),
            u'\n'.join([u'<li>%s</li>' % force_unicode(w) for w in self]))
        )

class AdminRadioSelect(forms.RadioSelect):
    renderer = AdminRadioFieldRenderer

class AdminFileWidget(forms.FileInput):
    """
    A FileField Widget that shows its current value if it has one.
    """
    def __init__(self, attrs={}):
        super(AdminFileWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        output = []
        if value and hasattr(value, "url"):
            output.append('%s <a target="_blank" href="%s">%s</a> <br />%s ' % \
                (_('Currently:'), value.url, value, _('Change:')))
        output.append(super(AdminFileWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))

class ForeignKeyRawIdWidget(forms.TextInput):
    """
    A Widget for displaying ForeignKeys in the "raw_id" interface rather than
    in a <select> box.
    """
    def __init__(self, rel, attrs=None):
        self.rel = rel
        super(ForeignKeyRawIdWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        related_url = '../../../%s/%s/' % (self.rel.to._meta.app_label, self.rel.to._meta.object_name.lower())
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.
        output = [super(ForeignKeyRawIdWidget, self).render(name, value, attrs)]
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);"> ' % \
            (related_url, url, name))
        output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(u''.join(output))

    def base_url_parameters(self):
        params = {}
        if self.rel.limit_choices_to:
            items = []
            for k, v in self.rel.limit_choices_to.items():
                if isinstance(v, list):
                    v = ','.join([str(x) for x in v])
                else:
                    v = str(v)
                items.append((k, v))
            params.update(dict(items))
        return params

    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        obj = self.rel.to._default_manager.get(**{key: value})
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

class ForeignKeySearchInput(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ForeignKeys in an autocomplete search input
    instead in a <select> box.
    """
    # Set in subclass to render the widget with a different template
    widget_template = 'widget/foreignkey_searchinput.html'
 
    class Media:
        css = {
            'all': (settings.ADMIN_MEDIA_PREFIX + 'css/jquery.autocomplete.css',)
        }
        js = (
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.bgiframe.min.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.ajaxQueue.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.autocomplete.js',
        )
 
    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        obj = self.rel.to._default_manager.get(**{key: value})
        return truncate_words(obj, 14)
 
    def __init__(self, rel, search_fields, attrs=None):
        self.search_fields = search_fields
        super(ForeignKeySearchInput, self).__init__(rel, attrs)
 
    def get_search_path(self, name):
        return '../autocomplete/%s/' % name
    
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        output = [super(ForeignKeySearchInput, self).render(name, value, attrs)]
        opts = self.rel.to._meta
        app_label = opts.app_label
        model_name = opts.object_name.lower()
        related_url = '../../../%s/%s/' % (app_label, model_name)
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # Call the TextInput render method directly to have more control
        output = [forms.TextInput.render(self, name, value, attrs)]
        if value:
            label = self.label_for_value(value)
        else:
            label = u''
        context = {
            'url': url,
            'related_url': related_url,
            'admin_media_prefix': settings.ADMIN_MEDIA_PREFIX,
            'search_path': self.get_search_path(name),
            'search_fields': ','.join(self.search_fields),
            'model_name': model_name,
            'app_label': app_label,
            'label': label,
            'name': name,
        }
        output.append(render_to_string(self.widget_template or (
            'templates/widget/%s/%s/foreignkey_searchinput.html' % (app_label, model_name),
            'templates/widget/%s/foreignkey_searchinput.html' % app_label,
            'templates/widget/foreignkey_searchinput.html',
        ), context))
        output.reverse()
        return mark_safe(u''.join(output))

class ManyToManyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ManyToMany ids in the "raw_id" interface rather than
    in a <select multiple> box.
    """
    def __init__(self, rel, attrs=None):
        super(ManyToManyRawIdWidget, self).__init__(rel, attrs)

    def render(self, name, value, attrs=None):
        attrs['class'] = 'vManyToManyRawIdAdminField'
        if value:
            value = ','.join([str(v) for v in value])
        else:
            value = ''
        return super(ManyToManyRawIdWidget, self).render(name, value, attrs)

    def url_parameters(self):
        return self.base_url_parameters()

    def label_for_value(self, value):
        return ''

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        
        if value and value[-1] == ',':
            value = value[0:-1] # truncate trailing comma
        
        if value and ',' in value:
            return value.split(',')
        if value:
            return [value]
        return None

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        for pk1, pk2 in zip(initial, data):
            if force_unicode(pk1) != force_unicode(pk2):
                return True
        return False

class ManyToManySearchInput(ManyToManyRawIdWidget):
    """
    A Widget for displaying M2Ms in an autocomplete search input
    instead in a <select> box.
    """
    # Set in subclass to render the widget with a different template
    widget_template = 'widget/m2m_searchinput.html'
 
    class Media:
        css = {
            'all': (settings.ADMIN_MEDIA_PREFIX + 'css/jquery.token.input.css',)
        }
        js = (
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.tokeninput.js',
        )
    
    def __init__(self, rel, search_fields, attrs=None):
        self.search_fields = search_fields
        super(ManyToManySearchInput, self).__init__(rel, attrs)

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        objs = self.rel.to._default_manager.filter(**{key + '__in': value.split(',')})
        return ','.join([str(o) for o in objs])
        
    def get_search_path(self, name):
        return '../autocomplete/%s/' % name
    
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        output = [super(ManyToManySearchInput, self).render(name, value, attrs)]
        if value:
            value = ','.join([str(v) for v in value])
        else:
            value = ''
        opts = self.rel.to._meta
        app_label = opts.app_label
        model_name = opts.object_name.lower()
        related_url = '../../../%s/%s/' % (app_label, model_name)
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vM2MRawIdAdminField'
        # Call the TextInput render method directly to have more control
        output = [forms.TextInput.render(self, name, value, attrs)]
        if value:
            label = self.label_for_value(value)
        else:
            label = u''
        context = {
            'url': url,
            'related_url': related_url,
            'admin_media_prefix': settings.ADMIN_MEDIA_PREFIX,
            'search_path': self.get_search_path(name),
            'search_fields': ','.join(self.search_fields),
            'model_name': model_name,
            'app_label': app_label,
            'label': label,
            'name': name,
        }
        output.append(render_to_string(self.widget_template or (
            'templates/widget/%s/%s/m2m_searchinput.html' % (app_label, model_name),
            'templates/widget/%s/m2m_searchinput.html' % app_label,
            'templates/widget/m2m_searchinput.html',
        ), context))
        output.reverse()
        return mark_safe(u''.join(output))

class RelatedFieldWidgetWrapper(forms.Widget):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """
    def __init__(self, widget, rel, admin_site):
        self.is_hidden = widget.is_hidden
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.rel = rel
        # so we can check if the related object is registered with this AdminSite
        self.admin_site = admin_site

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    def _media(self):
        return self.widget.media
    media = property(_media)

    def render(self, name, value, *args, **kwargs):
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        try:
            related_url = reverse('admin:%s_%s_add' % info, current_app=self.admin_site.name)
        except NoReverseMatch:
            info = (self.admin_site.root_path, rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = '%s%s/%s/add/' % info
        self.widget.choices = self.choices
        output = [self.widget.render(name, value, *args, **kwargs)]
        if rel_to in self.admin_site._registry: # If the related object has an admin interface:
            # TODO: "id_" is hard-coded here. This should instead use the correct
            # API to determine the ID dynamically.
            output.append(u'<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
                (related_url, name))
            output.append(u'<img src="%simg/admin/icon_addlink.gif" width="10" height="10" alt="%s"/></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Add Another')))
        return mark_safe(u''.join(output))

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

class AdminIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vIntegerField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminIntegerFieldWidget, self).__init__(attrs=final_attrs)

class AdminCommaSeparatedIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vCommaSeparatedIntegerField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminCommaSeparatedIntegerFieldWidget, self).__init__(attrs=final_attrs)
