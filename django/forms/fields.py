"""
Field classes.
"""

import datetime
import os
import re
import time
import urlparse
import warnings
from decimal import Decimal, DecimalException
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.exceptions import ValidationError
from django.core import validators
import django.utils.copycompat as copy
from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode, smart_str
from django.utils.functional import lazy

# Provide this import for backwards compatibility.
from django.core.validators import EMPTY_VALUES

from util import ErrorList
from widgets import TextInput, PasswordInput, HiddenInput, MultipleHiddenInput, \
        ClearableFileInput, CheckboxInput, Select, NullBooleanSelect, SelectMultiple, \
        DateInput, DateTimeInput, TimeInput, SplitDateTimeWidget, SplitHiddenDateTimeWidget, \
        FILE_INPUT_CONTRADICTION

__all__ = (
    'Field', 'CharField', 'IntegerField',
    'DEFAULT_DATE_INPUT_FORMATS', 'DateField',
    'DEFAULT_TIME_INPUT_FORMATS', 'TimeField',
    'DEFAULT_DATETIME_INPUT_FORMATS', 'DateTimeField', 'TimeField',
    'RegexField', 'EmailField', 'FileField', 'ImageField', 'URLField',
    'BooleanField', 'NullBooleanField', 'ChoiceField', 'MultipleChoiceField',
    'ComboField', 'MultiValueField', 'FloatField', 'DecimalField',
    'SplitDateTimeField', 'IPAddressField', 'FilePathField', 'SlugField',
    'TypedChoiceField'
)

def en_format(name):
    """
    Helper function to stay backward compatible.
    """
    from django.conf.locale.en import formats
    warnings.warn(
        "`django.forms.fields.DEFAULT_%s` is deprecated; use `django.utils.formats.get_format('%s')` instead." % (name, name),
        DeprecationWarning
    )
    return getattr(formats, name)

DEFAULT_DATE_INPUT_FORMATS = lazy(lambda: en_format('DATE_INPUT_FORMATS'), tuple, list)()
DEFAULT_TIME_INPUT_FORMATS = lazy(lambda: en_format('TIME_INPUT_FORMATS'), tuple, list)()
DEFAULT_DATETIME_INPUT_FORMATS = lazy(lambda: en_format('DATETIME_INPUT_FORMATS'), tuple, list)()

class Field(object):
    widget = TextInput # Default widget to use when rendering this type of Field.
    hidden_widget = HiddenInput # Default widget to use when rendering this as "hidden".
    default_validators = [] # Default set of validators
    default_error_messages = {
        'required': _(u'This field is required.'),
        'invalid': _(u'Enter a valid value.'),
    }

    # Tracks each time a Field instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self, required=True, widget=None, label=None, initial=None,
                 help_text=None, error_messages=None, show_hidden_initial=False,
                 validators=[], localize=False):
        # required -- Boolean that specifies whether the field is required.
        #             True by default.
        # widget -- A Widget class, or instance of a Widget class, that should
        #           be used for this Field when displaying it. Each Field has a
        #           default Widget that it'll use if you don't specify this. In
        #           most cases, the default widget is TextInput.
        # label -- A verbose name for this field, for use in displaying this
        #          field in a form. By default, Django will use a "pretty"
        #          version of the form field name, if the Field is part of a
        #          Form.
        # initial -- A value to use in this Field's initial display. This value
        #            is *not* used as a fallback if data isn't given.
        # help_text -- An optional string to use as "help text" for this Field.
        # error_messages -- An optional dictionary to override the default
        #                   messages that the field will raise.
        # show_hidden_initial -- Boolean that specifies if it is needed to render a
        #                        hidden widget with initial value after widget.
        # validators -- List of addtional validators to use
        # localize -- Boolean that specifies if the field should be localized.
        if label is not None:
            label = smart_unicode(label)
        self.required, self.label, self.initial = required, label, initial
        self.show_hidden_initial = show_hidden_initial
        if help_text is None:
            self.help_text = u''
        else:
            self.help_text = smart_unicode(help_text)
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()

        # Trigger the localization machinery if needed.
        self.localize = localize
        if self.localize:
            widget.is_localized = True

        # Let the widget know whether it should display as required.
        widget.is_required = self.required

        # Hook into self.widget_attrs() for any Field-specific HTML attributes.
        extra_attrs = self.widget_attrs(widget)
        if extra_attrs:
            widget.attrs.update(extra_attrs)

        self.widget = widget

        # Increase the creation counter, and save our local copy.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

        self.validators = self.default_validators + validators

    def prepare_value(self, value):
        return value

    def to_python(self, value):
        return value

    def validate(self, value):
        if value in validators.EMPTY_VALUES and self.required:
            raise ValidationError(self.error_messages['required'])

    def run_validators(self, value):
        if value in validators.EMPTY_VALUES:
            return
        errors = []
        for v in self.validators:
            try:
                v(value)
            except ValidationError, e:
                if hasattr(e, 'code') and e.code in self.error_messages:
                    message = self.error_messages[e.code]
                    if e.params:
                        message = message % e.params
                    errors.append(message)
                else:
                    errors.extend(e.messages)
        if errors:
            raise ValidationError(errors)

    def clean(self, value):
        """
        Validates the given value and returns its "cleaned" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return value

    def bound_data(self, data, initial):
        """
        Return the value that should be shown for this field on render of a
        bound form, given the submitted POST data for the field and the initial
        data, if any.

        For most fields, this will simply be data; FileFields need to handle it
        a bit differently.
        """
        return data

    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        return {}

    def __deepcopy__(self, memo):
        result = copy.copy(self)
        memo[id(self)] = result
        result.widget = copy.deepcopy(self.widget, memo)
        return result

class CharField(Field):
    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        self.max_length, self.min_length = max_length, min_length
        super(CharField, self).__init__(*args, **kwargs)
        if min_length is not None:
            self.validators.append(validators.MinLengthValidator(min_length))
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(max_length))

    def to_python(self, value):
        "Returns a Unicode object."
        if value in validators.EMPTY_VALUES:
            return u''
        return smart_unicode(value)

    def widget_attrs(self, widget):
        if self.max_length is not None and isinstance(widget, (TextInput, PasswordInput)):
            # The HTML attribute is maxlength, not max_length.
            return {'maxlength': str(self.max_length)}

class IntegerField(Field):
    default_error_messages = {
        'invalid': _(u'Enter a whole number.'),
        'max_value': _(u'Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _(u'Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, max_value=None, min_value=None, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)

        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(min_value))

    def to_python(self, value):
        """
        Validates that int() can be called on the input. Returns the result
        of int(). Returns None for empty values.
        """
        value = super(IntegerField, self).to_python(value)
        if value in validators.EMPTY_VALUES:
            return None
        if self.localize:
            value = formats.sanitize_separators(value)
        try:
            value = int(str(value))
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value

class FloatField(IntegerField):
    default_error_messages = {
        'invalid': _(u'Enter a number.'),
    }

    def to_python(self, value):
        """
        Validates that float() can be called on the input. Returns the result
        of float(). Returns None for empty values.
        """
        value = super(IntegerField, self).to_python(value)
        if value in validators.EMPTY_VALUES:
            return None
        if self.localize:
            value = formats.sanitize_separators(value)
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value

class DecimalField(Field):
    default_error_messages = {
        'invalid': _(u'Enter a number.'),
        'max_value': _(u'Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _(u'Ensure this value is greater than or equal to %(limit_value)s.'),
        'max_digits': _('Ensure that there are no more than %s digits in total.'),
        'max_decimal_places': _('Ensure that there are no more than %s decimal places.'),
        'max_whole_digits': _('Ensure that there are no more than %s digits before the decimal point.')
    }

    def __init__(self, max_value=None, min_value=None, max_digits=None, decimal_places=None, *args, **kwargs):
        self.max_digits, self.decimal_places = max_digits, decimal_places
        Field.__init__(self, *args, **kwargs)

        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(min_value))

    def to_python(self, value):
        """
        Validates that the input is a decimal number. Returns a Decimal
        instance. Returns None for empty values. Ensures that there are no more
        than max_digits in the number, and no more than decimal_places digits
        after the decimal point.
        """
        if value in validators.EMPTY_VALUES:
            return None
        if self.localize:
            value = formats.sanitize_separators(value)
        value = smart_str(value).strip()
        try:
            value = Decimal(value)
        except DecimalException:
            raise ValidationError(self.error_messages['invalid'])
        return value

    def validate(self, value):
        super(DecimalField, self).validate(value)
        if value in validators.EMPTY_VALUES:
            return
        # Check for NaN, Inf and -Inf values. We can't compare directly for NaN,
        # since it is never equal to itself. However, NaN is the only value that
        # isn't equal to itself, so we can use this to identify NaN
        if value != value or value == Decimal("Inf") or value == Decimal("-Inf"):
            raise ValidationError(self.error_messages['invalid'])
        sign, digittuple, exponent = value.as_tuple()
        decimals = abs(exponent)
        # digittuple doesn't include any leading zeros.
        digits = len(digittuple)
        if decimals > digits:
            # We have leading zeros up to or past the decimal point.  Count
            # everything past the decimal point as a digit.  We do not count
            # 0 before the decimal point as a digit since that would mean
            # we would not allow max_digits = decimal_places.
            digits = decimals
        whole_digits = digits - decimals

        if self.max_digits is not None and digits > self.max_digits:
            raise ValidationError(self.error_messages['max_digits'] % self.max_digits)
        if self.decimal_places is not None and decimals > self.decimal_places:
            raise ValidationError(self.error_messages['max_decimal_places'] % self.decimal_places)
        if self.max_digits is not None and self.decimal_places is not None and whole_digits > (self.max_digits - self.decimal_places):
            raise ValidationError(self.error_messages['max_whole_digits'] % (self.max_digits - self.decimal_places))
        return value

class DateField(Field):
    widget = DateInput
    default_error_messages = {
        'invalid': _(u'Enter a valid date.'),
    }

    def __init__(self, input_formats=None, *args, **kwargs):
        super(DateField, self).__init__(*args, **kwargs)
        self.input_formats = input_formats

    def to_python(self, value):
        """
        Validates that the input can be converted to a date. Returns a Python
        datetime.date object.
        """
        if value in validators.EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in self.input_formats or formats.get_format('DATE_INPUT_FORMATS'):
            try:
                return datetime.date(*time.strptime(value, format)[:3])
            except ValueError:
                continue
        raise ValidationError(self.error_messages['invalid'])

class TimeField(Field):
    widget = TimeInput
    default_error_messages = {
        'invalid': _(u'Enter a valid time.')
    }

    def __init__(self, input_formats=None, *args, **kwargs):
        super(TimeField, self).__init__(*args, **kwargs)
        self.input_formats = input_formats

    def to_python(self, value):
        """
        Validates that the input can be converted to a time. Returns a Python
        datetime.time object.
        """
        if value in validators.EMPTY_VALUES:
            return None
        if isinstance(value, datetime.time):
            return value
        for format in self.input_formats or formats.get_format('TIME_INPUT_FORMATS'):
            try:
                return datetime.time(*time.strptime(value, format)[3:6])
            except ValueError:
                continue
        raise ValidationError(self.error_messages['invalid'])

class DateTimeField(Field):
    widget = DateTimeInput
    default_error_messages = {
        'invalid': _(u'Enter a valid date/time.'),
    }

    def __init__(self, input_formats=None, *args, **kwargs):
        super(DateTimeField, self).__init__(*args, **kwargs)
        self.input_formats = input_formats

    def to_python(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        if value in validators.EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        if isinstance(value, list):
            # Input comes from a SplitDateTimeWidget, for example. So, it's two
            # components: date and time.
            if len(value) != 2:
                raise ValidationError(self.error_messages['invalid'])
            if value[0] in validators.EMPTY_VALUES and value[1] in validators.EMPTY_VALUES:
                return None
            value = '%s %s' % tuple(value)
        for format in self.input_formats or formats.get_format('DATETIME_INPUT_FORMATS'):
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        raise ValidationError(self.error_messages['invalid'])

class RegexField(CharField):
    def __init__(self, regex, max_length=None, min_length=None, error_message=None, *args, **kwargs):
        """
        regex can be either a string or a compiled regular expression object.
        error_message is an optional error message to use, if
        'Enter a valid value' is too generic for you.
        """
        # error_message is just kept for backwards compatibility:
        if error_message:
            error_messages = kwargs.get('error_messages') or {}
            error_messages['invalid'] = error_message
            kwargs['error_messages'] = error_messages
        super(RegexField, self).__init__(max_length, min_length, *args, **kwargs)
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.validators.append(validators.RegexValidator(regex=regex))

class EmailField(CharField):
    default_error_messages = {
        'invalid': _(u'Enter a valid e-mail address.'),
    }
    default_validators = [validators.validate_email]

    def clean(self, value):
        value = self.to_python(value).strip()
        return super(EmailField, self).clean(value)

class FileField(Field):
    widget = ClearableFileInput
    default_error_messages = {
        'invalid': _(u"No file was submitted. Check the encoding type on the form."),
        'missing': _(u"No file was submitted."),
        'empty': _(u"The submitted file is empty."),
        'max_length': _(u'Ensure this filename has at most %(max)d characters (it has %(length)d).'),
        'contradiction': _(u'Please either submit a file or check the clear checkbox, not both.')
    }

    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.pop('max_length', None)
        super(FileField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        if data in validators.EMPTY_VALUES:
            return None

        # UploadedFile objects should have name and size attributes.
        try:
            file_name = data.name
            file_size = data.size
        except AttributeError:
            raise ValidationError(self.error_messages['invalid'])

        if self.max_length is not None and len(file_name) > self.max_length:
            error_values =  {'max': self.max_length, 'length': len(file_name)}
            raise ValidationError(self.error_messages['max_length'] % error_values)
        if not file_name:
            raise ValidationError(self.error_messages['invalid'])
        if not file_size:
            raise ValidationError(self.error_messages['empty'])

        return data

    def clean(self, data, initial=None):
        # If the widget got contradictory inputs, we raise a validation error
        if data is FILE_INPUT_CONTRADICTION:
            raise ValidationError(self.error_messages['contradiction'])
        # False means the field value should be cleared; further validation is
        # not needed.
        if data is False:
            if not self.required:
                return False
            # If the field is required, clearing is not possible (the widget
            # shouldn't return False data in that case anyway). False is not
            # in validators.EMPTY_VALUES; if a False value makes it this far
            # it should be validated from here on out as None (so it will be
            # caught by the required check).
            data = None
        if not data and initial:
            return initial
        return super(FileField, self).clean(data)

    def bound_data(self, data, initial):
        if data in (None, FILE_INPUT_CONTRADICTION):
            return initial
        return data

class ImageField(FileField):
    default_error_messages = {
        'invalid_image': _(u"Upload a valid image. The file you uploaded was either not an image or a corrupted image."),
    }

    def to_python(self, data):
        """
        Checks that the file-upload field data contains a valid image (GIF, JPG,
        PNG, possibly others -- whatever the Python Imaging Library supports).
        """
        f = super(ImageField, self).to_python(data)
        if f is None:
            return None

        # Try to import PIL in either of the two ways it can end up installed.
        try:
            from PIL import Image
        except ImportError:
            import Image

        # We need to get a file object for PIL. We might have a path or we might
        # have to read the data into memory.
        if hasattr(data, 'temporary_file_path'):
            file = data.temporary_file_path()
        else:
            if hasattr(data, 'read'):
                file = StringIO(data.read())
            else:
                file = StringIO(data['content'])

        try:
            # load() is the only method that can spot a truncated JPEG,
            #  but it cannot be called sanely after verify()
            trial_image = Image.open(file)
            trial_image.load()

            # Since we're about to use the file again we have to reset the
            # file object if possible.
            if hasattr(file, 'reset'):
                file.reset()

            # verify() is the only method that can spot a corrupt PNG,
            #  but it must be called immediately after the constructor
            trial_image = Image.open(file)
            trial_image.verify()
        except ImportError:
            # Under PyPy, it is possible to import PIL. However, the underlying
            # _imaging C module isn't available, so an ImportError will be
            # raised. Catch and re-raise.
            raise
        except Exception: # Python Imaging Library doesn't recognize it as an image
            raise ValidationError(self.error_messages['invalid_image'])
        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)
        return f

class URLField(CharField):
    default_error_messages = {
        'invalid': _(u'Enter a valid URL.'),
        'invalid_link': _(u'This URL appears to be a broken link.'),
    }

    def __init__(self, max_length=None, min_length=None, verify_exists=False,
            validator_user_agent=validators.URL_VALIDATOR_USER_AGENT, *args, **kwargs):
        super(URLField, self).__init__(max_length, min_length, *args,
                                       **kwargs)
        self.validators.append(validators.URLValidator(verify_exists=verify_exists, validator_user_agent=validator_user_agent))

    def to_python(self, value):
        if value:
            if '://' not in value:
                # If no URL scheme given, assume http://
                value = u'http://%s' % value
            url_fields = list(urlparse.urlsplit(value))
            if not url_fields[2]:
                # the path portion may need to be added before query params
                url_fields[2] = '/'
                value = urlparse.urlunsplit(url_fields)
        return super(URLField, self).to_python(value)

class BooleanField(Field):
    widget = CheckboxInput

    def to_python(self, value):
        """Returns a Python boolean object."""
        # Explicitly check for the string 'False', which is what a hidden field
        # will submit for False. Also check for '0', since this is what
        # RadioSelect will provide. Because bool("True") == bool('1') == True,
        # we don't need to handle that explicitly.
        if value in ('False', '0'):
            value = False
        else:
            value = bool(value)
        value = super(BooleanField, self).to_python(value)
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])
        return value

class NullBooleanField(BooleanField):
    """
    A field whose valid values are None, True and False. Invalid values are
    cleaned to None.
    """
    widget = NullBooleanSelect

    def to_python(self, value):
        """
        Explicitly checks for the string 'True' and 'False', which is what a
        hidden field will submit for True and False, and for '1' and '0', which
        is what a RadioField will submit. Unlike the Booleanfield we need to
        explicitly check for True, because we are not using the bool() function
        """
        if value in (True, 'True', '1'):
            return True
        elif value in (False, 'False', '0'):
            return False
        else:
            return None

    def validate(self, value):
        pass

class ChoiceField(Field):
    widget = Select
    default_error_messages = {
        'invalid_choice': _(u'Select a valid choice. %(value)s is not one of the available choices.'),
    }

    def __init__(self, choices=(), required=True, widget=None, label=None,
                 initial=None, help_text=None, *args, **kwargs):
        super(ChoiceField, self).__init__(required=required, widget=widget, label=label,
                                        initial=initial, help_text=help_text, *args, **kwargs)
        self.choices = choices

    def _get_choices(self):
        return self._choices

    def _set_choices(self, value):
        # Setting choices also sets the choices on the widget.
        # choices can be any iterable, but we call list() on it because
        # it will be consumed more than once.
        self._choices = self.widget.choices = list(value)

    choices = property(_get_choices, _set_choices)

    def to_python(self, value):
        "Returns a Unicode object."
        if value in validators.EMPTY_VALUES:
            return u''
        return smart_unicode(value)

    def validate(self, value):
        """
        Validates that the input is in self.choices.
        """
        super(ChoiceField, self).validate(value)
        if value and not self.valid_value(value):
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

    def valid_value(self, value):
        "Check to see if the provided value is a valid choice"
        for k, v in self.choices:
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == smart_unicode(k2):
                        return True
            else:
                if value == smart_unicode(k):
                    return True
        return False

class TypedChoiceField(ChoiceField):
    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', lambda val: val)
        self.empty_value = kwargs.pop('empty_value', '')
        super(TypedChoiceField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Validate that the value is in self.choices and can be coerced to the
        right type.
        """
        value = super(TypedChoiceField, self).to_python(value)
        super(TypedChoiceField, self).validate(value)
        if value == self.empty_value or value in validators.EMPTY_VALUES:
            return self.empty_value
        try:
            value = self.coerce(value)
        except (ValueError, TypeError, ValidationError):
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})
        return value

    def validate(self, value):
        pass

class MultipleChoiceField(ChoiceField):
    hidden_widget = MultipleHiddenInput
    widget = SelectMultiple
    default_error_messages = {
        'invalid_choice': _(u'Select a valid choice. %(value)s is not one of the available choices.'),
        'invalid_list': _(u'Enter a list of values.'),
    }

    def to_python(self, value):
        if not value:
            return []
        elif not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['invalid_list'])
        return [smart_unicode(val) for val in value]

    def validate(self, value):
        """
        Validates that the input is a list or tuple.
        """
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        # Validate that each value in the value list is in self.choices.
        for val in value:
            if not self.valid_value(val):
                raise ValidationError(self.error_messages['invalid_choice'] % {'value': val})

class ComboField(Field):
    """
    A Field whose clean() method calls multiple Field clean() methods.
    """
    def __init__(self, fields=(), *args, **kwargs):
        super(ComboField, self).__init__(*args, **kwargs)
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
        super(ComboField, self).clean(value)
        for field in self.fields:
            value = field.clean(value)
        return value

class MultiValueField(Field):
    """
    A Field that aggregates the logic of multiple Fields.

    Its clean() method takes a "decompressed" list of values, which are then
    cleaned into a single value according to self.fields. Each value in
    this list is cleaned by the corresponding field -- the first value is
    cleaned by the first field, the second value is cleaned by the second
    field, etc. Once all fields are cleaned, the list of clean values is
    "compressed" into a single value.

    Subclasses should not have to implement clean(). Instead, they must
    implement compress(), which takes a list of valid values and returns a
    "compressed" version of those values -- a single value.

    You'll probably want to use this with MultiWidget.
    """
    default_error_messages = {
        'invalid': _(u'Enter a list of values.'),
    }

    def __init__(self, fields=(), *args, **kwargs):
        super(MultiValueField, self).__init__(*args, **kwargs)
        # Set 'required' to False on the individual fields, because the
        # required validation will be handled by MultiValueField, not by those
        # individual fields.
        for f in fields:
            f.required = False
        self.fields = fields

    def validate(self, value):
        pass

    def clean(self, value):
        """
        Validates every value in the given list. A value is validated against
        the corresponding Field in self.fields.

        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), clean() would call
        DateField.clean(value[0]) and TimeField.clean(value[1]).
        """
        clean_data = []
        errors = ErrorList()
        if not value or isinstance(value, (list, tuple)):
            if not value or not [v for v in value if v not in validators.EMPTY_VALUES]:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                else:
                    return self.compress([])
        else:
            raise ValidationError(self.error_messages['invalid'])
        for i, field in enumerate(self.fields):
            try:
                field_value = value[i]
            except IndexError:
                field_value = None
            if self.required and field_value in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['required'])
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError, e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        return out

    def compress(self, data_list):
        """
        Returns a single value for the given list of values. The values can be
        assumed to be valid.

        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), this might return a datetime
        object created by combining the date and time in data_list.
        """
        raise NotImplementedError('Subclasses must implement this method.')

class FilePathField(ChoiceField):
    def __init__(self, path, match=None, recursive=False, required=True,
                 widget=None, label=None, initial=None, help_text=None,
                 *args, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        super(FilePathField, self).__init__(choices=(), required=required,
            widget=widget, label=label, initial=initial, help_text=help_text,
            *args, **kwargs)

        if self.required:
            self.choices = []
        else:
            self.choices = [("", "---------")]

        if self.match is not None:
            self.match_re = re.compile(self.match)

        if recursive:
            for root, dirs, files in os.walk(self.path):
                for f in files:
                    if self.match is None or self.match_re.search(f):
                        f = os.path.join(root, f)
                        self.choices.append((f, f.replace(path, "", 1)))
        else:
            try:
                for f in os.listdir(self.path):
                    full_file = os.path.join(self.path, f)
                    if os.path.isfile(full_file) and (self.match is None or self.match_re.search(f)):
                        self.choices.append((full_file, f))
            except OSError:
                pass

        self.widget.choices = self.choices

class SplitDateTimeField(MultiValueField):
    widget = SplitDateTimeWidget
    hidden_widget = SplitHiddenDateTimeWidget
    default_error_messages = {
        'invalid_date': _(u'Enter a valid date.'),
        'invalid_time': _(u'Enter a valid time.'),
    }

    def __init__(self, input_date_formats=None, input_time_formats=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        localize = kwargs.get('localize', False)
        fields = (
            DateField(input_formats=input_date_formats,
                      error_messages={'invalid': errors['invalid_date']},
                      localize=localize),
            TimeField(input_formats=input_time_formats,
                      error_messages={'invalid': errors['invalid_time']},
                      localize=localize),
        )
        super(SplitDateTimeField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible if SplitDateTimeField has required=False).
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_date'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_time'])
            return datetime.datetime.combine(*data_list)
        return None


class IPAddressField(CharField):
    default_error_messages = {
        'invalid': _(u'Enter a valid IPv4 address.'),
    }
    default_validators = [validators.validate_ipv4_address]


class SlugField(CharField):
    default_error_messages = {
        'invalid': _(u"Enter a valid 'slug' consisting of letters, numbers,"
                     u" underscores or hyphens."),
    }
    default_validators = [validators.validate_slug]
