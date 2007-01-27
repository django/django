"""
HTML Widget classes
"""

__all__ = (
    'Widget', 'TextInput', 'PasswordInput', 'HiddenInput', 'MultipleHiddenInput',
    'FileInput', 'Textarea', 'CheckboxInput',
    'Select', 'NullBooleanSelect', 'SelectMultiple', 'RadioSelect', 'CheckboxSelectMultiple',
    'MultiWidget', 'SplitDateTimeWidget',
)

from util import flatatt, StrAndUnicode, smart_unicode
from django.utils.datastructures import MultiValueDict
from django.utils.html import escape
from django.utils.translation import gettext
from itertools import chain

try:
    set # Only available in Python 2.4+
except NameError:
    from sets import Set as set # Python 2.3 fallback

class Widget(object):
    is_hidden = False          # Determines whether this corresponds to an <input type="hidden">.

    def __init__(self, attrs=None):
        self.attrs = attrs or {}

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

    def value_from_datadict(self, data, name):
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
    id_for_label = classmethod(id_for_label)

class Input(Widget):
    """
    Base class for all <input> widgets (except type='checkbox' and
    type='radio', which are special).
    """
    input_type = None # Subclasses must define this.

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '': final_attrs['value'] = smart_unicode(value) # Only add the 'value' attribute if a value is non-empty.
        return u'<input%s />' % flatatt(final_attrs)

class TextInput(Input):
    input_type = 'text'

class PasswordInput(Input):
    input_type = 'password'

class HiddenInput(Input):
    input_type = 'hidden'
    is_hidden = True

class MultipleHiddenInput(HiddenInput):
    """
    A widget that handles <input type="hidden"> for fields that have a list
    of values.
    """
    def __init__(self, attrs=None, choices=()):
        # choices can be any iterable
        self.attrs = attrs or {}
        self.choices = choices

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        return u'\n'.join([(u'<input%s />' % flatatt(dict(value=smart_unicode(v), **final_attrs))) for v in value])

    def value_from_datadict(self, data, name):
        if isinstance(data, MultiValueDict):
            return data.getlist(name)
        return data.get(name, None)

class FileInput(Input):
    input_type = 'file'

class Textarea(Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        value = smart_unicode(value)
        final_attrs = self.build_attrs(attrs, name=name)
        return u'<textarea%s>%s</textarea>' % (flatatt(final_attrs), escape(value))

class CheckboxInput(Widget):
    def __init__(self, attrs=None, check_test=bool):
        # check_test is a callable that takes a value and returns True
        # if the checkbox should be checked for that value.
        self.attrs = attrs or {}
        self.check_test = check_test

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='checkbox', name=name)
        try:
            result = self.check_test(value)
        except: # Silently catch exceptions
            result = False
        if result:
            final_attrs['checked'] = 'checked'
        if value not in ('', True, False, None):
            final_attrs['value'] = smart_unicode(value) # Only add the 'value' attribute if a value is non-empty.
        return u'<input%s />' % flatatt(final_attrs)

class Select(Widget):
    def __init__(self, attrs=None, choices=()):
        self.attrs = attrs or {}
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = list(choices)

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<select%s>' % flatatt(final_attrs)]
        str_value = smart_unicode(value) # Normalize to string.
        for option_value, option_label in chain(self.choices, choices):
            option_value = smart_unicode(option_value)
            selected_html = (option_value == str_value) and u' selected="selected"' or ''
            output.append(u'<option value="%s"%s>%s</option>' % (escape(option_value), selected_html, escape(smart_unicode(option_label))))
        output.append(u'</select>')
        return u'\n'.join(output)

class NullBooleanSelect(Select):
    """
    A Select Widget intended to be used with NullBooleanField.
    """
    def __init__(self, attrs=None):
        choices = ((u'1', gettext('Unknown')), (u'2', gettext('Yes')), (u'3', gettext('No')))
        super(NullBooleanSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u'1'
        return super(NullBooleanSelect, self).render(name, value, attrs, choices)

    def value_from_datadict(self, data, name):
        value = data.get(name, None)
        return {u'2': True, u'3': False, True: True, False: False}.get(value, None)

class SelectMultiple(Widget):
    def __init__(self, attrs=None, choices=()):
        # choices can be any iterable
        self.attrs = attrs or {}
        self.choices = choices

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<select multiple="multiple"%s>' % flatatt(final_attrs)]
        str_values = set([smart_unicode(v) for v in value]) # Normalize to strings.
        for option_value, option_label in chain(self.choices, choices):
            option_value = smart_unicode(option_value)
            selected_html = (option_value in str_values) and ' selected="selected"' or ''
            output.append(u'<option value="%s"%s>%s</option>' % (escape(option_value), selected_html, escape(smart_unicode(option_label))))
        output.append(u'</select>')
        return u'\n'.join(output)

    def value_from_datadict(self, data, name):
        if isinstance(data, MultiValueDict):
            return data.getlist(name)
        return data.get(name, None)

class RadioInput(StrAndUnicode):
    "An object used by RadioFieldRenderer that represents a single <input type='radio'>."
    def __init__(self, name, value, attrs, choice, index):
        self.name, self.value = name, value
        self.attrs = attrs
        self.choice_value = smart_unicode(choice[0])
        self.choice_label = smart_unicode(choice[1])
        self.index = index

    def __unicode__(self):
        return u'<label>%s %s</label>' % (self.tag(), self.choice_label)

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self):
        if self.attrs.has_key('id'):
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='radio', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return u'<input%s />' % flatatt(final_attrs)

class RadioFieldRenderer(StrAndUnicode):
    "An object used by RadioSelect to enable customization of radio widgets."
    def __init__(self, name, value, attrs, choices):
        self.name, self.value, self.attrs = name, value, attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield RadioInput(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx] # Let the IndexError propogate
        return RadioInput(self.name, self.value, self.attrs.copy(), choice, idx)

    def __unicode__(self):
        "Outputs a <ul> for this set of radio fields."
        return u'<ul>\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>' % w for w in self])

class RadioSelect(Select):
    def render(self, name, value, attrs=None, choices=()):
        "Returns a RadioFieldRenderer instance rather than a Unicode string."
        if value is None: value = ''
        str_value = smart_unicode(value) # Normalize to string.
        attrs = attrs or {}
        return RadioFieldRenderer(name, str_value, attrs, list(chain(self.choices, choices)))

    def id_for_label(self, id_):
        # RadioSelect is represented by multiple <input type="radio"> fields,
        # each of which has a distinct ID. The IDs are made distinct by a "_X"
        # suffix, where X is the zero-based index of the radio field. Thus,
        # the label for a RadioSelect should reference the first one ('_0').
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)

class CheckboxSelectMultiple(SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<ul>']
        str_values = set([smart_unicode(v) for v in value]) # Normalize to strings.
        cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
        for option_value, option_label in chain(self.choices, choices):
            option_value = smart_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            output.append(u'<li><label>%s %s</label></li>' % (rendered_cb, escape(smart_unicode(option_label))))
        output.append(u'</ul>')
        return u'\n'.join(output)

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)

class MultiWidget(Widget):
    """
    A widget that is composed of multiple widgets.

    Its render() method takes a "decompressed" list of values, not a single
    value. Each value in this list is rendered in the corresponding widget --
    the first value is rendered in the first widget, the second value is
    rendered in the second widget, etc.

    Subclasses should implement decompress(), which specifies how a single
    value should be converted to a list of values. Subclasses should not
    have to implement clean().

    Subclasses may implement format_output(), which takes the list of rendered
    widgets and returns HTML that formats them any way you'd like.

    You'll probably want to use this with MultiValueField.
    """
    def __init__(self, widgets, attrs=None):
        self.widgets = [isinstance(w, type) and w() or w for w in widgets]
        super(MultiWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except KeyError:
                widget_value = None
            output.append(widget.render(name + '_%s' % i, widget_value, attrs))
        return self.format_output(output)

    def value_from_datadict(self, data, name):
        return [data.get(name + '_%s' % i) for i in range(len(self.widgets))]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def decompress(self, value):
        """
        Returns a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """
        raise NotImplementedError('Subclasses must implement this method.')

class SplitDateTimeWidget(MultiWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.
    """
    def __init__(self, attrs=None):
        widgets = (TextInput(attrs=attrs), TextInput(attrs=attrs))
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.date(), value.time()]
        return [None, None]
