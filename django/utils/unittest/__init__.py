import sys

#Django hackery to load the appropriate version of unittest

if sys.version_info >= (2,7):
    #unittest2 features are native in Python 2.7
    from unittest import *
else:
    try:
        #check the system path first
        from unittest2 import *
    except ImportError:
        #otherwise fall back to our bundled version
        from unittest2_package_init import *
