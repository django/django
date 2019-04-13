from datetime import date

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.secret_key import get_secret_key, get_verification_keys
from django.utils.crypto import (
    constant_time_any, constant_time_compare, salted_hmac,
)
from django.utils.http import base36_to_int, int_to_base36

USE_DEFAULT = object()


class PasswordResetTokenGenerator:
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """
    key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"
    _secret = USE_DEFAULT
    verification_keys = USE_DEFAULT

    @property
    def secret(self):
        if self._secret is USE_DEFAULT:
            return get_secret_key()
        return self._secret

    @secret.setter
    def secret(self, value):
        self._secret = value

    def _get_all_verification_keys(self):
        if self.verification_keys is not USE_DEFAULT:
            if self._secret is USE_DEFAULT:
                raise ImproperlyConfigured(
                    'verification_keys was specified on %s. '
                    'When specifying verification_keys, secret must also be specified.'
                )

            verification_keys = list(self.verification_keys)

        else:
            verification_keys = list(get_verification_keys())

        return [self.secret] + verification_keys

    def make_token(self, user):
        """
        Return a token that can be used once to do a password reset
        for the given user.
        """
        return self._make_token_with_timestamp(user, self._num_days(self._today()), self.secret)

    def check_token(self, user, token):
        """
        Check that a password reset token is correct for a given user.
        """
        if not (user and token):
            return False
        # Parse the token
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        attempts = [
            constant_time_compare(self._make_token_with_timestamp(user, ts, key), token)
            for key in self._get_all_verification_keys()
        ]

        if not constant_time_any(attempts):
            return False

        # Check the timestamp is within limit. Timestamps are rounded to
        # midnight (server time) providing a resolution of only 1 day. If a
        # link is generated 5 minutes before midnight and used 6 minutes later,
        # that counts as 1 day. Therefore, PASSWORD_RESET_TIMEOUT_DAYS = 1 means
        # "at least 1 day, could be up to 2."
        if (self._num_days(self._today()) - ts) > settings.PASSWORD_RESET_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp, secret):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp),
            secret=secret,
        ).hexdigest()[::2]  # Limit to 20 characters to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's primary key and some user state that's sure to change
        after a password reset to produce a token that invalidated when it's
        used:
        1. The password field will change upon a password reset (even if the
           same password is chosen, due to password salting).
        2. The last_login field will usually be updated very shortly after
           a password reset.
        Failing those things, settings.PASSWORD_RESET_TIMEOUT_DAYS eventually
        invalidates the token.

        Running this data through salted_hmac() prevents password cracking
        attempts using the reset token, provided the secret isn't compromised.
        """
        # Truncate microseconds so that tokens are consistent even if the
        # database doesn't support microseconds.
        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return str(user.pk) + user.password + str(login_timestamp) + str(timestamp)

    def _num_days(self, dt):
        return (dt - date(2001, 1, 1)).days

    def _today(self):
        # Used for mocking in tests
        return date.today()


default_token_generator = PasswordResetTokenGenerator()
