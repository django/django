import hashlib

from django.conf import settings
from django.utils import importlib
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_str
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import (
    pbkdf2, constant_time_compare, get_random_string)
from django.utils.translation import ugettext_noop as _


UNUSABLE_PASSWORD = '!'  # This will never be a valid encoded hash
HASHERS = None  # lazily loaded from PASSWORD_HASHERS
PREFERRED_HASHER = None  # defaults to first item in PASSWORD_HASHERS


def is_password_usable(encoded):
    return (encoded is not None and encoded != UNUSABLE_PASSWORD)


def check_password(password, encoded, setter=None, preferred='default'):
    """
    Returns a boolean of whether the raw password matches the three
    part encoded digest.

    If setter is specified, it'll be called when you need to
    regenerate the password.
    """
    if not password or not is_password_usable(encoded):
        return False

    preferred = get_hasher(preferred)
    raw_password = password
    password = smart_str(password)
    encoded = smart_str(encoded)

    if len(encoded) == 32 and '$' not in encoded:
        hasher = get_hasher('unsalted_md5')
    else:
        algorithm = encoded.split('$', 1)[0]
        hasher = get_hasher(algorithm)

    must_update = hasher.algorithm != preferred.algorithm
    is_correct = hasher.verify(password, encoded)
    if setter and is_correct and must_update:
        setter(raw_password)
    return is_correct


def make_password(password, salt=None, hasher='default'):
    """
    Turn a plain-text password into a hash for database storage

    Same as encode() but generates a new random salt.  If
    password is None or blank then UNUSABLE_PASSWORD will be
    returned which disallows logins.
    """
    if not password:
        return UNUSABLE_PASSWORD

    hasher = get_hasher(hasher)
    password = smart_str(password)

    if not salt:
        salt = hasher.salt()
    salt = smart_str(salt)

    return hasher.encode(password, salt)


def load_hashers(password_hashers=None):
    global HASHERS
    global PREFERRED_HASHER
    hashers = []
    if not password_hashers:
        password_hashers = settings.PASSWORD_HASHERS
    for backend in password_hashers:
        try:
            mod_path, cls_name = backend.rsplit('.', 1)
            mod = importlib.import_module(mod_path)
            hasher_cls = getattr(mod, cls_name)
        except (AttributeError, ImportError, ValueError):
            raise ImproperlyConfigured("hasher not found: %s" % backend)
        hasher = hasher_cls()
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
            except ImportError:
                raise ValueError("Couldn't load %s password algorithm "
                                 "library" % name)
            return module
        raise ValueError("Hasher '%s' doesn't specify a library attribute" %
                         self.__class__)

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
        assert password
        assert salt and '$' not in salt
        if not iterations:
            iterations = self.iterations
        hash = pbkdf2(password, salt, iterations, digest=self.digest)
        hash = hash.encode('base64').strip()
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


class BCryptPasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the py-bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """
    algorithm = "bcrypt"
    library = ("py-bcrypt", "bcrypt")
    rounds = 12

    def salt(self):
        bcrypt = self._load_library()
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        bcrypt = self._load_library()
        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, data)

    def verify(self, password, encoded):
        algorithm, data = encoded.split('$', 1)
        assert algorithm == self.algorithm
        bcrypt = self._load_library()
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


class SHA1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    """
    algorithm = "sha1"

    def encode(self, password, salt):
        assert password
        assert salt and '$' not in salt
        hash = hashlib.sha1(salt + password).hexdigest()
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
        assert password
        assert salt and '$' not in salt
        hash = hashlib.md5(salt + password).hexdigest()
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


class UnsaltedMD5PasswordHasher(BasePasswordHasher):
    """
    I am an incredibly insecure algorithm you should *never* use;
    stores unsalted MD5 hashes without the algorithm prefix.

    This class is implemented because Django used to store passwords
    this way. Some older Django installs still have these values
    lingering around so we need to handle and upgrade them properly.
    """
    algorithm = "unsalted_md5"

    def salt(self):
        return ''

    def encode(self, password, salt):
        return hashlib.md5(password).hexdigest()

    def verify(self, password, encoded):
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
        data = crypt.crypt(password, salt)
        # we don't need to store the salt, but Django used to do this
        return "%s$%s$%s" % (self.algorithm, '', data)

    def verify(self, password, encoded):
        crypt = self._load_library()
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return constant_time_compare(data, crypt.crypt(password, data))

    def safe_summary(self, encoded):
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return SortedDict([
            (_('algorithm'), algorithm),
            (_('salt'), salt),
            (_('hash'), mask_hash(data, show=3)),
        ])

