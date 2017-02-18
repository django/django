"""
Django's standard crypto functions and utilities.
"""
from __future__ import unicode_literals

import binascii
import hashlib
import hmac
import random
import struct
import time

from django.conf import settings
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.six.moves import range

# Use the system PRNG if possible
try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    import warnings
    warnings.warn('A secure pseudo-random number generator is not available '
                  'on your system. Falling back to Mersenne Twister.')
    using_sysrandom = False


def salted_hmac(key_salt, value, secret=None):
    """
    Returns the HMAC-SHA1 of 'value', using a key generated from key_salt and a
    secret (which defaults to settings.SECRET_KEY).

    A different key_salt should be passed in for every application of HMAC.
    """
    if secret is None:
        secret = settings.SECRET_KEY

    key_salt = force_bytes(key_salt)
    secret = force_bytes(secret)

    # We need to generate a derived key from our base key.  We can do this by
    # passing the key_salt and our base key through a pseudo-random function and
    # SHA1 works nicely.
    key = hashlib.sha1(key_salt + secret).digest()

    # If len(key_salt + secret) > sha_constructor().block_size, the above
    # line is redundant and could be replaced by key = key_salt + secret, since
    # the hmac module does the same thing for keys longer than the block size.
    # However, we need to ensure that we *always* do this.
    return hmac.new(key, msg=force_bytes(value), digestmod=hashlib.sha1)


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            hashlib.sha256(
                ("%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    settings.SECRET_KEY)).encode('utf-8')
            ).digest())
    return ''.join(random.choice(allowed_chars) for i in range(length))


if hasattr(hmac, "compare_digest"):
    # Prefer the stdlib implementation, when available.
    def constant_time_compare(val1, val2):
        return hmac.compare_digest(force_bytes(val1), force_bytes(val2))
else:
    def constant_time_compare(val1, val2):
        """
        Returns True if the two strings are equal, False otherwise.

        The time taken is independent of the number of characters that match.

        For the sake of simplicity, this function executes in constant time only
        when the two strings have the same length. It short-circuits when they
        have different lengths. Since Django only uses it to compare hashes of
        known expected length, this is acceptable.
        """
        if len(val1) != len(val2):
            return False
        result = 0
        if six.PY3 and isinstance(val1, bytes) and isinstance(val2, bytes):
            for x, y in zip(val1, val2):
                result |= x ^ y
        else:
            for x, y in zip(val1, val2):
                result |= ord(x) ^ ord(y)
        return result == 0


def _bin_to_long(x):
    """
    Convert a binary string into a long integer

    This is a clever optimization for fast xor vector math
    """
    return int(binascii.hexlify(x), 16)


def _long_to_bin(x, hex_format_string):
    """
    Convert a long integer into a binary string.
    hex_format_string is like "%020x" for padding 10 characters.
    """
    return binascii.unhexlify((hex_format_string % x).encode('ascii'))


if hasattr(hashlib, "pbkdf2_hmac"):
    def pbkdf2(password, salt, iterations, dklen=0, digest=None):
        """
        Implements PBKDF2 with the same API as Django's existing
        implementation, using the stdlib.

        This is used in Python 2.7.8+ and 3.4+.
        """
        if digest is None:
            digest = hashlib.sha256
        if not dklen:
            dklen = None
        password = force_bytes(password)
        salt = force_bytes(salt)
        return hashlib.pbkdf2_hmac(
            digest().name, password, salt, iterations, dklen)
else:
    def pbkdf2(password, salt, iterations, dklen=0, digest=None):
        """
        Implements PBKDF2 as defined in RFC 2898, section 5.2

        HMAC+SHA256 is used as the default pseudo random function.

        As of 2014, 100,000 iterations was the recommended default which took
        100ms on a 2.7Ghz Intel i7 with an optimized implementation. This is
        probably the bare minimum for security given 1000 iterations was
        recommended in 2001. This code is very well optimized for CPython and
        is about five times slower than OpenSSL's implementation. Look in
        django.contrib.auth.hashers for the present default, it is lower than
        the recommended 100,000 because of the performance difference between
        this and an optimized implementation.
        """
        assert iterations > 0
        if not digest:
            digest = hashlib.sha256
        password = force_bytes(password)
        salt = force_bytes(salt)
        hlen = digest().digest_size
        if not dklen:
            dklen = hlen
        if dklen > (2 ** 32 - 1) * hlen:
            raise OverflowError('dklen too big')
        l = -(-dklen // hlen)
        r = dklen - (l - 1) * hlen

        hex_format_string = "%%0%ix" % (hlen * 2)

        inner, outer = digest(), digest()
        if len(password) > inner.block_size:
            password = digest(password).digest()
        password += b'\x00' * (inner.block_size - len(password))
        inner.update(password.translate(hmac.trans_36))
        outer.update(password.translate(hmac.trans_5C))

        def F(i):
            u = salt + struct.pack(b'>I', i)
            result = 0
            for j in range(int(iterations)):
                dig1, dig2 = inner.copy(), outer.copy()
                dig1.update(u)
                dig2.update(dig1.digest())
                u = dig2.digest()
                result ^= _bin_to_long(u)
            return _long_to_bin(result, hex_format_string)

        T = [F(x) for x in range(1, l)]
        return b''.join(T) + F(l)[:r]
