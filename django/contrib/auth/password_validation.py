__all__ = (
    # Validator classes
    "CommonPasswordValidator",
    "MinimumLengthValidator",
    "NoAmbiguousCharactersValidator",
    "NoRepeatSubstringsValidator",
    "NoSequentialCharsValidator",
    "NumericPasswordValidator",
    "ShannonEntropyValidator",
    "UserAttributeSimilarityValidator",
    # Top-level functions
    "get_default_password_validators",
    "get_password_validators",
    "password_changed",
    "password_validators_help_text_html",
    "password_validators_help_texts",
    "validate_password"
)

import functools
import gzip
import math
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings
from django.core.exceptions import (
    FieldDoesNotExist, ImproperlyConfigured, ValidationError,
)
from django.utils.functional import lazy
from django.utils.html import format_html, format_html_join
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _, ngettext


@functools.lru_cache(maxsize=None)
def get_default_password_validators():
    return get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)


def get_password_validators(validator_config):
    validators = []
    for validator in validator_config:
        try:
            klass = import_string(validator['NAME'])
        except ImportError:
            msg = "The module in NAME could not be imported: %s. Check your AUTH_PASSWORD_VALIDATORS setting."
            raise ImproperlyConfigured(msg % validator['NAME'])
        validators.append(klass(**validator.get('OPTIONS', {})))

    return validators


def validate_password(password, user=None, password_validators=None):
    """
    Validate whether the password meets all validator requirements.

    If the password is valid, return ``None``.
    If the password is invalid, raise ValidationError with all error messages.
    """
    errors = []
    if password_validators is None:
        password_validators = get_default_password_validators()
    for validator in password_validators:
        try:
            validator.validate(password, user)
        except ValidationError as error:
            errors.append(error)
    if errors:
        raise ValidationError(errors)


def password_changed(password, user=None, password_validators=None):
    """
    Inform all validators that have implemented a password_changed() method
    that the password has been changed.
    """
    if password_validators is None:
        password_validators = get_default_password_validators()
    for validator in password_validators:
        password_changed = getattr(validator, 'password_changed', lambda *a: None)
        password_changed(password, user)


def password_validators_help_texts(password_validators=None):
    """
    Return a list of all help texts of all configured validators.
    """
    help_texts = []
    if password_validators is None:
        password_validators = get_default_password_validators()
    for validator in password_validators:
        help_texts.append(validator.get_help_text())
    return help_texts


def _password_validators_help_text_html(password_validators=None):
    """
    Return an HTML string with all help texts of all configured validators
    in an <ul>.
    """
    help_texts = password_validators_help_texts(password_validators)
    help_items = format_html_join('', '<li>{}</li>', ((help_text,) for help_text in help_texts))
    return format_html('<ul>{}</ul>', help_items) if help_items else ''


password_validators_help_text_html = lazy(_password_validators_help_text_html, str)


class MinimumLengthValidator:
    """
    Validate whether the password is of a minimum length.
    """
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                ngettext(
                    "This password is too short. It must contain at least %(min_length)d character.",
                    "This password is too short. It must contain at least %(min_length)d characters.",
                    self.min_length
                ),
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self):
        return ngettext(
            "Your password must contain at least %(min_length)d character.",
            "Your password must contain at least %(min_length)d characters.",
            self.min_length
        ) % {'min_length': self.min_length}


class UserAttributeSimilarityValidator:
    """
    Validate whether the password is sufficiently different from the user's
    attributes.

    If no specific attributes are provided, look at a sensible list of
    defaults. Attributes that don't exist are ignored. Comparison is made to
    not only the full attribute value, but also its components, so that, for
    example, a password is validated against either part of an email address,
    as well as the full address.
    """
    DEFAULT_USER_ATTRIBUTES = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, user_attributes=DEFAULT_USER_ATTRIBUTES, max_similarity=0.7):
        self.user_attributes = user_attributes
        self.max_similarity = max_similarity

    def validate(self, password, user=None):
        if not user:
            return

        for attribute_name in self.user_attributes:
            value = getattr(user, attribute_name, None)
            if not value or not isinstance(value, str):
                continue
            value_parts = re.split(r'\W+', value) + [value]
            for value_part in value_parts:
                if SequenceMatcher(a=password.lower(), b=value_part.lower()).quick_ratio() >= self.max_similarity:
                    try:
                        verbose_name = str(user._meta.get_field(attribute_name).verbose_name)
                    except FieldDoesNotExist:
                        verbose_name = attribute_name
                    raise ValidationError(
                        _("The password is too similar to the %(verbose_name)s."),
                        code='password_too_similar',
                        params={'verbose_name': verbose_name},
                    )

    def get_help_text(self):
        return _("Your password can't be too similar to your other personal information.")


class CommonPasswordValidator:
    """
    Validate whether the password is a common password.

    The password is rejected if it occurs in a provided list of passwords,
    which may be gzipped. The list Django ships with contains 20000 common
    passwords (lowercased and deduplicated), created by Royce Williams:
    https://gist.github.com/roycewilliams/281ce539915a947a23db17137d91aeb7
    The password list must be lowercased to match the comparison in validate().
    """
    DEFAULT_PASSWORD_LIST_PATH = Path(__file__).resolve().parent / 'common-passwords.txt.gz'

    def __init__(self, password_list_path=DEFAULT_PASSWORD_LIST_PATH):
        try:
            with gzip.open(str(password_list_path)) as f:
                common_passwords_lines = f.read().decode().splitlines()
        except OSError:
            with open(str(password_list_path)) as f:
                common_passwords_lines = f.readlines()

        self.passwords = {p.strip() for p in common_passwords_lines}

    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                _("This password is too common."),
                code='password_too_common',
            )

    def get_help_text(self):
        return _("Your password can't be a commonly used password.")


class NumericPasswordValidator:
    """
    Validate whether the password is alphanumeric.
    """
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                _("This password is entirely numeric."),
                code='password_entirely_numeric',
            )

    def get_help_text(self):
        return _("Your password can't be entirely numeric.")


class NoAmbiguousCharactersValidator:
    """
    Validate that the password does not contain ambiguous characters.

    The default set of ambiguous characters is:

    - The digit zero, 0
    - The digit one, 1
    - Capital letter I as in Isaac
    - Lowercase letter i as in intrinsic
    - Lowercase letter l as in leopard
    - The bar symbol, |
    - Uppercase letter O as in Onyx
    - Lowercase letter o as in operation

    This set is partly inspired by the characters included from a random
    password generated in BaseUserManager.make_random_password() from
    django/contrib/auth/base_user.py.
    """

    def __init__(
        self, ambiguous=frozenset(("0", "1", "I", "i", "|", "l", "O", "o"))
    ):
        if not ambiguous:
            raise ValueError("Must specify at least one ambiguous character.")
        # Always guarantee O(1) membership testing, no matter what user passes.
        self.ambiguous = set(ambiguous)

    def validate(self, password, user=None):
        found = sorted(self.ambiguous.intersection(password))
        if found:
            sfound = ", ".join(map(repr, found))
            msg = ngettext(
                "This password contains the following ambiguous character: %(sfound)s.",
                "This password contains the following ambiguous characters: %(sfound)s.",
                len(found),
            )
            raise ValidationError(
                msg,
                code="password_has_ambiguous_characters",
                params={"sfound": sfound},
            )

    def get_help_text(self):
        if len(self.ambiguous) == 1:
            return _(
                "Your password may not contain the ambiguous character %(char)r."
            ) % {"char": next(iter(self.ambiguous))}
        return _(
            "Your password may not contain ambiguous characters %(chars)s."
        ) % {"chars": ", ".join(map(repr, sorted(self.ambiguous)))}


class NoSequentialCharsValidator:
    """
    Validate that the password does not contain sequential repeated chars.

    If the password contains *greater than* `max_sequential_chars` repeats
    of a character consecutively, a ValidationError is raised.
    """

    def __init__(self, max_sequential_chars=2):
        if max_sequential_chars < 1:
            raise ValueError("`max_sequential_chars` must be >= 1.")
        self.max_sequential_chars = max_sequential_chars

    def validate(self, password, user=None):
        if len(password) <= self.max_sequential_chars:
            return None
        # Iterate over (i, j) pairs in password, incrementing a `seq`
        # counter if a repeat occurs or resetting it if one does not.
        # If at any time `seq` rises above max_sequential_chars,
        # raise immediately.
        previous = password[0]
        seq = 1
        for char in password[1:]:
            if char == previous:
                seq += 1
                if seq > self.max_sequential_chars:
                    raise ValidationError(
                        _(
                            "This password contains %(seq)d sequential characters."
                            "  Your password should contain no more than %(max)d"
                            " sequential characters."
                        ),
                        code="password_has_sequential_chars",
                        params={"seq": seq, "max": self.max_sequential_chars},
                    )
            else:
                seq = 1
            previous = char

    def get_help_text(self):
        return ngettext(
            "Your password must contain no more than %(n)d repeat of the same character in a row.",
            "Your password must contain no more than %(n)d repeats of the same character in a row.",
            self.max_sequential_chars,
        ) % {"n": self.max_sequential_chars}


class NoRepeatSubstringsValidator:
    """
    Validate that the password does not contain repeated substrings.

    The parameter max_length (int) specifies the *maximum allowed*
    length of a repeated substring.  `max_length` itself must be
    greater than 2.

    For example, specifying max_length=2 would raise a ValidationError
    on the password "abcdefabc", because "abc" is repeated and has a
    length of 3, which is greater than the maximum allowed of length 2.

    The validator does not concern itself with the *number* of repeats.

    Note that the technical definition here is for *overlapping*
    strings.  That means that validate("abcabcabc") will tell us that
    it is actually the substring "abcabc" that is repeated twice,
    rather than just "abc" as would be the case in the nonoverlappping
    version.

    The function for substring detection is modified from a recipe from
    Rajendra Dharmkar:

    https://www.tutorialspoint.com/How-to-find-longest-repetitive-sequence-in-a-string-in-Python

    This is the longest repeated substring problem.
    It uses what is basically a modified powerset, which is rough on
    time complexity but fast enough unless the password length gets
    outrageously long.  The O(N) alternative entails absolutely wicked
    code complexity in building a suffix tree.
    """

    def __init__(self, max_length=2):
        if max_length < 1:
            raise ValueError("max_length should be greater than 0.")
        self.max_length = max_length

    def validate(self, password, user=None):
        def longest_substring(r):
            def getsubs(loc, s):
                substr = s[loc:]
                i = -1
                while substr:
                    yield substr
                    substr = s[loc:i]
                    i -= 1

            occ = defaultdict(int)
            for i, __ in enumerate(r):
                for sub in getsubs(i, r):
                    if len(sub) >= self.max_length:
                        occ[sub] += 1
            try:
                return max((k for k, v in occ.items() if v >= 2), key=len)
            except ValueError:
                return ""

        longest_ss = longest_substring(password)
        if len(longest_ss) > self.max_length:
            raise ValidationError(
                _(
                    "This password contains a repeated substring longer than %(len)d characters: %(ss)r."
                )
                % {"len": self.max_length, "ss": longest_ss},
                code="password_found_repeat_substring",
            )

    def get_help_text(self):
        return ngettext(
            "Your password should not contain a repeated substring longer than %(mr)d character.",
            "Your password should not contain a repeated substring longer than %(mr)d characters.",
            self.max_length,
        ) % {"mr": self.max_length}


class ShannonEntropyValidator:
    """
    Validate that the password is sufficiently complex.

    The score is Shannon Entropy, described at:
    http://bearcave.com/misl/misl_tech/wavelets/compression/shannon.html.

    It is a way to estimate the average minimum number of bits needed
    to encode a string.
    """

    # We pick a default number of 3.0 which is, admittedly, not all
    # that strong, and leave it up to the developer to increase this
    # threshold.  For some perspective, the Shannon entropy
    # of the string "({ucdC(Rp7kG" is 3.42.  This string was derived
    # from Dashlane Password Generator using a combination of
    # mixed-case letters, digits, and symbols, and scores "Strength: 100"
    # according to Dashlane.  The string "11123456789" scores a 3.03.
    DEFAULT_MIN_ENTROPY = 3.0

    def __init__(self, min_entropy=DEFAULT_MIN_ENTROPY):
        self.min_entropy = min_entropy

    @staticmethod
    def _shannon_entropy(password):
        """Number of bits needed *per symbol* if PW optimally encoded.

        Returns: float
        """

        # Probabilities (values sum to 1.0).  This is a PMF constructed
        # in linear time, rather than looping over collections.Counter
        # to first get the counts and then normalize.

        if not password:
            return 0.
        freq = defaultdict(float)
        incr = 1 / len(password)
        for char in password:
            freq[char] += incr
        return -1 * sum(p * math.log2(p) for p in freq.values())

    def validate(self, password, user=None):
        se = self._shannon_entropy(password)
        if se < self.min_entropy:
            raise ValidationError(
                _("This password does not meet the required complexity "
                  "score of %(min_entropy).2f; it scores a %(se).2f.  "
                  "Increase the length of the password and avoid repeating "
                  "characters."),
                code="password_not_complex_enough",
                params={"min_entropy": self.min_entropy, "se": se},
            )

    def get_help_text(self):
        return _("Your password should meet an overall complexity score. "
                 "This score is based on the length of the password and "
                 "variety of unique characters used.")
