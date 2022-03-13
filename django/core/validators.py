import ipaddress
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.encoding import punycode
from django.utils.ipv6 import is_valid_ipv6_address
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

# These values, if given to validate(), will trigger the self.required check.
EMPTY_VALUES = (None, "", [], (), {})


@deconstructible
class RegexValidator:
    regex = ""
    message = _("Enter a valid value.")
    code = "invalid"
    inverse_match = False
    flags = 0

    def __init__(
        self, regex=None, message=None, code=None, inverse_match=None, flags=None
    ):
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
        if self.flags and not isinstance(self.regex, str):
            raise TypeError(
                "If the flags are set, regex must be a regular expression string."
            )

        self.regex = _lazy_re_compile(self.regex, self.flags)

    def __call__(self, value):
        """
        Validate that the input contains (or does *not* contain, if
        inverse_match is True) a match for the regular expression.
        """
        regex_matches = self.regex.search(str(value))
        invalid_input = regex_matches if self.inverse_match else not regex_matches
        if invalid_input:
            raise ValidationError(self.message, code=self.code, params={"value": value})

    def __eq__(self, other):
        return (
            isinstance(other, RegexValidator)
            and self.regex.pattern == other.regex.pattern
            and self.regex.flags == other.regex.flags
            and (self.message == other.message)
            and (self.code == other.code)
            and (self.inverse_match == other.inverse_match)
        )


@deconstructible
class URLValidator(RegexValidator):
    ul = "\u00a1-\uffff"  # Unicode letters range (must not be a raw string).

    # IP patterns
    ipv4_re = (
        r"(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)"
        r"(?:\.(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)){3}"
    )
    ipv6_re = r"\[[0-9a-f:.]+\]"  # (simple regex, validated later)

    # Host patterns
    hostname_re = (
        r"[a-z" + ul + r"0-9](?:[a-z" + ul + r"0-9-]{0,61}[a-z" + ul + r"0-9])?"
    )
    # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
    domain_re = r"(?:\.(?!-)[a-z" + ul + r"0-9-]{1,63}(?<!-))*"
    tld_re = (
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-z" + ul + "-]{2,63}"  # domain label
        r"|xn--[a-z0-9]{1,59})"  # or punycode label
        r"(?<!-)"  # can't end with a dash
        r"\.?"  # may have a trailing dot
    )
    host_re = "(" + hostname_re + domain_re + tld_re + "|localhost)"

    regex = _lazy_re_compile(
        r"^(?:[a-z0-9.+-]*)://"  # scheme is validated separately
        r"(?:[^\s:@/]+(?::[^\s:@/]*)?@)?"  # user:pass authentication
        r"(?:" + ipv4_re + "|" + ipv6_re + "|" + host_re + ")"
        r"(?::[0-9]{1,5})?"  # port
        r"(?:[/?#][^\s]*)?"  # resource path
        r"\Z",
        re.IGNORECASE,
    )
    message = _("Enter a valid URL.")
    schemes = ["http", "https", "ftp", "ftps"]
    unsafe_chars = frozenset("\t\r\n")

    def __init__(self, schemes=None, **kwargs):
        super().__init__(**kwargs)
        if schemes is not None:
            self.schemes = schemes

    def __call__(self, value):
        if not isinstance(value, str):
            raise ValidationError(self.message, code=self.code, params={"value": value})
        if self.unsafe_chars.intersection(value):
            raise ValidationError(self.message, code=self.code, params={"value": value})
        # Check if the scheme is valid.
        scheme = value.split("://")[0].lower()
        if scheme not in self.schemes:
            raise ValidationError(self.message, code=self.code, params={"value": value})

        # Then check full URL
        try:
            splitted_url = urlsplit(value)
        except ValueError:
            raise ValidationError(self.message, code=self.code, params={"value": value})
        try:
            super().__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                scheme, netloc, path, query, fragment = splitted_url
                try:
                    netloc = punycode(netloc)  # IDN -> ACE
                except UnicodeError:  # invalid domain part
                    raise e
                url = urlunsplit((scheme, netloc, path, query, fragment))
                super().__call__(url)
            else:
                raise
        else:
            # Now verify IPv6 in the netloc part
            host_match = re.search(r"^\[(.+)\](?::[0-9]{1,5})?$", splitted_url.netloc)
            if host_match:
                potential_ip = host_match[1]
                try:
                    validate_ipv6_address(potential_ip)
                except ValidationError:
                    raise ValidationError(
                        self.message, code=self.code, params={"value": value}
                    )

        # The maximum length of a full host name is 253 characters per RFC 1034
        # section 3.1. It's defined to be 255 bytes or less, but this includes
        # one byte for the length of the name and one byte for the trailing dot
        # that's used to indicate absolute names in DNS.
        if splitted_url.hostname is None or len(splitted_url.hostname) > 253:
            raise ValidationError(self.message, code=self.code, params={"value": value})


integer_validator = RegexValidator(
    _lazy_re_compile(r"^-?\d+\Z"),
    message=_("Enter a valid integer."),
    code="invalid",
)


def validate_integer(value):
    return integer_validator(value)


@deconstructible
class EmailValidator:
    message = _("Enter a valid email address.")
    code = "invalid"
    user_regex = _lazy_re_compile(
        # dot-atom
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"
        # quoted-string
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])'
        r'*"\Z)',
        re.IGNORECASE,
    )
    domain_regex = _lazy_re_compile(
        # max length for domain name labels is 63 characters per RFC 1034
        r"((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+)(?:[A-Z0-9-]{2,63}(?<!-))\Z",
        re.IGNORECASE,
    )
    literal_regex = _lazy_re_compile(
        # literal form, ipv4 or ipv6 address (SMTP 4.1.3)
        r"\[([A-F0-9:.]+)\]\Z",
        re.IGNORECASE,
    )
    domain_allowlist = ["localhost"]

    def __init__(self, message=None, code=None, allowlist=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if allowlist is not None:
            self.domain_allowlist = allowlist

    def __call__(self, value):
        if not value or "@" not in value:
            raise ValidationError(self.message, code=self.code, params={"value": value})

        user_part, domain_part = value.rsplit("@", 1)

        if not self.user_regex.match(user_part):
            raise ValidationError(self.message, code=self.code, params={"value": value})

        if domain_part not in self.domain_allowlist and not self.validate_domain_part(
            domain_part
        ):
            # Try for possible IDN domain-part
            try:
                domain_part = punycode(domain_part)
            except UnicodeError:
                pass
            else:
                if self.validate_domain_part(domain_part):
                    return
            raise ValidationError(self.message, code=self.code, params={"value": value})

    def validate_domain_part(self, domain_part):
        if self.domain_regex.match(domain_part):
            return True

        literal_match = self.literal_regex.match(domain_part)
        if literal_match:
            ip_address = literal_match[1]
            try:
                validate_ipv46_address(ip_address)
                return True
            except ValidationError:
                pass
        return False

    def __eq__(self, other):
        return (
            isinstance(other, EmailValidator)
            and (self.domain_allowlist == other.domain_allowlist)
            and (self.message == other.message)
            and (self.code == other.code)
        )


validate_email = EmailValidator()

slug_re = _lazy_re_compile(r"^[-a-zA-Z0-9_]+\Z")
validate_slug = RegexValidator(
    slug_re,
    # Translators: "letters" means latin letters: a-z and A-Z.
    _("Enter a valid “slug” consisting of letters, numbers, underscores or hyphens."),
    "invalid",
)

slug_unicode_re = _lazy_re_compile(r"^[-\w]+\Z")
validate_unicode_slug = RegexValidator(
    slug_unicode_re,
    _(
        "Enter a valid “slug” consisting of Unicode letters, numbers, underscores, or "
        "hyphens."
    ),
    "invalid",
)


def validate_ipv4_address(value):
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ValidationError(
            _("Enter a valid IPv4 address."), code="invalid", params={"value": value}
        )
    else:
        # Leading zeros are forbidden to avoid ambiguity with the octal
        # notation. This restriction is included in Python 3.9.5+.
        # TODO: Remove when dropping support for PY39.
        if any(octet != "0" and octet[0] == "0" for octet in value.split(".")):
            raise ValidationError(
                _("Enter a valid IPv4 address."),
                code="invalid",
                params={"value": value},
            )


def validate_ipv6_address(value):
    if not is_valid_ipv6_address(value):
        raise ValidationError(
            _("Enter a valid IPv6 address."), code="invalid", params={"value": value}
        )


def validate_ipv46_address(value):
    try:
        validate_ipv4_address(value)
    except ValidationError:
        try:
            validate_ipv6_address(value)
        except ValidationError:
            raise ValidationError(
                _("Enter a valid IPv4 or IPv6 address."),
                code="invalid",
                params={"value": value},
            )


ip_address_validator_map = {
    "both": ([validate_ipv46_address], _("Enter a valid IPv4 or IPv6 address.")),
    "ipv4": ([validate_ipv4_address], _("Enter a valid IPv4 address.")),
    "ipv6": ([validate_ipv6_address], _("Enter a valid IPv6 address.")),
}


def ip_address_validators(protocol, unpack_ipv4):
    """
    Depending on the given parameters, return the appropriate validators for
    the GenericIPAddressField.
    """
    if protocol != "both" and unpack_ipv4:
        raise ValueError(
            "You can only use `unpack_ipv4` if `protocol` is set to 'both'"
        )
    try:
        return ip_address_validator_map[protocol.lower()]
    except KeyError:
        raise ValueError(
            "The protocol '%s' is unknown. Supported: %s"
            % (protocol, list(ip_address_validator_map))
        )


def int_list_validator(sep=",", message=None, code="invalid", allow_negative=False):
    regexp = _lazy_re_compile(
        r"^%(neg)s\d+(?:%(sep)s%(neg)s\d+)*\Z"
        % {
            "neg": "(-)?" if allow_negative else "",
            "sep": re.escape(sep),
        }
    )
    return RegexValidator(regexp, message=message, code=code)


validate_comma_separated_integer_list = int_list_validator(
    message=_("Enter only digits separated by commas."),
)


@deconstructible
class BaseValidator:
    message = _("Ensure this value is %(limit_value)s (it is %(show_value)s).")
    code = "limit_value"

    def __init__(self, limit_value, message=None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def __call__(self, value):
        cleaned = self.clean(value)
        limit_value = (
            self.limit_value() if callable(self.limit_value) else self.limit_value
        )
        params = {"limit_value": limit_value, "show_value": cleaned, "value": value}
        if self.compare(cleaned, limit_value):
            raise ValidationError(self.message, code=self.code, params=params)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.limit_value == other.limit_value
            and self.message == other.message
            and self.code == other.code
        )

    def compare(self, a, b):
        return a is not b

    def clean(self, x):
        return x


@deconstructible
class MaxValueValidator(BaseValidator):
    message = _("Ensure this value is less than or equal to %(limit_value)s.")
    code = "max_value"

    def compare(self, a, b):
        return a > b


@deconstructible
class MinValueValidator(BaseValidator):
    message = _("Ensure this value is greater than or equal to %(limit_value)s.")
    code = "min_value"

    def compare(self, a, b):
        return a < b


@deconstructible
class MinLengthValidator(BaseValidator):
    message = ngettext_lazy(
        "Ensure this value has at least %(limit_value)d character (it has "
        "%(show_value)d).",
        "Ensure this value has at least %(limit_value)d characters (it has "
        "%(show_value)d).",
        "limit_value",
    )
    code = "min_length"

    def compare(self, a, b):
        return a < b

    def clean(self, x):
        return len(x)


@deconstructible
class MaxLengthValidator(BaseValidator):
    message = ngettext_lazy(
        "Ensure this value has at most %(limit_value)d character (it has "
        "%(show_value)d).",
        "Ensure this value has at most %(limit_value)d characters (it has "
        "%(show_value)d).",
        "limit_value",
    )
    code = "max_length"

    def compare(self, a, b):
        return a > b

    def clean(self, x):
        return len(x)


@deconstructible
class DecimalValidator:
    """
    Validate that the input does not exceed the maximum number of digits
    expected, otherwise raise ValidationError.
    """

    messages = {
        "invalid": _("Enter a number."),
        "max_digits": ngettext_lazy(
            "Ensure that there are no more than %(max)s digit in total.",
            "Ensure that there are no more than %(max)s digits in total.",
            "max",
        ),
        "max_decimal_places": ngettext_lazy(
            "Ensure that there are no more than %(max)s decimal place.",
            "Ensure that there are no more than %(max)s decimal places.",
            "max",
        ),
        "max_whole_digits": ngettext_lazy(
            "Ensure that there are no more than %(max)s digit before the decimal "
            "point.",
            "Ensure that there are no more than %(max)s digits before the decimal "
            "point.",
            "max",
        ),
    }

    def __init__(self, max_digits, decimal_places):
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def __call__(self, value):
        digit_tuple, exponent = value.as_tuple()[1:]
        if exponent in {"F", "n", "N"}:
            raise ValidationError(
                self.messages["invalid"], code="invalid", params={"value": value}
            )
        if exponent >= 0:
            # A positive exponent adds that many trailing zeros.
            digits = len(digit_tuple) + exponent
            decimals = 0
        else:
            # If the absolute value of the negative exponent is larger than the
            # number of digits, then it's the same as the number of digits,
            # because it'll consume all of the digits in digit_tuple and then
            # add abs(exponent) - len(digit_tuple) leading zeros after the
            # decimal point.
            if abs(exponent) > len(digit_tuple):
                digits = decimals = abs(exponent)
            else:
                digits = len(digit_tuple)
                decimals = abs(exponent)
        whole_digits = digits - decimals

        if self.max_digits is not None and digits > self.max_digits:
            raise ValidationError(
                self.messages["max_digits"],
                code="max_digits",
                params={"max": self.max_digits, "value": value},
            )
        if self.decimal_places is not None and decimals > self.decimal_places:
            raise ValidationError(
                self.messages["max_decimal_places"],
                code="max_decimal_places",
                params={"max": self.decimal_places, "value": value},
            )
        if (
            self.max_digits is not None
            and self.decimal_places is not None
            and whole_digits > (self.max_digits - self.decimal_places)
        ):
            raise ValidationError(
                self.messages["max_whole_digits"],
                code="max_whole_digits",
                params={"max": (self.max_digits - self.decimal_places), "value": value},
            )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.max_digits == other.max_digits
            and self.decimal_places == other.decimal_places
        )


@deconstructible
class FileExtensionValidator:
    message = _(
        "File extension “%(extension)s” is not allowed. "
        "Allowed extensions are: %(allowed_extensions)s."
    )
    code = "invalid_extension"

    def __init__(self, allowed_extensions=None, message=None, code=None):
        if allowed_extensions is not None:
            allowed_extensions = [
                allowed_extension.lower() for allowed_extension in allowed_extensions
            ]
        self.allowed_extensions = allowed_extensions
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value):
        extension = Path(value.name).suffix[1:].lower()
        if (
            self.allowed_extensions is not None
            and extension not in self.allowed_extensions
        ):
            raise ValidationError(
                self.message,
                code=self.code,
                params={
                    "extension": extension,
                    "allowed_extensions": ", ".join(self.allowed_extensions),
                    "value": value,
                },
            )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.allowed_extensions == other.allowed_extensions
            and self.message == other.message
            and self.code == other.code
        )


def get_available_image_extensions():
    try:
        from PIL import Image
    except ImportError:
        return []
    else:
        Image.init()
        return [ext.lower()[1:] for ext in Image.EXTENSION]


def validate_image_file_extension(value):
    return FileExtensionValidator(allowed_extensions=get_available_image_extensions())(
        value
    )


@deconstructible
class ProhibitNullCharactersValidator:
    """Validate that the string doesn't contain the null character."""

    message = _("Null characters are not allowed.")
    code = "null_characters_not_allowed"

    def __init__(self, message=None, code=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value):
        if "\x00" in str(value):
            raise ValidationError(self.message, code=self.code, params={"value": value})

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.message == other.message
            and self.code == other.code
        )
