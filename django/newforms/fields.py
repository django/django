"""
Field classes
"""

from django.utils.translation import gettext
from util import ValidationError, smart_unicode
from widgets import TextInput, PasswordInput, HiddenInput, MultipleHiddenInput, CheckboxInput, Select, SelectMultiple
import datetime
import re
import time

__all__ = (
    'Field', 'CharField', 'IntegerField',
    'DEFAULT_DATE_INPUT_FORMATS', 'DateField',
    'DEFAULT_TIME_INPUT_FORMATS', 'TimeField',
    'DEFAULT_DATETIME_INPUT_FORMATS', 'DateTimeField',
    'RegexField', 'EmailField', 'URLField', 'BooleanField',
    'ChoiceField', 'MultipleChoiceField',
    'ComboField',
)

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

try:
    set # Only available in Python 2.4+
except NameError:
    from sets import Set as set # Python 2.3 fallback

class Field(object):
    widget = TextInput # Default widget to use when rendering this type of Field.
    hidden_widget = HiddenInput # Default widget to use when rendering this as "hidden".

    # Tracks each time a Field instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self, required=True, widget=None, label=None, initial=None):
        # required -- Boolean that specifies whether the field is required.
        #             True by default.
        # widget -- A Widget class, or instance of a Widget class, that should be
        #         used for this Field when displaying it. Each Field has a default
        #         Widget that it'll use if you don't specify this. In most cases,
        #         the default widget is TextInput.
        # label -- A verbose name for this field, for use in displaying this field in
        #         a form. By default, Django will use a "pretty" version of the form
        #         field name, if the Field is part of a Form.
        # initial -- A value to use in this Field's initial display. This value is
        #            *not* used as a fallback if data isn't given.
        if label is not None:
            label = smart_unicode(label)
        self.required, self.label, self.initial = required, label, initial
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()

        # Hook into self.widget_attrs() for any Field-specific HTML attributes.
        extra_attrs = self.widget_attrs(widget)
        if extra_attrs:
            widget.attrs.update(extra_attrs)

        self.widget = widget

        # Increase the creation counter, and save our local copy.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def clean(self, value):
        """
        Validates the given value and returns its "cleaned" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        if self.required and value in EMPTY_VALUES:
            raise ValidationError(gettext(u'This field is required.'))
        return value

    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        return {}

class CharField(Field):
    def __init__(self, max_length=None, min_length=None, required=True, widget=None, label=None, initial=None):
        self.max_length, self.min_length = max_length, min_length
        Field.__init__(self, required, widget, label, initial)

    def clean(self, value):
        "Validates max_length and min_length. Returns a Unicode object."
        Field.clean(self, value)
        if value in EMPTY_VALUES:
            value = u''
            if not self.required:
                return value
        value = smart_unicode(value)
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(gettext(u'Ensure this value has at most %d characters.') % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(gettext(u'Ensure this value has at least %d characters.') % self.min_length)
        return value

    def widget_attrs(self, widget):
        if self.max_length is not None and isinstance(widget, (TextInput, PasswordInput)):
            return {'maxlength': str(self.max_length)}

class IntegerField(Field):
    def __init__(self, max_value=None, min_value=None, required=True, widget=None, label=None, initial=None):
        self.max_value, self.min_value = max_value, min_value
        Field.__init__(self, required, widget, label, initial)

    def clean(self, value):
        """
        Validates that int() can be called on the input. Returns the result
        of int(). Returns None for empty values.
        """
        super(IntegerField, self).clean(value)
        if not self.required and value in EMPTY_VALUES:
            return None
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(gettext(u'Enter a whole number.'))
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(gettext(u'Ensure this value is less than or equal to %s.') % self.max_value)
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(gettext(u'Ensure this value is greater than or equal to %s.') % self.min_value)
        return value

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

class DateField(Field):
    def __init__(self, input_formats=None, required=True, widget=None, label=None, initial=None):
        Field.__init__(self, required, widget, label, initial)
        self.input_formats = input_formats or DEFAULT_DATE_INPUT_FORMATS

    def clean(self, value):
        """
        Validates that the input can be converted to a date. Returns a Python
        datetime.date object.
        """
        Field.clean(self, value)
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
        raise ValidationError(gettext(u'Enter a valid date.'))

DEFAULT_TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)

class TimeField(Field):
    def __init__(self, input_formats=None, required=True, widget=None, label=None, initial=None):
        Field.__init__(self, required, widget, label, initial)
        self.input_formats = input_formats or DEFAULT_TIME_INPUT_FORMATS

    def clean(self, value):
        """
        Validates that the input can be converted to a time. Returns a Python
        datetime.time object.
        """
        Field.clean(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.time):
            return value
        for format in self.input_formats:
            try:
                return datetime.time(*time.strptime(value, format)[3:6])
            except ValueError:
                continue
        raise ValidationError(gettext(u'Enter a valid time.'))

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
    def __init__(self, input_formats=None, required=True, widget=None, label=None, initial=None):
        Field.__init__(self, required, widget, label, initial)
        self.input_formats = input_formats or DEFAULT_DATETIME_INPUT_FORMATS

    def clean(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        Field.clean(self, value)
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
        raise ValidationError(gettext(u'Enter a valid date/time.'))

class RegexField(Field):
    def __init__(self, regex, max_length=None, min_length=None, error_message=None,
            required=True, widget=None, label=None, initial=None):
        """
        regex can be either a string or a compiled regular expression object.
        error_message is an optional error message to use, if
        'Enter a valid value' is too generic for you.
        """
        Field.__init__(self, required, widget, label, initial)
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.max_length, self.min_length = max_length, min_length
        self.error_message = error_message or gettext(u'Enter a valid value.')

    def clean(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        Field.clean(self, value)
        if value in EMPTY_VALUES: value = u''
        value = smart_unicode(value)
        if not self.required and value == u'':
            return value
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(gettext(u'Ensure this value has at most %d characters.') % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(gettext(u'Ensure this value has at least %d characters.') % self.min_length)
        if not self.regex.search(value):
            raise ValidationError(self.error_message)
        return value

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

class EmailField(RegexField):
    def __init__(self, max_length=None, min_length=None, required=True, widget=None, label=None, initial=None):
        RegexField.__init__(self, email_re, max_length, min_length, gettext(u'Enter a valid e-mail address.'), required, widget, label, initial)

url_re = re.compile(
    r'^https?://' # http:// or https://
    r'(?:[A-Z0-9-]+\.)+[A-Z]{2,6}' # domain
    r'(?::\d+)?' # optional port
    r'(?:/?|/\S+)$', re.IGNORECASE)

try:
    from django.conf import settings
    URL_VALIDATOR_USER_AGENT = settings.URL_VALIDATOR_USER_AGENT
except ImportError:
    # It's OK if Django settings aren't configured.
    URL_VALIDATOR_USER_AGENT = 'Django (http://www.djangoproject.com/)'

class URLField(RegexField):
    def __init__(self, max_length=None, min_length=None, required=True, verify_exists=False, widget=None, label=None,
            initial=None, validator_user_agent=URL_VALIDATOR_USER_AGENT):
        RegexField.__init__(self, url_re, max_length, min_length, gettext(u'Enter a valid URL.'), required, widget, label, initial)
        self.verify_exists = verify_exists
        self.user_agent = validator_user_agent

    def clean(self, value):
        value = RegexField.clean(self, value)
        if not self.required and value == u'':
            return value
        if self.verify_exists:
            import urllib2
            from django.conf import settings
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            try:
                req = urllib2.Request(value, None, headers)
                u = urllib2.urlopen(req)
            except ValueError:
                raise ValidationError(gettext(u'Enter a valid URL.'))
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise ValidationError(gettext(u'This URL appears to be a broken link.'))
        return value

class BooleanField(Field):
    widget = CheckboxInput

    def clean(self, value):
        "Returns a Python boolean object."
        Field.clean(self, value)
        return bool(value)

class ChoiceField(Field):
    def __init__(self, choices=(), required=True, widget=Select, label=None, initial=None):
        if isinstance(widget, type):
            widget = widget(choices=choices)
        Field.__init__(self, required, widget, label, initial)
        self.choices = choices

    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
        value = Field.clean(self, value)
        if value in EMPTY_VALUES: value = u''
        value = smart_unicode(value)
        if not self.required and value == u'':
            return value
        valid_values = set([str(k) for k, v in self.choices])
        if value not in valid_values:
            raise ValidationError(gettext(u'Select a valid choice. %s is not one of the available choices.') % value)
        return value

class MultipleChoiceField(ChoiceField):
    hidden_widget = MultipleHiddenInput

    def __init__(self, choices=(), required=True, widget=SelectMultiple, label=None, initial=None):
        ChoiceField.__init__(self, choices, required, widget, label, initial)

    def clean(self, value):
        """
        Validates that the input is a list or tuple.
        """
        if self.required and not value:
            raise ValidationError(gettext(u'This field is required.'))
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValidationError(gettext(u'Enter a list of values.'))
        new_value = []
        for val in value:
            val = smart_unicode(val)
            new_value.append(val)
        # Validate that each value in the value list is in self.choices.
        valid_values = set([smart_unicode(k) for k, v in self.choices])
        for val in new_value:
            if val not in valid_values:
                raise ValidationError(gettext(u'Select a valid choice. %s is not one of the available choices.') % val)
        return new_value

class ComboField(Field):
    def __init__(self, fields=(), required=True, widget=None, label=None, initial=None):
        Field.__init__(self, required, widget, label, initial)
        # Set 'required' to False on the individual fields, because the
        # required validation will be handled by ComboField, not by those
        # individual fields.
        for f in fields:
            f.required = False
        self.fields = fields

    def clean(self, value):
        """
        Validates the given value against all of self.fields, which is a
        list of Field instances.
        """
        Field.clean(self, value)
        for field in self.fields:
            value = field.clean(value)
        return value
