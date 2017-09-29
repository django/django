from datetime import date, datetime

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36


class PasswordResetTokenGenerator:
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """
    key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"
    secret = settings.SECRET_KEY
    timeout_type = 'SECONDS' if hasattr(settings, 'PASSWORD_RESET_TIMEOUT') else 'DAYS'

    def make_token(self, user):
        """
        Return a token that can be used once to do a password reset
        for the given user.
        """
        return self._make_token_with_timestamp(user, self._num_seconds(self._now()))

    def check_token(self, user, token):
        """
        Check that a password reset token is correct for a given user.
        """
        if not (user and token):
            return False
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(user, ts), token):
            return False

        # Check the timestamp is within limit
        # Because settings may be changed between PASSWORD_RESET_TIMEOUT and PASSWORD_RESET_TIMEOUT_DAYS,
        # convert both to seconds to compare
        timeout = settings.PASSWORD_RESET_TIMEOUT if hasattr(settings, 'PASSWORD_RESET_TIMEOUT') \
            else settings.PASSWORD_RESET_TIMEOUT_DAYS * 24 * 60 * 60

        ts = ts * 24 * 60 * 60 if len(ts_b36) < 6 else ts

        if (self._num_seconds(self._now()) - ts) > timeout:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp):
        # If using PASSWORD_RESET_TIMEOUT_DAYS, timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        # If using PASSWORD_RESET_TIMEOUT, timestamp is number of seconds since 2001-1-1.  Converted to
        # base 36, this gives us a 6 digit string for a long long time
        ts_b36 = int_to_base36(timestamp)

        # By hashing on the internal state of the user and using state
        # that is sure to change (the password salt will change as soon as
        # the password is set, at least for current Django auth, and
        # last_login will also change), we produce a hash that will be
        # invalid as soon as it is used.
        # We limit the hash to 20 chars to keep URL short

        hash = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp),
            secret=self.secret,
        ).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)

    def _make_hash_value(self, user, timestamp):
        # Ensure results are consistent across DB backends
        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return str(user.pk) + user.password + str(login_timestamp) + str(timestamp)

    def _num_seconds(self, dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self):
        return datetime.now()


default_token_generator = PasswordResetTokenGenerator()
