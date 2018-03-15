"""
Form Widget classes specific to the Django admin site.
"""
import copy
import json

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.deletion import CASCADE
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.html import smart_urlquote
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import get_language, gettext as _


class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    @property
    def media(self):
        extra = '' if settings.DEBUG else '.min'
        js = [
            'vendor/jquery/jquery%s.js' % extra,
            'jquery.init.js',
            'core.js',
            'SelectBox.js',
            'SelectFilter2.js',
        ]
        return forms.Media(js=["admin/js/%s" % path for path in js])

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super().__init__(attrs, choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['attrs']['class'] = 'selectfilter'
        if self.is_stacked:
            context['widget']['attrs']['class'] += 'stacked'
        context['widget']['attrs']['data-field-name'] = self.verbose_name
        context['widget']['attrs']['data-is-stacked'] = int(self.is_stacked)
        return context


class AdminDateWidget(forms.DateInput):
    @property
    def media(self):
        extra = '' if settings.DEBUG else '.min'
        js = [
            'vendor/jquery/jquery%s.js' % extra,
            'jquery.init.js',
            'calendar.js',
            'admin/DateTimeShortcuts.js',
        ]
        return forms.Media(js=["admin/js/%s" % path for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vDateField', 'size': '10'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs, format=format)


class AdminTimeWidget(forms.TimeInput):
    @property
    def media(self):
        extra = '' if settings.DEBUG else '.min'
        js = [
            'vendor/jquery/jquery%s.js' % extra,
            'jquery.init.js',
            'calendar.js',
            'admin/DateTimeShortcuts.js',
        ]
        return forms.Media(js=["admin/js/%s" % path for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vTimeField', 'size': '8'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs, format=format)


class AdminSplitDateTime(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    template_name = 'admin/widgets/split_datetime.html'

    def __init__(self, attrs=None):
        widgets = [AdminDateWidget, AdminTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['date_label'] = _('Date:')
        context['time_label'] = _('Time:')
        return context


class AdminRadioSelect(forms.RadioSelect):
    template_name = 'admin/widgets/radio.html'


class AdminFileWidget(forms.ClearableFileInput):
    template_name = 'admin/widgets/clearable_file_input.html'


def url_params_from_lookup_dict(lookups):
    """
    Convert the type of lookups specified in a ForeignKey limit_choices_to
    attribute to a dictionary of query parameters
    """
    params = {}
    if lookups and hasattr(lookups, 'items'):
        for k, v in lookups.items():
            if callable(v):
                v = v()
            if isinstance(v, (tuple, list)):
                v = ','.join(str(x) for x in v)
            elif isinstance(v, bool):
                v = ('0', '1')[v]
            else:
                v = str(v)
            params[k] = v
    return params


class ForeignKeyRawIdWidget(forms.TextInput):
    """
    A Widget for displaying ForeignKeys in the "raw_id" interface rather than
    in a <select> box.
    """
    template_name = 'admin/widgets/foreign_key_raw_id.html'

    def __init__(self, rel, admin_site, attrs=None, using=None):
        self.rel = rel
        self.admin_site = admin_site
        self.db = using
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        rel_to = self.rel.model
        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse(
                'admin:%s_%s_changelist' % (
                    rel_to._meta.app_label,
                    rel_to._meta.model_name,
                ),
                current_app=self.admin_site.name,
            )

            params = self.url_parameters()
            if params:
                related_url += '?' + '&amp;'.join('%s=%s' % (k, v) for k, v in params.items())
            context['related_url'] = mark_safe(related_url)
            context['link_title'] = _('Lookup')
            # The JavaScript code looks for this class.
            context['widget']['attrs'].setdefault('class', 'vForeignKeyRawIdAdminField')
        if context['widget']['value']:
            context['link_label'], context['link_url'] = self.label_and_url_for_value(value)
        return context

    def base_url_parameters(self):
        limit_choices_to = self.rel.limit_choices_to
        if callable(limit_choices_to):
            limit_choices_to = limit_choices_to()
        return url_params_from_lookup_dict(limit_choices_to)

    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

    def label_and_url_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.model._default_manager.using(self.db).get(**{key: value})
        except (ValueError, self.rel.model.DoesNotExist, ValidationError):
            return '', ''

        try:
            url = reverse(
                '%s:%s_%s_change' % (
                    self.admin_site.name,
                    obj._meta.app_label,
                    obj._meta.object_name.lower(),
                ),
                args=(obj.pk,)
            )
        except NoReverseMatch:
            url = ''  # Admin not registered for target model.

        return Truncator(obj).words(14, truncate='...'), url


class ManyToManyRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ManyToMany ids in the "raw_id" interface rather than
    in a <select multiple> box.
    """
    template_name = 'admin/widgets/many_to_many_raw_id.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.rel.model in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            context['widget']['attrs']['class'] = 'vManyToManyRawIdAdminField'
        return context

    def url_parameters(self):
        return self.base_url_parameters()

    def label_and_url_for_value(self, value):
        return '', ''

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return value.split(',')

    def format_value(self, value):
        return ','.join(str(v) for v in value) if value else ''


class RelatedFieldWidgetWrapper(forms.Widget):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """
    template_name = 'admin/widgets/related_widget_wrapper.html'

    def __init__(self, widget, rel, admin_site, can_add_related=None,
                 can_change_related=False, can_delete_related=False):
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.rel = rel
        # Backwards compatible check for whether a user can add related
        # objects.
        if can_add_related is None:
            can_add_related = rel.model in admin_site._registry
        self.can_add_related = can_add_related
        # XXX: The UX does not support multiple selected values.
        multiple = getattr(widget, 'allow_multiple_selected', False)
        self.can_change_related = not multiple and can_change_related
        # XXX: The deletion UX can be confusing when dealing with cascading deletion.
        cascade = getattr(rel, 'on_delete', None) is CASCADE
        self.can_delete_related = not multiple and not cascade and can_delete_related
        # so we can check if the related object is registered with this AdminSite
        self.admin_site = admin_site

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    @property
    def is_hidden(self):
        return self.widget.is_hidden

    @property
    def media(self):
        return self.widget.media

    def get_related_url(self, info, action, *args):
        return reverse("admin:%s_%s_%s" % (info + (action,)),
                       current_app=self.admin_site.name, args=args)

    def get_context(self, name, value, attrs):
        from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
        rel_opts = self.rel.model._meta
        info = (rel_opts.app_label, rel_opts.model_name)
        self.widget.choices = self.choices
        url_params = '&'.join("%s=%s" % param for param in [
            (TO_FIELD_VAR, self.rel.get_related_field().name),
            (IS_POPUP_VAR, 1),
        ])
        context = {
            'rendered_widget': self.widget.render(name, value, attrs),
            'name': name,
            'url_params': url_params,
            'model': rel_opts.verbose_name,
        }
        if self.can_change_related:
            change_related_template_url = self.get_related_url(info, 'change', '__fk__')
            context.update(
                can_change_related=True,
                change_related_template_url=change_related_template_url,
            )
        if self.can_add_related:
            add_related_url = self.get_related_url(info, 'add')
            context.update(
                can_add_related=True,
                add_related_url=add_related_url,
            )
        if self.can_delete_related:
            delete_related_template_url = self.get_related_url(info, 'delete', '__fk__')
            context.update(
                can_delete_related=True,
                delete_related_template_url=delete_related_template_url,
            )
        return context

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def value_omitted_from_data(self, data, files, name):
        return self.widget.value_omitted_from_data(data, files, name)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)


class AdminTextareaWidget(forms.Textarea):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vLargeTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)


class AdminTextInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)


class AdminEmailInputWidget(forms.EmailInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vTextField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)


class AdminURLFieldWidget(forms.URLInput):
    template_name = 'admin/widgets/url.html'

    def __init__(self, attrs=None):
        final_attrs = {'class': 'vURLField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['current_label'] = _('Currently:')
        context['change_label'] = _('Change:')
        context['widget']['href'] = smart_urlquote(context['widget']['value']) if value else ''
        return context


class AdminIntegerFieldWidget(forms.NumberInput):
    class_name = 'vIntegerField'

    def __init__(self, attrs=None):
        final_attrs = {'class': self.class_name}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)


class AdminBigIntegerFieldWidget(AdminIntegerFieldWidget):
    class_name = 'vBigIntegerField'


# Mapping of lower case language codes [returned by Django's get_language()]
# to language codes supported by select2.
# See django/contrib/admin/static/admin/js/vendor/select2/i18n/*
SELECT2_TRANSLATIONS = {x.lower(): x for x in [
    'ar', 'az', 'bg', 'ca', 'cs', 'da', 'de', 'el', 'en', 'es', 'et',
    'eu', 'fa', 'fi', 'fr', 'gl', 'he', 'hi', 'hr', 'hu', 'id', 'is',
    'it', 'ja', 'km', 'ko', 'lt', 'lv', 'mk', 'ms', 'nb', 'nl', 'pl',
    'pt-BR', 'pt', 'ro', 'ru', 'sk', 'sr-Cyrl', 'sr', 'sv', 'th',
    'tr', 'uk', 'vi',
]}
SELECT2_TRANSLATIONS.update({'zh-hans': 'zh-CN', 'zh-hant': 'zh-TW'})


class AutocompleteMixin:
    """
    Select widget mixin that loads options from AutocompleteJsonView via AJAX.

    Renders the necessary data attributes for select2 and adds the static form
    media.
    """
    url_name = '%s:%s_%s_autocomplete'

    def __init__(self, rel, admin_site, attrs=None, choices=(), using=None):
        self.rel = rel
        self.admin_site = admin_site
        self.db = using
        self.choices = choices
        if attrs is not None:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}

    def get_url(self):
        model = self.rel.model
        return reverse(self.url_name % (self.admin_site.name, model._meta.app_label, model._meta.model_name))

    def build_attrs(self, base_attrs, extra_attrs=None):
        """
        Set select2's AJAX attributes.

        Attributes can be set using the html5 data attribute.
        Nested attributes require a double dash as per
        https://select2.org/configuration/data-attributes#nested-subkey-options
        """
        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs.setdefault('class', '')
        attrs.update({
            'data-ajax--cache': 'true',
            'data-ajax--type': 'GET',
            'data-ajax--url': self.get_url(),
            'data-theme': 'admin-autocomplete',
            'data-allow-clear': json.dumps(not self.is_required),
            'data-placeholder': '',  # Allows clearing of the input.
            'class': attrs['class'] + (' ' if attrs['class'] else '') + 'admin-autocomplete',
        })
        return attrs

    def optgroups(self, name, value, attr=None):
        """Return selected options based on the ModelChoiceIterator."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {
            str(v) for v in value
            if str(v) not in self.choices.field.empty_values
        }
        if not self.is_required and not self.allow_multiple_selected:
            default[1].append(self.create_option(name, '', '', False, 0))
        choices = (
            (obj.pk, self.choices.field.label_from_instance(obj))
            for obj in self.choices.queryset.using(self.db).filter(pk__in=selected_choices)
        )
        for option_value, option_label in choices:
            selected = (
                str(option_value) in value and
                (has_selected is False or self.allow_multiple_selected)
            )
            if selected is True and has_selected is False:
                has_selected = True
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(self.create_option(name, option_value, option_label, selected_choices, index))
        return groups

    @property
    def media(self):
        extra = '' if settings.DEBUG else '.min'
        i18n_name = SELECT2_TRANSLATIONS.get(get_language())
        i18n_file = ('admin/js/vendor/select2/i18n/%s.js' % i18n_name,) if i18n_name else ()
        return forms.Media(
            js=(
                'admin/js/vendor/jquery/jquery%s.js' % extra,
                'admin/js/vendor/select2/select2.full%s.js' % extra,
            ) + i18n_file + (
                'admin/js/jquery.init.js',
                'admin/js/autocomplete.js',
            ),
            css={
                'screen': (
                    'admin/css/vendor/select2/select2%s.css' % extra,
                    'admin/css/autocomplete.css',
                ),
            },
        )


class AutocompleteSelect(AutocompleteMixin, forms.Select):
    pass


class AutocompleteSelectMultiple(AutocompleteMixin, forms.SelectMultiple):
    pass
