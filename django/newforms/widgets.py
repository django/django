"""
HTML Widget classes
"""

__all__ = ('Widget', 'TextInput', 'Textarea', 'CheckboxInput')

from django.utils.html import escape

# Converts a dictionary to a single string with key="value", XML-style.
# Assumes keys do not need to be XML-escaped.
flatatt = lambda attrs: ' '.join(['%s="%s"' % (k, escape(v)) for k, v in attrs.items()])

class Widget(object):
    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    def render(self, name, value):
        raise NotImplementedError

class TextInput(Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = dict(self.attrs, type='text', name=name)
        if attrs:
            final_attrs.update(attrs)
        if value != '': final_attrs['value'] = value # Only add the 'value' attribute if a value is non-empty.
        return u'<input %s />' % flatatt(final_attrs)

class Textarea(Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = dict(self.attrs, name=name)
        if attrs:
            final_attrs.update(attrs)
        return u'<textarea %s>%s</textarea>' % (flatatt(final_attrs), escape(value))

class CheckboxInput(Widget):
    def render(self, name, value, attrs=None):
        final_attrs = dict(self.attrs, type='checkbox', name=name)
        if attrs:
            final_attrs.update(attrs)
        if value: final_attrs['checked'] = 'checked'
        return u'<input %s />' % flatatt(final_attrs)
