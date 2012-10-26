from __future__ import unicode_literals

import re
try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:     # Python 2
    from urlparse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.utils.ipv6 import is_valid_ipv6_address
from django.utils import six

# These values, if given to validate(), will trigger the self.required check.
EMPTY_VALUES = (None, '', [], (), {})


class RegexValidator(object):
    regex = ''
    message = _('Enter a valid value.')
    code = 'invalid'

    def __init__(self, regex=None, message=None, code=None):
        if regex is not None:
            self.regex = regex
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

        # Compile the regex if it was not passed pre-compiled.
        if isinstance(self.regex, six.string_types):
            self.regex = re.compile(self.regex)

    def __call__(self, value):
        """
        Validates that the input matches the regular expression.
        """
        if not self.regex.search(force_text(value)):
            raise ValidationError(self.message, code=self.code)


class URLValidator(RegexValidator):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __call__(self, value):
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = force_text(value)
                scheme, netloc, path, query, fragment = urlsplit(value)
                try:
                    netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
                except UnicodeError:  # invalid domain part
                    raise e
                url = urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value


def validate_integer(value):
    try:
        int(value)
    except (ValueError, TypeError):
        raise ValidationError('')


class EmailValidator(RegexValidator):

    def __call__(self, value):
        try:
            super(EmailValidator, self).__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain-part
            if value and '@' in value:
                parts = value.split('@')
                try:
                    parts[-1] = parts[-1].encode('idna').decode('ascii')
                except UnicodeError:
                    raise e
                super(EmailValidator, self).__call__('@'.join(parts))
            else:
                raise

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    # quoted-string, see also http://tools.ietf.org/html/rfc2822#section-3.2.5
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'
    r')@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)$)'  # domain
    r'|\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$', re.IGNORECASE)  # literal form, ipv4 address (SMTP 4.1.3)
validate_email = EmailValidator(email_re, _('Enter a valid email address.'), 'invalid')

slug_re = re.compile(r'^[-a-zA-Z0-9_]+$')
validate_slug = RegexValidator(slug_re, _("Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."), 'invalid')

ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')
validate_ipv4_address = RegexValidator(ipv4_re, _('Enter a valid IPv4 address.'), 'invalid')


def validate_ipv6_address(value):
    if not is_valid_ipv6_address(value):
        raise ValidationError(_('Enter a valid IPv6 address.'), code='invalid')


def validate_ipv46_address(value):
    try:
        validate_ipv4_address(value)
    except ValidationError:
        try:
            validate_ipv6_address(value)
        except ValidationError:
            raise ValidationError(_('Enter a valid IPv4 or IPv6 address.'), code='invalid')

ip_address_validator_map = {
    'both': ([validate_ipv46_address], _('Enter a valid IPv4 or IPv6 address.')),
    'ipv4': ([validate_ipv4_address], _('Enter a valid IPv4 address.')),
    'ipv6': ([validate_ipv6_address], _('Enter a valid IPv6 address.')),
}


def ip_address_validators(protocol, unpack_ipv4):
    """
    Depending on the given parameters returns the appropriate validators for
    the GenericIPAddressField.

    This code is here, because it is exactly the same for the model and the form field.
    """
    if protocol != 'both' and unpack_ipv4:
        raise ValueError(
            "You can only use `unpack_ipv4` if `protocol` is set to 'both'")
    try:
        return ip_address_validator_map[protocol.lower()]
    except KeyError:
        raise ValueError("The protocol '%s' is unknown. Supported: %s"
                         % (protocol, list(ip_address_validator_map)))

comma_separated_int_list_re = re.compile('^[\d,]+$')
validate_comma_separated_integer_list = RegexValidator(comma_separated_int_list_re, _('Enter only digits separated by commas.'), 'invalid')


class BaseValidator(object):
    compare = lambda self, a, b: a is not b
    clean = lambda self, x: x
    message = _('Ensure this value is %(limit_value)s (it is %(show_value)s).')
    code = 'limit_value'

    def __init__(self, limit_value):
        self.limit_value = limit_value

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned}
        if self.compare(cleaned, self.limit_value):
            raise ValidationError(
                self.message % params,
                code=self.code,
                params=params,
            )


class MaxValueValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    message = _('Ensure this value is less than or equal to %(limit_value)s.')
    code = 'max_value'


class MinValueValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    message = _('Ensure this value is greater than or equal to %(limit_value)s.')
    code = 'min_value'


class MinLengthValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    clean = lambda self, x: len(x)
    message = _('Ensure this value has at least %(limit_value)d characters (it has %(show_value)d).')
    code = 'min_length'


class MaxLengthValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    clean = lambda self, x: len(x)
    message = _('Ensure this value has at most %(limit_value)d characters (it has %(show_value)d).')
    code = 'max_length'
