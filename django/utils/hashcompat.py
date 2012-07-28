"""
The md5 and sha modules are deprecated since Python 2.5, replaced by the
hashlib module containing both hash algorithms. Here, we provide a common
interface to the md5 and sha constructors, depending on system version.
"""

import warnings
warnings.warn("django.utils.hashcompat is deprecated; use django.utils.tokens.HashToken instead",
              DeprecationWarning)

from django.utils.tokens import HashToken
md5_constructor = HashToken(algorithm='md5').digestmod
md5_hmac = md5_constructor
sha_constructor = HashToken(algorithm='sha1').digestmod
sha_hmac = sha_constructor
