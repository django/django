"""
Field classes
"""

from util import ValidationError, DEFAULT_ENCODING
from widgets import TextInput, CheckboxInput
import datetime
import re
import time

__all__ = (
    'Field', 'CharField', 'IntegerField',
    'DEFAULT_DATE_INPUT_FORMATS', 'DateField',
    'DEFAULT_DATETIME_INPUT_FORMATS', 'DateTimeField',
    'RegexField', 'EmailField', 'URLField', 'BooleanField',
)

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

class Field(object):
    widget = TextInput # Default widget to use when rendering this type of Field.

    def __init__(self, required=True, widget=None):
        self.required = required
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()
        self.widget = widget

    def to_python(self, value):
        """
        Validates the given value and returns its "normalized" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        if self.required and value in EMPTY_VALUES:
            raise ValidationError(u'This field is required.')
        return value

class CharField(Field):
    def __init__(self, max_length=None, min_length=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.max_length, self.min_length = max_length, min_length

    def to_python(self, value):
        "Validates max_length and min_length. Returns a Unicode object."
        Field.to_python(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(u'Ensure this value has at most %d characters.' % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(u'Ensure this value has at least %d characters.' % self.min_length)
        return value

class IntegerField(Field):
    def to_python(self, value):
        """
        Validates that int() can be called on the input. Returns the result
        of int().
        """
        super(IntegerField, self).to_python(value)
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(u'Enter a whole number.')

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

class DateField(Field):
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATE_INPUT_FORMATS

    def to_python(self, value):
        """
        Validates that the input can be converted to a date. Returns a Python
        datetime.date object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in self.input_formats:
            try:
                return datetime.date(*time.strptime(value, format)[:3])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date.')

DEFAULT_DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)

class DateTimeField(Field):
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATETIME_INPUT_FORMATS

    def to_python(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in self.input_formats:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date/time.')

class RegexField(Field):
    def __init__(self, regex, error_message=None, required=True, widget=None):
        """
        regex can be either a string or a compiled regular expression object.
        error_message is an optional error message to use, if
        'Enter a valid value' is too generic for you.
        """
        Field.__init__(self, required, widget)
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.error_message = error_message or u'Enter a valid value.'

    def to_python(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if not self.regex.search(value):
            raise ValidationError(self.error_message)
        return value

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

class EmailField(RegexField):
    def __init__(self, required=True, widget=None):
        RegexField.__init__(self, email_re, u'Enter a valid e-mail address.', required, widget)

url_re = re.compile(
    r'^https?://' # http:// or https://
    r'(?:[A-Z0-9-]+\.)+[A-Z]{2,6}' # domain
    r'(?::\d+)?' # optional port
    r'(?:/?|/\S+)$', re.IGNORECASE)

class URLField(RegexField):
    def __init__(self, required=True, verify_exists=False, widget=None):
        RegexField.__init__(self, url_re, u'Enter a valid URL.', required, widget)
        self.verify_exists = verify_exists

    def to_python(self, value):
        value = RegexField.to_python(self, value)
        if self.verify_exists:
            import urllib2
            try:
                u = urllib2.urlopen(value)
            except ValueError:
                raise ValidationError(u'Enter a valid URL.')
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise ValidationError(u'This URL appears to be a broken link.')
        return value

class BooleanField(Field):
    widget = CheckboxInput

    def to_python(self, value):
        "Returns a Python boolean object."
        Field.to_python(self, value)
        return bool(value)
