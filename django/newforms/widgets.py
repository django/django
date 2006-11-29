"""
HTML Widget classes
"""

__all__ = (
    'Widget', 'TextInput', 'PasswordInput', 'HiddenInput', 'FileInput',
    'Textarea', 'CheckboxInput',
    'Select', 'SelectMultiple', 'RadioSelect', 'CheckboxSelectMultiple',
)

from util import smart_unicode
from django.utils.html import escape
from itertools import chain

try:
    set # Only available in Python 2.4+
except NameError:
    from sets import Set as set # Python 2.3 fallback

# Converts a dictionary to a single string with key="value", XML-style with
# a leading space. Assumes keys do not need to be XML-escaped.
flatatt = lambda attrs: u''.join([u' %s="%s"' % (k, escape(v)) for k, v in attrs.items()])

class Widget(object):
    requires_data_list = False # Determines whether render()'s 'value' argument should be a list.
    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    def render(self, name, value):
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

class FileInput(Input):
    input_type = 'file'

class Textarea(Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        value = smart_unicode(value)
        final_attrs = self.build_attrs(attrs, name=name)
        return u'<textarea%s>%s</textarea>' % (flatatt(final_attrs), escape(value))

class CheckboxInput(Widget):
    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='checkbox', name=name)
        if value: final_attrs['checked'] = 'checked'
        return u'<input%s />' % flatatt(final_attrs)

class Select(Widget):
    def __init__(self, attrs=None, choices=()):
        # choices can be any iterable
        self.attrs = attrs or {}
        self.choices = choices

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

class SelectMultiple(Widget):
    requires_data_list = True
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

class RadioInput(object):
    "An object used by RadioFieldRenderer that represents a single <input type='radio'>."
    def __init__(self, name, value, attrs, choice, index):
        self.name, self.value = name, value
        self.attrs = attrs
        self.choice_value, self.choice_label = choice
        self.index = index

    def __str__(self):
        return u'<label>%s %s</label>' % (self.tag(), self.choice_label)

    def is_checked(self):
        return self.value == smart_unicode(self.choice_value)

    def tag(self):
        if self.attrs.has_key('id'):
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='radio', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return u'<input%s />' % flatatt(final_attrs)

class RadioFieldRenderer(object):
    "An object used by RadioSelect to enable customization of radio widgets."
    def __init__(self, name, value, attrs, choices):
        self.name, self.value, self.attrs = name, value, attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield RadioInput(self.name, self.value, self.attrs.copy(), choice, i)

    def __str__(self):
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
        cb = CheckboxInput(final_attrs)
        for option_value, option_label in chain(self.choices, choices):
            option_value = smart_unicode(option_value)
            field_name = name + option_value
            rendered_cb = cb.render(field_name, (option_value in str_values))
            output.append(u'<li><label>%s %s</label></li>' % (rendered_cb, escape(smart_unicode(option_label))))
        output.append(u'</ul>')
        return u'\n'.join(output)

    def value_from_datadict(self, data, name):
        data_list = [k for k, v in self.choices if data.get(name + k)]
        return data_list or None

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
    id_for_label = classmethod(id_for_label)
