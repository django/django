import hashlib
from datetime import datetime

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    base36_to_int,
    int_to_base36,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)


class PasswordResetTokenGenerator:
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """

    key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"
    algorithm = None
    _secret = None
    _secret_fallbacks = None

    def __init__(self):
        self.algorithm = self.algorithm or "sha256"

    def _get_secret(self):
        return self._secret or settings.SECRET_KEY

    def _set_secret(self, secret):
        self._secret = secret

    secret = property(_get_secret, _set_secret)

    def _get_fallbacks(self):
        if self._secret_fallbacks is None:
            return settings.SECRET_KEY_FALLBACKS
        return self._secret_fallbacks

    def _set_fallbacks(self, fallbacks):
        self._secret_fallbacks = fallbacks

    secret_fallbacks = property(_get_fallbacks, _set_fallbacks)

    def make_token(self, user):
        """
        Return a token that can be used once to do a password reset
        for the given user.
        """
        return self._make_token_with_timestamp(
            user,
            self._num_seconds(self._now()),
            self.secret,
        )

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
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret),
                token,
            ):
                break
        else:
            return False

        # Check the timestamp is within limit.
        if (self._num_seconds(self._now()) - ts) > settings.PASSWORD_RESET_TIMEOUT:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp, secret):
        # timestamp is number of seconds since 2001-1-1. Converted to base 36,
        # this gives us a 6 digit string until about 2069.
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp),
            secret=secret,
            algorithm=self.algorithm,
        ).hexdigest()[
            ::2
        ]  # Limit to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's primary key, email (if available), and some user state
        that's sure to change after a password reset to produce a token that is
        invalidated when it's used:
        1. The password field will change upon a password reset (even if the
           same password is chosen, due to password salting).
        2. The last_login field will usually be updated very shortly after
           a password reset.
        Failing those things, settings.PASSWORD_RESET_TIMEOUT eventually
        invalidates the token.

        Running this data through salted_hmac() prevents password cracking
        attempts using the reset token, provided the secret isn't compromised.
        """
        # Truncate microseconds so that tokens are consistent even if the
        # database doesn't support microseconds.
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, "") or ""
        return f"{user.pk}{user.password}{login_timestamp}{timestamp}{email}"

    def _num_seconds(self, dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self):
        # Used for mocking in tests
        return datetime.now()

    def _xor_encrypt_decrypt(self, uid):
        """
        Performs XOR encryption/decryption on a uid to obfuscate
        its value in the reset link.
        This approach avoids adding a new dependency for encryption,
        which is not natively part of Python's standard library.
        The cypher key is a salted hash of the SECRET_KEY.
        It is important that the cipher key is at least as long as the uid.
        We use the SHA-512 hash algorithm to ensure a long enough cipher key (64 bytes)
        to encrypt UUID4s (36 bytes) that might be used as primary key.
        BigAutoField (the default primary key) is also supported since
        it has a maximum size of 19 bytes. We cycle the key to also support the
        unlikely scenario that the uid is longer than 64 bytes.
        """
        key = hashlib.sha512(force_bytes(f"{self.key_salt}{self.secret}")).digest()
        uid_bytes = force_bytes(uid)
        xor_ciphertext = bytes(
            a ^ b for a, b in zip(uid_bytes, (key * (len(uid_bytes) // len(key) + 1)))
        )
        return xor_ciphertext

    def encrypt_uid(self, uid):
        """
        Returns a XOR-encrypted user id for use in the password reset mechanism.
        """
        xor_ciphertext = self._xor_encrypt_decrypt(uid)
        return urlsafe_base64_encode(xor_ciphertext)

    def decrypt_uid(self, encrypted_uidb64):
        """
        Returns the decrypted user id given the base64-encoded encrypted user id.
        """
        xor_ciphertext = urlsafe_base64_decode(encrypted_uidb64)
        return force_str(self._xor_encrypt_decrypt(xor_ciphertext))


default_token_generator = PasswordResetTokenGenerator()
