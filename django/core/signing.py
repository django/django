"""
Functions for creating and restoring url-safe signed JSON objects.

The format used looks like this:

>>> signing.dumps("hello")
'ImhlbGxvIg:1QaUZC:YIye-ze3TTx7gtSv422nZA4sgmk'

There are two components here, separated by a ':'. The first component is a
URLsafe base64 encoded JSON of the object passed to dumps(). The second
component is a base64 encoded hmac/SHA1 hash of "$first_component:$secret"

signing.loads(s) checks the signature and returns the deserialised object.
If the signature fails, a BadSignature exception is raised.

>>> signing.loads("ImhlbGxvIg:1QaUZC:YIye-ze3TTx7gtSv422nZA4sgmk")
u'hello'
>>> signing.loads("ImhlbGxvIg:1QaUZC:YIye-ze3TTx7gtSv422nZA4sgmk-modified")
...
BadSignature: Signature failed: ImhlbGxvIg:1QaUZC:YIye-ze3TTx7gtSv422nZA4sgmk-modified

You can optionally compress the JSON prior to base64 encoding it to save
space, using the compress=True argument. This checks if compression actually
helps and only applies compression if the result is a shorter string:

>>> signing.dumps(range(1, 20), compress=True)
'.eJwFwcERACAIwLCF-rCiILN47r-GyZVJsNgkxaFxoDgxcOHGxMKD_T7vhAml:1QaUaL:BA0thEZrp4FQVXIXuOvYJtLJSrQ'

The fact that the string is compressed is signalled by the prefixed '.' at the
start of the base64 JSON.

There are 65 url-safe characters: the 64 used by url-safe base64 and the ':'.
These functions make use of all of them.
"""

from __future__ import unicode_literals

import base64
import json
import time
import zlib

from django.conf import settings
from django.utils import baseconv
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.encoding import force_bytes, force_str, force_text
from django.utils.module_loading import import_by_path


class BadSignature(Exception):
    """
    Signature does not match
    """
    pass


class SignatureExpired(BadSignature):
    """
    Signature timestamp is older than required max_age
    """
    pass


def b64_encode(s):
    return base64.urlsafe_b64encode(s).strip(b'=')


def b64_decode(s):
    pad = b'=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def base64_hmac(salt, value, key):
    return b64_encode(salted_hmac(salt, value, key).digest())


def get_cookie_signer(salt='django.core.signing.get_cookie_signer'):
    Signer = import_by_path(settings.SIGNING_BACKEND)
    return Signer('django.http.cookies' + settings.SECRET_KEY, salt=salt)


class JSONSerializer(object):
    """
    Simple wrapper around json to be used in signing.dumps and
    signing.loads.
    """
    def dumps(self, obj):
        return json.dumps(obj, separators=(',', ':')).encode('latin-1')

    def loads(self, data):
        return json.loads(data.decode('latin-1'))


def dumps(obj, key=None, salt='django.core.signing', serializer=JSONSerializer, compress=False):
    """
    Returns URL-safe, sha1 signed base64 compressed JSON string. If key is
    None, settings.SECRET_KEY is used instead.

    If compress is True (not the default) checks if compressing using zlib can
    save some space. Prepends a '.' to signify compression. This is included
    in the signature, to protect against zip bombs.

    Salt can be used to namespace the hash, so that a signed string is
    only valid for a given namespace. Leaving this at the default
    value or re-using a salt value across different parts of your
    application without good cause is a security risk.

    The serializer is expected to return a bytestring.
    """
    data = serializer().dumps(obj)

    # Flag for if it's been compressed or not
    is_compressed = False

    if compress:
        # Avoid zlib dependency unless compress is being used
        compressed = zlib.compress(data)
        if len(compressed) < (len(data) - 1):
            data = compressed
            is_compressed = True
    base64d = b64_encode(data)
    if is_compressed:
        base64d = b'.' + base64d
    return TimestampSigner(key, salt=salt).sign(base64d)


def loads(s, key=None, salt='django.core.signing', serializer=JSONSerializer, max_age=None):
    """
    Reverse of dumps(), raises BadSignature if signature fails.

    The serializer is expected to accept a bytestring.
    """
    # TimestampSigner.unsign always returns unicode but base64 and zlib
    # compression operate on bytes.
    base64d = force_bytes(TimestampSigner(key, salt=salt).unsign(s, max_age=max_age))
    decompress = False
    if base64d[:1] == b'.':
        # It's compressed; uncompress it first
        base64d = base64d[1:]
        decompress = True
    data = b64_decode(base64d)
    if decompress:
        data = zlib.decompress(data)
    return serializer().loads(data)


class Signer(object):

    def __init__(self, key=None, sep=':', salt=None):
        # Use of native strings in all versions of Python
        self.sep = str(sep)
        self.key = str(key or settings.SECRET_KEY)
        self.salt = str(salt or
            '%s.%s' % (self.__class__.__module__, self.__class__.__name__))

    def signature(self, value):
        signature = base64_hmac(self.salt + 'signer', value, self.key)
        # Convert the signature from bytes to str only on Python 3
        return force_str(signature)

    def sign(self, value):
        value = force_str(value)
        return str('%s%s%s') % (value, self.sep, self.signature(value))

    def unsign(self, signed_value):
        signed_value = force_str(signed_value)
        if not self.sep in signed_value:
            raise BadSignature('No "%s" found in value' % self.sep)
        value, sig = signed_value.rsplit(self.sep, 1)
        if constant_time_compare(sig, self.signature(value)):
            return force_text(value)
        raise BadSignature('Signature "%s" does not match' % sig)


class TimestampSigner(Signer):

    def timestamp(self):
        return baseconv.base62.encode(int(time.time()))

    def sign(self, value):
        value = force_str(value)
        value = str('%s%s%s') % (value, self.sep, self.timestamp())
        return super(TimestampSigner, self).sign(value)

    def unsign(self, value, max_age=None):
        result =  super(TimestampSigner, self).unsign(value)
        value, timestamp = result.rsplit(self.sep, 1)
        timestamp = baseconv.base62.decode(timestamp)
        if max_age is not None:
            # Check timestamp is not older than max_age
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired(
                    'Signature age %s > %s seconds' % (age, max_age))
        return value
