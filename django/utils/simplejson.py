# Django 1.5 only supports Python >= 2.6, where the standard library includes
# the json module. Previous version of Django shipped a copy for Python < 2.6.

# For backwards compatibility, we're keeping an importable json module
# at this location, with the same lookup sequence.

# Avoid shadowing the simplejson module
from __future__ import absolute_import

import warnings
warnings.warn("django.utils.simplejson is deprecated; use json instead.",
              PendingDeprecationWarning)

try:
    import simplejson
except ImportError:
    use_simplejson = False
else:
    # The system-installed version has priority providing it is either not an
    # earlier version or it contains the C speedups.
    from json import __version__ as stdlib_json_version
    use_simplejson = (hasattr(simplejson, '_speedups') or
        simplejson.__version__.split('.') >= stdlib_json_version.split('.'))

# Make sure we copy over the version. See #17071
if use_simplejson:
    from simplejson import *
    from simplejson import __version__
else:
    from json import *
    from json import __version__
