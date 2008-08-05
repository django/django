"""
The md5 and sha modules are deprecated since Python 2.5, replaced by the
hashlib module containing both hash algorithms. Here, we provide a common
interface to the md5 and sha constructors, preferring the hashlib module when
available.
"""

try:
    import hashlib
    md5_constructor = hashlib.md5
    sha_constructor = hashlib.sha1
except ImportError:
    import md5
    md5_constructor = md5.new
    import sha
    sha_constructor = sha.new
