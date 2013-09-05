"""
HTML Widget classes
"""

from __future__ import absolute_import, unicode_literals

import copy
from itertools import chain
import warnings

from django.conf import settings
from django.forms.util import flatatt, to_current_timezone
from django.utils.datastructures import MultiValueDict, MergeDict
from django.utils.html import conditional_escape, format_html
from django.utils.translation import ugettext_lazy
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.safestring import mark_safe
from django.utils import datetime_safe, formats, six
from django.utils.six.moves.urllib.parse import urljoin

__all__ = (
    'Media', 'MediaDefiningClass', 'Widget', 'TextInput',
    'EmailInput', 'URLInput', 'NumberInput', 'PasswordInput',
    'HiddenInput', 'MultipleHiddenInput', 'ClearableFileInput',
    'FileInput', 'DateInput', 'DateTimeInput', 'TimeInput', 'Textarea', 'CheckboxInput',
    'Select', 'NullBooleanSelect', 'SelectMultiple', 'RadioSelect',
    'CheckboxSelectMultiple', 'MultiWidget',
    'SplitDateTimeWidget',
)

MEDIA_TYPES = ('css','js')

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
            getattr(self, 'add_' + name)(media_attrs.get(name, None))

        # Any leftover attributes must be invalid.
        # if media_attrs != {}:
        #     raise TypeError("'class Media' has invalid attribute(s): %s" % ','.join(media_attrs.keys()))

    def __str__(self):
        return self.render()

    def render(self):
        return mark_safe('\n'.join(chain(*[getattr(self, 'render_' + name)() for name in MEDIA_TYPES])))

    def render_js(self):
        return [format_html('<script type="text/javascript" src="{0}"></script>', self.absolute_path(path)) for path in self._js]

    def render_css(self):
        # To keep rendering order consistent, we can't just iterate over items().
        # We need to sort the keys, and iterate over the sorted list.
        media = sorted(self._css.keys())
        return chain(*[
                [format_html('<link href="{0}" type="text/css" media="{1}" rel="stylesheet" />', self.absolute_path(path), medium)
                    for path in self._css[medium]]
                for medium in media])

    def absolute_path(self, path, prefix=None):
        if path.startswith(('http://', 'https://', '/')):
            return path
        if prefix is None:
            if settings.STATIC_URL is None:
                 # backwards compatibility
                prefix = settings.MEDIA_URL
            else:
                prefix = settings.STATIC_URL
        return urljoin(prefix, path)

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
                if extend == True:
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
    "Metaclass for classes that can have media definitions"
    def __new__(cls, name, bases, attrs):
        new_class = super(MediaDefiningClass, cls).__new__(cls, name, bases,
                                                           attrs)
        if 'media' not in attrs:
            new_class.media = media_property(new_class)
        return new_class

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

class Widget(six.with_metaclass(MediaDefiningClass)):
    is_hidden = False          # Determines whether this corresponds to an <input type="hidden">.
    needs_multipart_form = False # Determines does this widget need multipart form
    is_localized = False
    is_required = False

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
        raise NotImplementedError

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
        return data.get(name, None)

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

class Input(Widget):
    """
    Base class for all <input> widgets (except type='checkbox' and
    type='radio', which are special).
    """
    input_type = None # Subclasses must define this.

    def _format_value(self, value):
        if self.is_localized:
            return formats.localize_input(value)
        return value

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<input{0} />', flatatt(final_attrs))


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
        if not self.render_value: value=None
        return super(PasswordInput, self).render(name, value, attrs)

class HiddenInput(Input):
    input_type = 'hidden'
    is_hidden = True

class MultipleHiddenInput(HiddenInput):
    """
    A widget that handles <input type="hidden"> for fields that have a list
    of values.
    """
    def __init__(self, attrs=None, choices=()):
        super(MultipleHiddenInput, self).__init__(attrs)
        # choices can be any iterable
        self.choices = choices

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        id_ = final_attrs.get('id', None)
        inputs = []
        for i, v in enumerate(value):
            input_attrs = dict(value=force_text(v), **final_attrs)
            if id_:
                # An ID attribute was given. Add a numeric index as a suffix
                # so that the inputs don't all have the same ID attribute.
                input_attrs['id'] = '%s_%s' % (id_, i)
            inputs.append(format_html('<input{0} />', flatatt(input_attrs)))
        return mark_safe('\n'.join(inputs))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)

class FileInput(Input):
    input_type = 'file'
    needs_multipart_form = True

    def render(self, name, value, attrs=None):
        return super(FileInput, self).render(name, None, attrs=attrs)

    def value_from_datadict(self, data, files, name):
        "File widgets take data from FILES, not POST"
        return files.get(name, None)


FILE_INPUT_CONTRADICTION = object()

class ClearableFileInput(FileInput):
    initial_text = ugettext_lazy('Currently')
    input_text = ugettext_lazy('Change')
    clear_checkbox_label = ugettext_lazy('Clear')

    template_with_initial = '%(initial_text)s: %(initial)s %(clear_template)s<br />%(input_text)s: %(input)s'

    template_with_clear = '%(clear)s <label for="%(clear_checkbox_id)s">%(clear_checkbox_label)s</label>'

    url_markup_template = '<a href="{0}">{1}</a>'

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

    def render(self, name, value, attrs=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'clear_template': '',
            'clear_checkbox_label': self.clear_checkbox_label,
        }
        template = '%(input)s'
        substitutions['input'] = super(ClearableFileInput, self).render(name, value, attrs)

        if value and hasattr(value, "url"):
            template = self.template_with_initial
            substitutions['initial'] = format_html(self.url_markup_template,
                                                   value.url,
                                                   force_text(value))
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

class Textarea(Widget):
    def __init__(self, attrs=None):
        # The 'rows' and 'cols' attributes are required for HTML correctness.
        default_attrs = {'cols': '40', 'rows': '10'}
        if attrs:
            default_attrs.update(attrs)
        super(Textarea, self).__init__(default_attrs)

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{0}>\r\n{1}</textarea>',
                           flatatt(final_attrs),
                           force_text(value))


class DateInput(TextInput):
    def __init__(self, attrs=None, format=None):
        super(DateInput, self).__init__(attrs)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('DATE_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            value = datetime_safe.new_date(value)
            return value.strftime(self.format)
        return value


class DateTimeInput(TextInput):
    def __init__(self, attrs=None, format=None):
        super(DateTimeInput, self).__init__(attrs)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('DATETIME_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            value = datetime_safe.new_datetime(value)
            return value.strftime(self.format)
        return value


class TimeInput(TextInput):
    def __init__(self, attrs=None, format=None):
        super(TimeInput, self).__init__(attrs)
        if format:
            self.format = format
            self.manual_format = True
        else:
            self.format = formats.get_format('TIME_INPUT_FORMATS')[0]
            self.manual_format = False

    def _format_value(self, value):
        if self.is_localized and not self.manual_format:
            return formats.localize_input(value)
        elif hasattr(value, 'strftime'):
            return value.strftime(self.format)
        return value


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
        return format_html('<input{0} />', flatatt(final_attrs))

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


class Select(Widget):
    allow_multiple_selected = False

    def __init__(self, attrs=None, choices=()):
        super(Select, self).__init__(attrs)
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = list(choices)

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html('<select{0}>', flatatt(final_attrs))]
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return format_html('<option value="{0}"{1}>{2}</option>',
                           option_value,
                           selected_html,
                           force_text(option_label))

    def render_options(self, choices, selected_choices):
        # Normalize to strings.
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                output.append(format_html('<optgroup label="{0}">', force_text(option_value)))
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
        choices = (('1', ugettext_lazy('Unknown')),
                   ('2', ugettext_lazy('Yes')),
                   ('3', ugettext_lazy('No')))
        super(NullBooleanSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {True: '2', False: '3', '2': '2', '3': '3'}[value]
        except KeyError:
            value = '1'
        return super(NullBooleanSelect, self).render(name, value, attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        return {'2': True,
                True: True,
                'True': True,
                '3': False,
                'False': False,
                False: False}.get(value, None)


class SelectMultiple(Select):
    allow_multiple_selected = True

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html('<select multiple="multiple"{0}>', flatatt(final_attrs))]
        options = self.render_options(choices, value)
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)


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

    def __str__(self):
        return self.render()

    def render(self, name=None, value=None, attrs=None, choices=()):
        name = name or self.name
        value = value or self.value
        attrs = attrs or self.attrs
        if 'id' in self.attrs:
            label_for = format_html(' for="{0}_{1}"', self.attrs['id'], self.index)
        else:
            label_for = ''
        return format_html('<label{0}>{1} {2}</label>', label_for, self.tag(), self.choice_label)

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type=self.input_type, name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return format_html('<input{0} />', flatatt(final_attrs))


class RadioChoiceInput(ChoiceInput):
    input_type = 'radio'

    def __init__(self, *args, **kwargs):
        super(RadioChoiceInput, self).__init__(*args, **kwargs)
        self.value = force_text(self.value)


class RadioInput(RadioChoiceInput):
    def __init__(self, *args, **kwargs):
        msg = "RadioInput has been deprecated. Use RadioChoiceInput instead."
        warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        super(RadioInput, self).__init__(*args, **kwargs)


class CheckboxChoiceInput(ChoiceInput):
    input_type = 'checkbox'

    def __init__(self, *args, **kwargs):
        super(CheckboxChoiceInput, self).__init__(*args, **kwargs)
        self.value = set(force_text(v) for v in self.value)

    def is_checked(self):
        return self.choice_value in self.value


@python_2_unicode_compatible
class ChoiceFieldRenderer(object):
    """
    An object used by RadioSelect to enable customization of radio widgets.
    """

    choice_input_class = None

    def __init__(self, name, value, attrs, choices):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield self.choice_input_class(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx] # Let the IndexError propogate
        return self.choice_input_class(self.name, self.value, self.attrs.copy(), choice, idx)

    def __str__(self):
        return self.render()

    def render(self):
        """
        Outputs a <ul> for this set of choice fields.
        If an id was given to the field, it is applied to the <ul> (each
        item in the list will get an id of `$id_$i`).
        """
        id_ = self.attrs.get('id', None)
        start_tag = format_html('<ul id="{0}">', id_) if id_ else '<ul>'
        output = [start_tag]
        for widget in self:
            output.append(format_html('<li>{0}</li>', force_text(widget)))
        output.append('</ul>')
        return mark_safe('\n'.join(output))


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

    def subwidgets(self, name, value, attrs=None, choices=()):
        for widget in self.get_renderer(name, value, attrs, choices):
            yield widget

    def get_renderer(self, name, value, attrs=None, choices=()):
        """Returns an instance of the renderer."""
        if value is None:
            value = self._empty_value
        final_attrs = self.build_attrs(attrs)
        choices = list(chain(self.choices, choices))
        return self.renderer(name, value, final_attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        return self.get_renderer(name, value, attrs, choices).render()

    def id_for_label(self, id_):
        # Widgets using this RendererMixin are made of a collection of
        # subwidgets, each with their own <label>, and distinct ID.
        # The IDs are made distinct by y "_X" suffix, where X is the zero-based
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
        id_ = final_attrs.get('id', None)
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

    def __init__(self, attrs=None, date_format=None, time_format=None):
        widgets = (DateInput(attrs=attrs, format=date_format),
                   TimeInput(attrs=attrs, format=time_format))
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
    is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(SplitHiddenDateTimeWidget, self).__init__(attrs, date_format, time_format)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True
