from __future__ import unicode_literals

import base64
import binascii
import hashlib

from django.dispatch import receiver
from django.conf import settings
from django.test.signals import setting_changed
from django.utils import importlib
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_bytes, force_str, force_text
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import (
    pbkdf2, constant_time_compare, get_random_string)
from django.utils.module_loading import import_by_path
from django.utils.translation import ugettext_noop as _


UNUSABLE_PASSWORD_PREFIX = '!'  # This will never be a valid encoded hash
UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40  # number of random chars to add after UNUSABLE_PASSWORD_PREFIX
HASHERS = None  # lazily loaded from PASSWORD_HASHERS
PREFERRED_HASHER = None  # defaults to first item in PASSWORD_HASHERS


@receiver(setting_changed)
def reset_hashers(**kwargs):
    if kwargs['setting'] == 'PASSWORD_HASHERS':
        global HASHERS, PREFERRED_HASHER
        HASHERS = None
        PREFERRED_HASHER = None


def is_password_usable(encoded):
    if encoded is None or encoded.startswith(UNUSABLE_PASSWORD_PREFIX):
        return False
    try:
        identify_hasher(encoded)
    except ValueError:
        return False
    return True


def check_password(password, encoded, setter=None, preferred='default'):
    """
    Returns a boolean of whether the raw password matches the three
    part encoded digest.

    If setter is specified, it'll be called when you need to
    regenerate the password.
    """
    if password is None or not is_password_usable(encoded):
        return False

    preferred = get_hasher(preferred)
    hasher = identify_hasher(encoded)

    must_update = hasher.algorithm != preferred.algorithm
    is_correct = hasher.verify(password, encoded)
    if setter and is_correct and must_update:
        setter(password)
    return is_correct


def make_password(password, salt=None, hasher='default'):
    """
    Turn a plain-text password into a hash for database storage

    Same as encode() but generates a new random salt.
    If password is None then a concatenation of
    UNUSABLE_PASSWORD_PREFIX and a random string will be returned
    which disallows logins. Additional random string reduces chances
    of gaining access to staff or superuser accounts.
    See ticket #20079 for more info.
    """
    if password is None:
        return UNUSABLE_PASSWORD_PREFIX + get_random_string(UNUSABLE_PASSWORD_SUFFIX_LENGTH)
    hasher = get_hasher(hasher)

    if not salt:
        salt = hasher.salt()

    return hasher.encode(password, salt)


def load_hashers(password_hashers=None):
    global HASHERS
    global PREFERRED_HASHER
    hashers = []
    if not password_hashers:
        password_hashers = settings.PASSWORD_HASHERS
    for backend in password_hashers:
        hasher = import_by_path(backend)()
        if not getattr(hasher, 'algorithm'):
            raise ImproperlyConfigured("hasher doesn't specify an "
                                       "algorithm name: %s" % backend)
        hashers.append(hasher)
    HASHERS = dict([(hasher.algorithm, hasher) for hasher in hashers])
    PREFERRED_HASHER = hashers[0]


def get_hasher(algorithm='default'):
    """
    Returns an instance of a loaded password hasher.

    If algorithm is 'default', the default hasher will be returned.
    This function will also lazy import hashers specified in your
    settings file if needed.
    """
    if hasattr(algorithm, 'algorithm'):
        return algorithm

    elif algorithm == 'default':
        if PREFERRED_HASHER is None:
            load_hashers()
        return PREFERRED_HASHER
    else:
        if HASHERS is None:
            load_hashers()
        if algorithm not in HASHERS:
            raise ValueError("Unknown password hashing algorithm '%s'. "
                             "Did you specify it in the PASSWORD_HASHERS "
                             "setting?" % algorithm)
        return HASHERS[algorithm]


def identify_hasher(encoded):
    """
    Returns an instance of a loaded password hasher.

    Identifies hasher algorithm by examining encoded hash, and calls
    get_hasher() to return hasher. Raises ValueError if
    algorithm cannot be identified, or if hasher is not loaded.
    """
    # Ancient versions of Django created plain MD5 passwords and accepted
    # MD5 passwords with an empty salt.
    if ((len(encoded) == 32 and '$' not in encoded) or
            (len(encoded) == 37 and encoded.startswith('md5$$'))):
        algorithm = 'unsalted_md5'
    # Ancient versions of Django accepted SHA1 passwords with an empty salt.
    elif len(encoded) == 46 and encoded.startswith('sha1$$'):
        algorithm = 'unsalted_sha1'
    else:
        algorithm = encoded.split('$', 1)[0]
    return get_hasher(algorithm)


def mask_hash(hash, show=6, char="*"):
    """
    Returns the given hash, with only the first ``show`` number shown. The
    rest are masked with ``char`` for security reasons.
    """
    masked = hash[:show]
    masked += char * len(hash[show:])
    return masked


class BasePasswordHasher(object):
    """
    Abstract base class for password hashers

    When creating your own hasher, you need to override algorithm,
    verify(), encode() and safe_summary().

    PasswordHasher objects are immutable.
    """
    algorithm = None
    library = None

    def _load_library(self):
        if self.library is not None:
            if isinstance(self.library, (tuple, list)):
                name, mod_path = self.library
            else:
                name = mod_path = self.library
            try:
                module = importlib.import_module(mod_path)
            except ImportError as e:
                raise ValueError("Couldn't load %r algorithm library: %s" %
                                 (self.__class__.__name__, e))
            return module
        raise ValueError("Hasher %r doesn't specify a library attribute" %
                         self.__class__.__name__)

    def salt(self):
        """
        Generates a cryptographically secure nonce salt in ascii
        """
        return get_random_string()

    def verify(self, password, encoded):
        """
        Checks if the given password is correct
        """
        raise NotImplementedError()

    def encode(self, password, salt):
        """
        Creates an encoded database value

        The result is normally formatted as "algorithm$salt$hash" and
        must be fewer than 128 characters.
        """
        raise NotImplementedError()

    def safe_summary(self, encoded):
        """
        Returns a summary of safe values

        The result is a dictionary and will be used where the password field
        must be displayed to construct a safe representation of the password.
        """
        raise NotImplementedError()


class PBKDF2PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the PBKDF2 algorithm (recommended)

    Configured to use PBKDF2 + HMAC + SHA256 with 10000 iterations.
    The result is a 64 byte binary string.  Iterations may be changed
    safely but you must rename the algorithm if you change SHA256.
    """
    algorithm = "pbkdf2_sha256"
    iterations = 10000
    digest = hashlib.sha256

    def encode(self, password, salt, iterations=None):
        assert password is not None
        assert salt and '$' not in salt
        if not iterations:
            iterations = self.iterations
        hash = pbkdf2(password, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode('ascii').strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)

    def verify(self, password, encoded):
        algorithm, iterations, salt, hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, iterations, salt, hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('iterations'), iterations),
            (_('salt'), mask_hash(salt)),
            (_('hash'), mask_hash(hash)),
        ])


class PBKDF2SHA1PasswordHasher(PBKDF2PasswordHasher):
    """
    Alternate PBKDF2 hasher which uses SHA1, the default PRF
    recommended by PKCS #5. This is compatible with other
    implementations of PBKDF2, such as openssl's
    PKCS5_PBKDF2_HMAC_SHA1().
    """
    algorithm = "pbkdf2_sha1"
    digest = hashlib.sha1


class BCryptSHA256PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """
    algorithm = "bcrypt_sha256"
    digest = hashlib.sha256
    library = ("bcrypt", "bcrypt")
    rounds = 12

    def salt(self):
        bcrypt = self._load_library()
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        bcrypt = self._load_library()
        # Need to reevaluate the force_bytes call once bcrypt is supported on
        # Python 3

        # Hash the password prior to using bcrypt to prevent password truncation
        #   See: https://code.djangoproject.com/ticket/20138
        if self.digest is not None:
            # We use binascii.hexlify here because Python3 decided that a hex encoded
            #   bytestring is somehow a unicode.
            password = binascii.hexlify(self.digest(force_bytes(password)).digest())
        else:
            password = force_bytes(password)

        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, force_text(data))

    def verify(self, password, encoded):
        algorithm, data = encoded.split('$', 1)
        assert algorithm == self.algorithm
        bcrypt = self._load_library()

        # Hash the password prior to using bcrypt to prevent password truncation
        #   See: https://code.djangoproject.com/ticket/20138
        if self.digest is not None:
            # We use binascii.hexlify here because Python3 decided that a hex encoded
            #   bytestring is somehow a unicode.
            password = binascii.hexlify(self.digest(force_bytes(password)).digest())
        else:
            password = force_bytes(password)

        # Ensure that our data is a bytestring
        data = force_bytes(data)

        return constant_time_compare(data, bcrypt.hashpw(password, data))

    def safe_summary(self, encoded):
        algorithm, empty, algostr, work_factor, data = encoded.split('$', 4)
        assert algorithm == self.algorithm
        salt, checksum = data[:22], data[22:]
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('work factor'), work_factor),
            (_('salt'), mask_hash(salt)),
            (_('checksum'), mask_hash(checksum)),
        ])


class BCryptPasswordHasher(BCryptSHA256PasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.

    This hasher does not first hash the password which means it is subject to
    the 72 character bcrypt password truncation, most use cases should prefer
    the BCryptSha512PasswordHasher.

    See: https://code.djangoproject.com/ticket/20138
    """
    algorithm = "bcrypt"
    digest = None


class SHA1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    """
    algorithm = "sha1"

    def encode(self, password, salt):
        assert password is not None
        assert salt and '$' not in salt
        hash = hashlib.sha1(force_bytes(salt + password)).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('salt'), mask_hash(salt, show=2)),
            (_('hash'), mask_hash(hash)),
        ])


class MD5PasswordHasher(BasePasswordHasher):
    """
    The Salted MD5 password hashing algorithm (not recommended)
    """
    algorithm = "md5"

    def encode(self, password, salt):
        assert password is not None
        assert salt and '$' not in salt
        hash = hashlib.md5(force_bytes(salt + password)).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('salt'), mask_hash(salt, show=2)),
            (_('hash'), mask_hash(hash)),
        ])


class UnsaltedSHA1PasswordHasher(BasePasswordHasher):
    """
    Very insecure algorithm that you should *never* use; stores SHA1 hashes
    with an empty salt.

    This class is implemented because Django used to accept such password
    hashes. Some older Django installs still have these values lingering
    around so we need to handle and upgrade them properly.
    """
    algorithm = "unsalted_sha1"

    def salt(self):
        return ''

    def encode(self, password, salt):
        assert salt == ''
        hash = hashlib.sha1(force_bytes(password)).hexdigest()
        return 'sha1$$%s' % hash

    def verify(self, password, encoded):
        encoded_2 = self.encode(password, '')
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        assert encoded.startswith('sha1$$')
        hash = encoded[6:]
        return SortedDict([
            (_('algorithm'), self.algorithm),
            (_('hash'), mask_hash(hash)),
        ])


class UnsaltedMD5PasswordHasher(BasePasswordHasher):
    """
    Incredibly insecure algorithm that you should *never* use; stores unsalted
    MD5 hashes without the algorithm prefix, also accepts MD5 hashes with an
    empty salt.

    This class is implemented because Django used to store passwords this way
    and to accept such password hashes. Some older Django installs still have
    these values lingering around so we need to handle and upgrade them
    properly.
    """
    algorithm = "unsalted_md5"

    def salt(self):
        return ''

    def encode(self, password, salt):
        assert salt == ''
        return hashlib.md5(force_bytes(password)).hexdigest()

    def verify(self, password, encoded):
        if len(encoded) == 37 and encoded.startswith('md5$$'):
            encoded = encoded[5:]
        encoded_2 = self.encode(password, '')
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        return SortedDict([
            (_('algorithm'), self.algorithm),
            (_('hash'), mask_hash(encoded, show=3)),
        ])


class CryptPasswordHasher(BasePasswordHasher):
    """
    Password hashing using UNIX crypt (not recommended)

    The crypt module is not supported on all platforms.
    """
    algorithm = "crypt"
    library = "crypt"

    def salt(self):
        return get_random_string(2)

    def encode(self, password, salt):
        crypt = self._load_library()
        assert len(salt) == 2
        data = crypt.crypt(force_str(password), salt)
        # we don't need to store the salt, but Django used to do this
        return "%s$%s$%s" % (self.algorithm, '', data)

    def verify(self, password, encoded):
        crypt = self._load_library()
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return constant_time_compare(data, crypt.crypt(force_str(password), data))

    def safe_summary(self, encoded):
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('salt'), salt),
            (_('hash'), mask_hash(data, show=3)),
        ])

