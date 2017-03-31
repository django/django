"""
HTML Widget classes
"""

from __future__ import unicode_literals

import copy
import datetime
import re
from itertools import chain

from django.conf import settings
from django.forms.utils import flatatt, to_current_timezone
from django.templatetags.static import static
from django.utils import datetime_safe, formats, six
from django.utils.datastructures import MultiValueDict
from django.utils.dates import MONTHS
from django.utils.deprecation import (
    RemovedInDjango20Warning, RenameMethodsBase,
)
from django.utils.encoding import (
    force_str, force_text, python_2_unicode_compatible,
)
from django.utils.formats import get_format
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy

__all__ = (
    'Media', 'MediaDefiningClass', 'Widget', 'TextInput', 'NumberInput',
    'EmailInput', 'URLInput', 'PasswordInput', 'HiddenInput',
    'MultipleHiddenInput', 'FileInput', 'ClearableFileInput', 'Textarea',
    'DateInput', 'DateTimeInput', 'TimeInput', 'CheckboxInput', 'Select',
    'NullBooleanSelect', 'SelectMultiple', 'RadioSelect',
    'CheckboxSelectMultiple', 'MultiWidget', 'SplitDateTimeWidget',
    'SplitHiddenDateTimeWidget', 'SelectDateWidget',
)

MEDIA_TYPES = ('css', 'js')


@html_safe
@python_2_unicode_compatible
class Media(object):
    def __init__(self, media=None, **kwargs):
        if media:
            media_attrs = media.__dict__
        else:
            media_attrs = kwargs

        self._css = {}
        self._js = []

        for name in MEDIA_TYPES:
            getattr(self, 'add_' + name)(media_attrs.get(name))

    def __str__(self):
        return self.render()

    def render(self):
        return mark_safe('\n'.join(chain(*[getattr(self, 'render_' + name)() for name in MEDIA_TYPES])))

    def render_js(self):
        return [
            format_html(
                '<script type="text/javascript" src="{}"></script>',
                self.absolute_path(path)
            ) for path in self._js
        ]

    def render_css(self):
        # To keep rendering order consistent, we can't just iterate over items().
        # We need to sort the keys, and iterate over the sorted list.
        media = sorted(self._css.keys())
        return chain(*[[
            format_html(
                '<link href="{}" type="text/css" media="{}" rel="stylesheet" />',
                self.absolute_path(path), medium
            ) for path in self._css[medium]
        ] for medium in media])

    def absolute_path(self, path):
        """
        Given a relative or absolute path to a static asset, return an absolute
        path. An absolute path will be returned unchanged while a relative path
        will be passed to django.templatetags.static.static().
        """
        if path.startswith(('http://', 'https://', '/')):
            return path
        return static(path)

    def __getitem__(self, name):
        "Returns a Media object that only contains media of the given type"
        if name in MEDIA_TYPES:
            return Media(**{str(name): getattr(self, '_' + name)})
        raise KeyError('Unknown media type "%s"' % name)

    def add_js(self, data):
        if data:
            for path in data:
                if path not in self._js:
                    self._js.append(path)

    def add_css(self, data):
        if data:
            for medium, paths in data.items():
                for path in paths:
                    if not self._css.get(medium) or path not in self._css[medium]:
                        self._css.setdefault(medium, []).append(path)

    def __add__(self, other):
        combined = Media()
        for name in MEDIA_TYPES:
            getattr(combined, 'add_' + name)(getattr(self, '_' + name, None))
            getattr(combined, 'add_' + name)(getattr(other, '_' + name, None))
        return combined


def media_property(cls):
    def _media(self):
        # Get the media property of the superclass, if it exists
        sup_cls = super(cls, self)
        try:
            base = sup_cls.media
        except AttributeError:
            base = Media()

        # Get the media definition for this class
        definition = getattr(cls, 'Media', None)
        if definition:
            extend = getattr(definition, 'extend', True)
            if extend:
                if extend is True:
                    m = base
                else:
                    m = Media()
                    for medium in extend:
                        m = m + base[medium]
                return m + Media(definition)
            else:
                return Media(definition)
        else:
            return base
    return property(_media)


class MediaDefiningClass(type):
    """
    Metaclass for classes that can have media definitions.
    """
    def __new__(mcs, name, bases, attrs):
        new_class = super(MediaDefiningClass, mcs).__new__(mcs, name, bases, attrs)

        if 'media' not in attrs:
            new_class.media = media_property(new_class)

        return new_class


@html_safe
@python_2_unicode_compatible
class SubWidget(object):
    """
    Some widgets are made of multiple HTML elements -- namely, RadioSelect.
    This is a class that represents the "inner" HTML element of a widget.
    """
    def __init__(self, parent_widget, name, value, attrs, choices):
        self.parent_widget = parent_widget
        self.name, self.value = name, value
        self.attrs, self.choices = attrs, choices

    def __str__(self):
        args = [self.name, self.value, self.attrs]
        if self.choices:
            args.append(self.choices)
        return self.parent_widget.render(*args)


class RenameWidgetMethods(MediaDefiningClass, RenameMethodsBase):
    renamed_methods = (
        ('_format_value', 'format_value', RemovedInDjango20Warning),
    )


class Widget(six.with_metaclass(RenameWidgetMethods)):
    needs_multipart_form = False  # Determines does this widget need multipart form
    is_localized = False
    is_required = False
    supports_microseconds = True

    def __init__(self, attrs=None):
        if attrs is not None:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.attrs = self.attrs.copy()
        memo[id(self)] = obj
        return obj

    @property
    def is_hidden(self):
        return self.input_type == 'hidden' if hasattr(self, 'input_type') else False

    def subwidgets(self, name, value, attrs=None, choices=()):
        """
        Yields all "subwidgets" of this widget. Used only by RadioSelect to
        allow template access to individual <input type="radio"> buttons.

        Arguments are the same as for render().
        """
        yield SubWidget(self, name, value, attrs, choices)

    def render(self, name, value, attrs=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        raise NotImplementedError('subclasses of Widget must provide a render() method')

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        attrs = dict(self.attrs, **kwargs)
        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def value_from_datadict(self, data, files, name):
        """
        Given a dictionary of data and this widget's name, returns the value
        of this widget. Returns None if it's not provided.
        """
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return name not in data

    def id_for_label(self, id_):
        """
        Returns the HTML ID attribute of this Widget for use by a <label>,
        given the ID of the field. Returns None if no ID is available.

        This hook is necessary because some widgets have multiple HTML
        elements and, thus, multiple IDs. In that case, this method should
        return an ID value that corresponds to the first ID in the widget's
        tags.
        """
        return id_

    def use_required_attribute(self, initial):
        return not self.is_hidden


class Input(Widget):
    """
    Base class for all <input> widgets (except type='checkbox' and
    type='radio', which are special).
    """
    input_type = None  # Subclasses must define this.

    def format_value(self, value):
        if self.is_localized:
            return formats.localize_input(value)
        return value

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self.format_value(value))
        return format_html('<input{} />', flatatt(final_attrs))


class TextInput(Input):
    input_type = 'text'

    def __init__(self, attrs=None):
        if attrs is not None:
            self.input_type = attrs.pop('type', self.input_type)
        super(TextInput, self).__init__(attrs)


class NumberInput(TextInput):
    input_type = 'number'


class EmailInput(TextInput):
    input_type = 'email'


class URLInput(TextInput):
    input_type = 'url'


class PasswordInput(TextInput):
    input_type = 'password'

    def __init__(self, attrs=None, render_value=False):
        super(PasswordInput, self).__init__(attrs)
        self.render_value = render_value

    def render(self, name, value, attrs=None):
        if not self.render_value:
            value = None
        return super(PasswordInput, self).render(name, value, attrs)


class HiddenInput(Input):
    input_type = 'hidden'


class MultipleHiddenInput(HiddenInput):
    """
    A widget that handles <input type="hidden"> for fields that have a list
    of values.
    """
    def render(self, name, value, attrs=None):
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        id_ = final_attrs.get('id')
        inputs = []
        for i, v in enumerate(value):
            input_attrs = dict(value=force_text(v), **final_attrs)
            if id_:
                # An ID attribute was given. Add a numeric index as a suffix
                # so that the inputs don't all have the same ID attribute.
                input_attrs['id'] = '%s_%s' % (id_, i)
            inputs.append(format_html('<input{} />', flatatt(input_attrs)))
        return mark_safe('\n'.join(inputs))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, MultiValueDict):
            return data.getlist(name)
        return data.get(name)


class FileInput(Input):
    input_type = 'file'
    needs_multipart_form = True

    def render(self, name, value, attrs=None):
        return super(FileInput, self).render(name, None, attrs=attrs)

    def value_from_datadict(self, data, files, name):
        "File widgets take data from FILES, not POST"
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        return name not in files


FILE_INPUT_CONTRADICTION = object()


class ClearableFileInput(FileInput):
    initial_text = ugettext_lazy('Currently')
    input_text = ugettext_lazy('Change')
    clear_checkbox_label = ugettext_lazy('Clear')

    template_with_initial = (
        '%(initial_text)s: <a href="%(initial_url)s">%(initial)s</a> '
        '%(clear_template)s<br />%(input_text)s: %(input)s'
    )

    template_with_clear = '%(clear)s <label for="%(clear_checkbox_id)s">%(clear_checkbox_label)s</label>'

    def clear_checkbox_name(self, name):
        """
        Given the name of the file input, return the name of the clear checkbox
        input.
        """
        return name + '-clear'

    def clear_checkbox_id(self, name):
        """
        Given the name of the clear checkbox input, return the HTML id for it.
        """
        return name + '_id'

    def is_initial(self, value):
        """
        Return whether value is considered to be initial value.
        """
        return bool(value and getattr(value, 'url', False))

    def get_template_substitution_values(self, value):
        """
        Return value-related substitutions.
        """
        return {
            'initial': conditional_escape(value),
            'initial_url': conditional_escape(value.url),
        }

    def render(self, name, value, attrs=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'clear_template': '',
            'clear_checkbox_label': self.clear_checkbox_label,
        }
        template = '%(input)s'
        substitutions['input'] = super(ClearableFileInput, self).render(name, value, attrs)

        if self.is_initial(value):
            template = self.template_with_initial
            substitutions.update(self.get_template_substitution_values(value))
            if not self.is_required:
                checkbox_name = self.clear_checkbox_name(name)
                checkbox_id = self.clear_checkbox_id(checkbox_name)
                substitutions['clear_checkbox_name'] = conditional_escape(checkbox_name)
                substitutions['clear_checkbox_id'] = conditional_escape(checkbox_id)
                substitutions['clear'] = CheckboxInput().render(checkbox_name, False, attrs={'id': checkbox_id})
                substitutions['clear_template'] = self.template_with_clear % substitutions

        return mark_safe(template % substitutions)

    def value_from_datadict(self, data, files, name):
        upload = super(ClearableFileInput, self).value_from_datadict(data, files, name)
        if not self.is_required and CheckboxInput().value_from_datadict(
                data, files, self.clear_checkbox_name(name)):

            if upload:
                # If the user contradicts themselves (uploads a new file AND
                # checks the "clear" checkbox), we return a unique marker
                # object that FileField will turn into a ValidationError.
                return FILE_INPUT_CONTRADICTION
            # False signals to clear any existing value, as opposed to just None
            return False
        return upload

    def use_required_attribute(self, initial):
        return super(ClearableFileInput, self).use_required_attribute(initial) and not initial

    def value_omitted_from_data(self, data, files, name):
        return (
            super(ClearableFileInput, self).value_omitted_from_data(data, files, name) and
            self.clear_checkbox_name(name) not in data
        )


class Textarea(Widget):
    def __init__(self, attrs=None):
        # Use slightly better defaults than HTML's 20x2 box
        default_attrs = {'cols': '40', 'rows': '10'}
        if attrs:
            default_attrs.update(attrs)
        super(Textarea, self).__init__(default_attrs)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{}>\r\n{}</textarea>', flatatt(final_attrs), force_text(value))


class DateTimeBaseInput(TextInput):
    format_key = ''
    supports_microseconds = False

    def __init__(self, attrs=None, format=None):
        super(DateTimeBaseInput, self).__init__(attrs)
        self.format = format if format else None

    def format_value(self, value):
        return formats.localize_input(value, self.format or formats.get_format(self.format_key)[0])


class DateInput(DateTimeBaseInput):
    format_key = 'DATE_INPUT_FORMATS'


class DateTimeInput(DateTimeBaseInput):
    format_key = 'DATETIME_INPUT_FORMATS'


class TimeInput(DateTimeBaseInput):
    format_key = 'TIME_INPUT_FORMATS'


# Defined at module level so that CheckboxInput is picklable (#17976)
def boolean_check(v):
    return not (v is False or v is None or v == '')


class CheckboxInput(Widget):
    def __init__(self, attrs=None, check_test=None):
        super(CheckboxInput, self).__init__(attrs)
        # check_test is a callable that takes a value and returns True
        # if the checkbox should be checked for that value.
        self.check_test = boolean_check if check_test is None else check_test

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='checkbox', name=name)
        if self.check_test(value):
            final_attrs['checked'] = 'checked'
        if not (value is True or value is False or value is None or value == ''):
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(value)
        return format_html('<input{} />', flatatt(final_attrs))

    def value_from_datadict(self, data, files, name):
        if name not in data:
            # A missing value means False because HTML form submission does not
            # send results for unselected checkboxes.
            return False
        value = data.get(name)
        # Translate true and false strings to boolean values.
        values = {'true': True, 'false': False}
        if isinstance(value, six.string_types):
            value = values.get(value.lower(), value)
        return bool(value)

    def value_omitted_from_data(self, data, files, name):
        # HTML checkboxes don't appear in POST data if not checked, so it's
        # never known if the value is actually omitted.
        return False


class Select(Widget):
    allow_multiple_selected = False

    def __init__(self, attrs=None, choices=()):
        super(Select, self).__init__(attrs)
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = list(choices)

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.attrs = self.attrs.copy()
        obj.choices = copy.copy(self.choices)
        memo[id(self)] = obj
        return obj

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html('<select{}>', flatatt(final_attrs))]
        options = self.render_options([value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return format_html('<option value="{}"{}>{}</option>', option_value, selected_html, force_text(option_label))

    def render_options(self, selected_choices):
        # Normalize to strings.
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        for option_value, option_label in self.choices:
            if isinstance(option_label, (list, tuple)):
                output.append(format_html('<optgroup label="{}">', force_text(option_value)))
                for option in option_label:
                    output.append(self.render_option(selected_choices, *option))
                output.append('</optgroup>')
            else:
                output.append(self.render_option(selected_choices, option_value, option_label))
        return '\n'.join(output)


class NullBooleanSelect(Select):
    """
    A Select Widget intended to be used with NullBooleanField.
    """
    def __init__(self, attrs=None):
        choices = (
            ('1', ugettext_lazy('Unknown')),
            ('2', ugettext_lazy('Yes')),
            ('3', ugettext_lazy('No')),
        )
        super(NullBooleanSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None):
        try:
            value = {True: '2', False: '3', '2': '2', '3': '3'}[value]
        except KeyError:
            value = '1'
        return super(NullBooleanSelect, self).render(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return {
            '2': True,
            True: True,
            'True': True,
            '3': False,
            'False': False,
            False: False,
        }.get(value)


class SelectMultiple(Select):
    allow_multiple_selected = True

    def render(self, name, value, attrs=None):
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html('<select multiple="multiple"{}>', flatatt(final_attrs))]
        options = self.render_options(value)
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, MultiValueDict):
            return data.getlist(name)
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        # An unselected <select multiple> doesn't appear in POST data, so it's
        # never known if the value is actually omitted.
        return False


@html_safe
@python_2_unicode_compatible
class ChoiceInput(SubWidget):
    """
    An object used by ChoiceFieldRenderer that represents a single
    <input type='$input_type'>.
    """
    input_type = None  # Subclasses must define this

    def __init__(self, name, value, attrs, choice, index):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choice_value = force_text(choice[0])
        self.choice_label = force_text(choice[1])
        self.index = index
        if 'id' in self.attrs:
            self.attrs['id'] += "_%d" % self.index

    def __str__(self):
        return self.render()

    def render(self, name=None, value=None, attrs=None):
        if self.id_for_label:
            label_for = format_html(' for="{}"', self.id_for_label)
        else:
            label_for = ''
        attrs = dict(self.attrs, **attrs) if attrs else self.attrs
        return format_html(
            '<label{}>{} {}</label>', label_for, self.tag(attrs), self.choice_label
        )

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self, attrs=None):
        attrs = attrs or self.attrs
        final_attrs = dict(attrs, type=self.input_type, name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return format_html('<input{} />', flatatt(final_attrs))

    @property
    def id_for_label(self):
        return self.attrs.get('id', '')


class RadioChoiceInput(ChoiceInput):
    input_type = 'radio'

    def __init__(self, *args, **kwargs):
        super(RadioChoiceInput, self).__init__(*args, **kwargs)
        self.value = force_text(self.value)


class CheckboxChoiceInput(ChoiceInput):
    input_type = 'checkbox'

    def __init__(self, *args, **kwargs):
        super(CheckboxChoiceInput, self).__init__(*args, **kwargs)
        self.value = set(force_text(v) for v in self.value)

    def is_checked(self):
        return self.choice_value in self.value


@html_safe
@python_2_unicode_compatible
class ChoiceFieldRenderer(object):
    """
    An object used by RadioSelect to enable customization of radio widgets.
    """

    choice_input_class = None
    outer_html = '<ul{id_attr}>{content}</ul>'
    inner_html = '<li>{choice_value}{sub_widgets}</li>'

    def __init__(self, name, value, attrs, choices):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choices = choices

    def __getitem__(self, idx):
        return list(self)[idx]

    def __iter__(self):
        for idx, choice in enumerate(self.choices):
            yield self.choice_input_class(self.name, self.value, self.attrs.copy(), choice, idx)

    def __str__(self):
        return self.render()

    def render(self):
        """
        Outputs a <ul> for this set of choice fields.
        If an id was given to the field, it is applied to the <ul> (each
        item in the list will get an id of `$id_$i`).
        """
        id_ = self.attrs.get('id')
        output = []
        for i, choice in enumerate(self.choices):
            choice_value, choice_label = choice
            if isinstance(choice_label, (tuple, list)):
                attrs_plus = self.attrs.copy()
                if id_:
                    attrs_plus['id'] += '_{}'.format(i)
                sub_ul_renderer = self.__class__(
                    name=self.name,
                    value=self.value,
                    attrs=attrs_plus,
                    choices=choice_label,
                )
                sub_ul_renderer.choice_input_class = self.choice_input_class
                output.append(format_html(
                    self.inner_html, choice_value=choice_value,
                    sub_widgets=sub_ul_renderer.render(),
                ))
            else:
                w = self.choice_input_class(self.name, self.value, self.attrs.copy(), choice, i)
                output.append(format_html(self.inner_html, choice_value=force_text(w), sub_widgets=''))
        return format_html(
            self.outer_html,
            id_attr=format_html(' id="{}"', id_) if id_ else '',
            content=mark_safe('\n'.join(output)),
        )


class RadioFieldRenderer(ChoiceFieldRenderer):
    choice_input_class = RadioChoiceInput


class CheckboxFieldRenderer(ChoiceFieldRenderer):
    choice_input_class = CheckboxChoiceInput


class RendererMixin(object):
    renderer = None  # subclasses must define this
    _empty_value = None

    def __init__(self, *args, **kwargs):
        # Override the default renderer if we were passed one.
        renderer = kwargs.pop('renderer', None)
        if renderer:
            self.renderer = renderer
        super(RendererMixin, self).__init__(*args, **kwargs)

    def subwidgets(self, name, value, attrs=None):
        for widget in self.get_renderer(name, value, attrs):
            yield widget

    def get_renderer(self, name, value, attrs=None):
        """Returns an instance of the renderer."""
        if value is None:
            value = self._empty_value
        final_attrs = self.build_attrs(attrs)
        return self.renderer(name, value, final_attrs, self.choices)

    def render(self, name, value, attrs=None):
        return self.get_renderer(name, value, attrs).render()

    def id_for_label(self, id_):
        # Widgets using this RendererMixin are made of a collection of
        # subwidgets, each with their own <label>, and distinct ID.
        # The IDs are made distinct by a "_X" suffix, where X is the zero-based
        # index of the choice field. Thus, the label for the main widget should
        # reference the first subwidget, hence the "_0" suffix.
        if id_:
            id_ += '_0'
        return id_


class RadioSelect(RendererMixin, Select):
    renderer = RadioFieldRenderer
    _empty_value = ''


class CheckboxSelectMultiple(RendererMixin, SelectMultiple):
    renderer = CheckboxFieldRenderer
    _empty_value = []

    def use_required_attribute(self, initial):
        # Don't use the 'required' attribute because browser validation would
        # require all checkboxes to be checked instead of at least one.
        return False

    def value_omitted_from_data(self, data, files, name):
        # HTML checkboxes don't appear in POST data if not checked, so it's
        # never known if the value is actually omitted.
        return False


class MultiWidget(Widget):
    """
    A widget that is composed of multiple widgets.

    Its render() method is different than other widgets', because it has to
    figure out how to split a single value for display in multiple widgets.
    The ``value`` argument can be one of two things:

        * A list.
        * A normal value (e.g., a string) that has been "compressed" from
          a list of values.

    In the second case -- i.e., if the value is NOT a list -- render() will
    first "decompress" the value into a list before rendering it. It does so by
    calling the decompress() method, which MultiWidget subclasses must
    implement. This method takes a single "compressed" value and returns a
    list.

    When render() does its HTML rendering, each value in the list is rendered
    with the corresponding widget -- the first value is rendered in the first
    widget, the second value is rendered in the second widget, etc.

    Subclasses may implement format_output(), which takes the list of rendered
    widgets and returns a string of HTML that formats them any way you'd like.

    You'll probably want to use this class with MultiValueField.
    """
    def __init__(self, widgets, attrs=None):
        self.widgets = [w() if isinstance(w, type) else w for w in widgets]
        super(MultiWidget, self).__init__(attrs)

    @property
    def is_hidden(self):
        return all(w.is_hidden for w in self.widgets)

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
        return mark_safe(self.format_output(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_

    def value_from_datadict(self, data, files, name):
        return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]

    def value_omitted_from_data(self, data, files, name):
        return all(
            widget.value_omitted_from_data(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)
        )

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), returns a Unicode string
        representing the HTML for the whole lot.

        This hook allows you to format the HTML design of the widgets, if
        needed.
        """
        return ''.join(rendered_widgets)

    def decompress(self, value):
        """
        Returns a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """
        raise NotImplementedError('Subclasses must implement this method.')

    def _get_media(self):
        "Media for a multiwidget is the combination of all media of the subwidgets"
        media = Media()
        for w in self.widgets:
            media = media + w.media
        return media
    media = property(_get_media)

    def __deepcopy__(self, memo):
        obj = super(MultiWidget, self).__deepcopy__(memo)
        obj.widgets = copy.deepcopy(self.widgets)
        return obj

    @property
    def needs_multipart_form(self):
        return any(w.needs_multipart_form for w in self.widgets)


class SplitDateTimeWidget(MultiWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.
    """
    supports_microseconds = False

    def __init__(self, attrs=None, date_format=None, time_format=None):
        widgets = (
            DateInput(attrs=attrs, format=date_format),
            TimeInput(attrs=attrs, format=time_format),
        )
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class SplitHiddenDateTimeWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="hidden"> inputs.
    """
    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(SplitHiddenDateTimeWidget, self).__init__(attrs, date_format, time_format)
        for widget in self.widgets:
            widget.input_type = 'hidden'


class SelectDateWidget(Widget):
    """
    A Widget that splits date input into three <select> boxes.

    This also serves as an example of a Widget that has more than one HTML
    element and hence implements value_from_datadict.
    """
    none_value = (0, '---')
    month_field = '%s_month'
    day_field = '%s_day'
    year_field = '%s_year'
    select_widget = Select

    date_re = re.compile(r'(\d{4})-(\d\d?)-(\d\d?)$')

    def __init__(self, attrs=None, years=None, months=None, empty_label=None):
        self.attrs = attrs or {}

        # Optional list or tuple of years to use in the "year" select box.
        if years:
            self.years = years
        else:
            this_year = datetime.date.today().year
            self.years = range(this_year, this_year + 10)

        # Optional dict of months to use in the "month" select box.
        if months:
            self.months = months
        else:
            self.months = MONTHS

        # Optional string, list, or tuple to use as empty_label.
        if isinstance(empty_label, (list, tuple)):
            if not len(empty_label) == 3:
                raise ValueError('empty_label list/tuple must have 3 elements.')

            self.year_none_value = (0, empty_label[0])
            self.month_none_value = (0, empty_label[1])
            self.day_none_value = (0, empty_label[2])
        else:
            if empty_label is not None:
                self.none_value = (0, empty_label)

            self.year_none_value = self.none_value
            self.month_none_value = self.none_value
            self.day_none_value = self.none_value

    @staticmethod
    def _parse_date_fmt():
        fmt = get_format('DATE_FORMAT')
        escaped = False
        for char in fmt:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char in 'Yy':
                yield 'year'
            elif char in 'bEFMmNn':
                yield 'month'
            elif char in 'dj':
                yield 'day'

    def render(self, name, value, attrs=None):
        try:
            year_val, month_val, day_val = value.year, value.month, value.day
        except AttributeError:
            year_val = month_val = day_val = None
            if isinstance(value, six.string_types):
                if settings.USE_L10N:
                    try:
                        input_format = get_format('DATE_INPUT_FORMATS')[0]
                        v = datetime.datetime.strptime(force_str(value), input_format)
                        year_val, month_val, day_val = v.year, v.month, v.day
                    except ValueError:
                        pass
                if year_val is None:
                    match = self.date_re.match(value)
                    if match:
                        year_val, month_val, day_val = [int(val) for val in match.groups()]
        html = {}
        choices = [(i, i) for i in self.years]
        html['year'] = self.create_select(name, self.year_field, value, year_val, choices, self.year_none_value)
        choices = list(self.months.items())
        html['month'] = self.create_select(name, self.month_field, value, month_val, choices, self.month_none_value)
        choices = [(i, i) for i in range(1, 32)]
        html['day'] = self.create_select(name, self.day_field, value, day_val, choices, self.day_none_value)

        output = []
        for field in self._parse_date_fmt():
            output.append(html[field])
        return mark_safe('\n'.join(output))

    def id_for_label(self, id_):
        for first_select in self._parse_date_fmt():
            return '%s_%s' % (id_, first_select)
        else:
            return '%s_month' % id_

    def value_from_datadict(self, data, files, name):
        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        d = data.get(self.day_field % name)
        if y == m == d == "0":
            return None
        if y and m and d:
            if settings.USE_L10N:
                input_format = get_format('DATE_INPUT_FORMATS')[0]
                try:
                    date_value = datetime.date(int(y), int(m), int(d))
                except ValueError:
                    return '%s-%s-%s' % (y, m, d)
                else:
                    date_value = datetime_safe.new_date(date_value)
                    return date_value.strftime(input_format)
            else:
                return '%s-%s-%s' % (y, m, d)
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return not any(
            ('{}_{}'.format(name, interval) in data)
            for interval in ('year', 'month', 'day')
        )

    def create_select(self, name, field, value, val, choices, none_value):
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name
        if not self.is_required:
            choices.insert(0, none_value)
        local_attrs = self.build_attrs(id=field % id_)
        s = self.select_widget(choices=choices)
        select_html = s.render(field % name, val, local_attrs)
        return select_html
