"""
The md5 and sha modules are deprecated since Python 2.5, replaced by the
hashlib module containing both hash algorithms. Here, we provide a common
interface to the md5 and sha constructors, depending on system version.
"""

import warnings
warnings.warn("django.utils.hashcompat is deprecated; use hashlib instead",
              DeprecationWarning)

import hashlib
md5_constructor = hashlib.md5
md5_hmac = md5_constructor
sha_constructor = hashlib.sha1
sha_hmac = sha_constructor
