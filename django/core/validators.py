from __future__ import unicode_literals

import re

from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text
from django.utils.ipv6 import is_valid_ipv6_address
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit
from django.utils.translation import ugettext_lazy as _, ungettext_lazy

# These values, if given to validate(), will trigger the self.required check.
EMPTY_VALUES = (None, '', [], (), {})


@deconstructible
class RegexValidator(object):
    regex = ''
    message = _('Enter a valid value.')
    code = 'invalid'
    inverse_match = False
    flags = 0

    def __init__(self, regex=None, message=None, code=None, inverse_match=None, flags=None):
        if regex is not None:
            self.regex = regex
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if inverse_match is not None:
            self.inverse_match = inverse_match
        if flags is not None:
            self.flags = flags
        if self.flags and not isinstance(self.regex, six.string_types):
            raise TypeError("If the flags are set, regex must be a regular expression string.")

        # Compile the regex if it was not passed pre-compiled.
        if isinstance(self.regex, six.string_types):
            self.regex = re.compile(self.regex, self.flags)

    def __call__(self, value):
        """
        Validates that the input matches the regular expression
        if inverse_match is False, otherwise raises ValidationError.
        """
        if not (self.inverse_match is not bool(self.regex.search(
                force_text(value)))):
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return (
            isinstance(other, RegexValidator) and
            self.regex.pattern == other.regex.pattern and
            self.regex.flags == other.regex.flags and
            (self.message == other.message) and
            (self.code == other.code) and
            (self.inverse_match == other.inverse_match)
        )

    def __ne__(self, other):
        return not (self == other)


@deconstructible
class URLValidator(RegexValidator):
    ul = '\u00a1-\uffff'  # unicode letters range (must be a unicode string, not a raw string)

    # IP patterns
    ipv4_re = r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}'
    ipv6_re = r'\[[0-9a-f:\.]+\]'  # (simple regex, validated later)

    # Host patterns
    hostname_re = r'[a-z' + ul + r'0-9](?:[a-z' + ul + r'0-9-]*[a-z' + ul + r'0-9])?'
    domain_re = r'(?:\.(?!-)[a-z' + ul + r'0-9-]*(?<!-))*'
    tld_re = r'\.(?:[a-z' + ul + r']{2,}|xn--[a-z0-9]+)\.?'
    host_re = '(' + hostname_re + domain_re + tld_re + '|localhost)'

    regex = re.compile(
        r'^(?:[a-z0-9\.\-]*)://'  # scheme is validated separately
        r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
        r'(?:' + ipv4_re + '|' + ipv6_re + '|' + host_re + ')'
        r'(?::\d{2,5})?'  # port
        r'(?:[/?#][^\s]*)?'  # resource path
        r'\Z', re.IGNORECASE)
    message = _('Enter a valid URL.')
    schemes = ['http', 'https', 'ftp', 'ftps']

    def __init__(self, schemes=None, **kwargs):
        super(URLValidator, self).__init__(**kwargs)
        if schemes is not None:
            self.schemes = schemes

    def __call__(self, value):
        value = force_text(value)
        # Check first if the scheme is valid
        scheme = value.split('://')[0].lower()
        if scheme not in self.schemes:
            raise ValidationError(self.message, code=self.code)

        # Then check full URL
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain
            if value:
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
            # Now verify IPv6 in the netloc part
            host_match = re.search(r'^\[(.+)\](?::\d{2,5})?$', urlsplit(value).netloc)
            if host_match:
                potential_ip = host_match.groups()[0]
                try:
                    validate_ipv6_address(potential_ip)
                except ValidationError:
                    raise ValidationError(self.message, code=self.code)
            url = value

integer_validator = RegexValidator(
    re.compile('^-?\d+\Z'),
    message=_('Enter a valid integer.'),
    code='invalid',
)


def validate_integer(value):
    return integer_validator(value)


@deconstructible
class EmailValidator(object):
    message = _('Enter a valid email address.')
    code = 'invalid'
    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"  # dot-atom
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"\Z)',  # quoted-string
        re.IGNORECASE)
    domain_regex = re.compile(
        # max length of the domain is 249: 254 (max email length) minus one
        # period, two characters for the TLD, @ sign, & one character before @.
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,247}[A-Z0-9])?\.)+(?:[A-Z]{2,6}|[A-Z0-9-]{2,}(?<!-))\Z',
        re.IGNORECASE)
    literal_regex = re.compile(
        # literal form, ipv4 or ipv6 address (SMTP 4.1.3)
        r'\[([A-f0-9:\.]+)\]\Z',
        re.IGNORECASE)
    domain_whitelist = ['localhost']

    def __init__(self, message=None, code=None, whitelist=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if whitelist is not None:
            self.domain_whitelist = whitelist

    def __call__(self, value):
        value = force_text(value)

        if not value or '@' not in value:
            raise ValidationError(self.message, code=self.code)

        user_part, domain_part = value.rsplit('@', 1)

        if not self.user_regex.match(user_part):
            raise ValidationError(self.message, code=self.code)

        if (domain_part not in self.domain_whitelist and
                not self.validate_domain_part(domain_part)):
            # Try for possible IDN domain-part
            try:
                domain_part = domain_part.encode('idna').decode('ascii')
                if self.validate_domain_part(domain_part):
                    return
            except UnicodeError:
                pass
            raise ValidationError(self.message, code=self.code)

    def validate_domain_part(self, domain_part):
        if self.domain_regex.match(domain_part):
            return True

        literal_match = self.literal_regex.match(domain_part)
        if literal_match:
            ip_address = literal_match.group(1)
            try:
                validate_ipv46_address(ip_address)
                return True
            except ValidationError:
                pass
        return False

    def __eq__(self, other):
        return (
            isinstance(other, EmailValidator) and
            (self.domain_whitelist == other.domain_whitelist) and
            (self.message == other.message) and
            (self.code == other.code)
        )

validate_email = EmailValidator()

slug_re = re.compile(r'^[-a-zA-Z0-9_]+\Z')
validate_slug = RegexValidator(
    slug_re,
    _("Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."),
    'invalid'
)

ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\Z')
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

comma_separated_int_list_re = re.compile('^[\d,]+\Z')
validate_comma_separated_integer_list = RegexValidator(
    comma_separated_int_list_re,
    _('Enter only digits separated by commas.'),
    'invalid'
)


@deconstructible
class BaseValidator(object):
    compare = lambda self, a, b: a is not b
    clean = lambda self, x: x
    message = _('Ensure this value is %(limit_value)s (it is %(show_value)s).')
    code = 'limit_value'

    def __init__(self, limit_value, message=None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned, 'value': value}
        if self.compare(cleaned, self.limit_value):
            raise ValidationError(self.message, code=self.code, params=params)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            (self.limit_value == other.limit_value)
            and (self.message == other.message)
            and (self.code == other.code)
        )


@deconstructible
class MaxValueValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    message = _('Ensure this value is less than or equal to %(limit_value)s.')
    code = 'max_value'


@deconstructible
class MinValueValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    message = _('Ensure this value is greater than or equal to %(limit_value)s.')
    code = 'min_value'


@deconstructible
class MinLengthValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    clean = lambda self, x: len(x)
    message = ungettext_lazy(
        'Ensure this value has at least %(limit_value)d character (it has %(show_value)d).',
        'Ensure this value has at least %(limit_value)d characters (it has %(show_value)d).',
        'limit_value')
    code = 'min_length'


@deconstructible
class MaxLengthValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    clean = lambda self, x: len(x)
    message = ungettext_lazy(
        'Ensure this value has at most %(limit_value)d character (it has %(show_value)d).',
        'Ensure this value has at most %(limit_value)d characters (it has %(show_value)d).',
        'limit_value')
    code = 'max_length'
