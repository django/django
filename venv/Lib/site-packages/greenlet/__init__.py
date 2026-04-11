# -*- coding: utf-8 -*-
"""
The root of the greenlet package.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    '__version__',
    '_C_API',

    'GreenletExit',
    'error',

    'getcurrent',
    'greenlet',

    'gettrace',
    'settrace',
]

# pylint:disable=no-name-in-module

###
# Metadata
###
__version__ = '3.3.2'
from ._greenlet import _C_API # pylint:disable=no-name-in-module

###
# Exceptions
###
from ._greenlet import GreenletExit
from ._greenlet import error

###
# greenlets
###
from ._greenlet import getcurrent
from ._greenlet import greenlet

###
# tracing
###
try:
    from ._greenlet import gettrace
    from ._greenlet import settrace
except ImportError:
    # Tracing wasn't supported.
    # XXX: The option to disable it was removed in 1.0,
    # so this branch should be dead code.
    pass

###
# Constants
# These constants aren't documented and aren't recommended.
# In 1.0, USE_GC and USE_TRACING are always true, and USE_CONTEXT_VARS
# is the same as ``sys.version_info[:2] >= 3.7``
###
from ._greenlet import GREENLET_USE_CONTEXT_VARS # pylint:disable=unused-import
from ._greenlet import GREENLET_USE_GC # pylint:disable=unused-import
from ._greenlet import GREENLET_USE_TRACING # pylint:disable=unused-import

# Controlling the use of the gc module. Provisional API for this greenlet
# implementation in 2.0.
from ._greenlet import CLOCKS_PER_SEC # pylint:disable=unused-import
from ._greenlet import enable_optional_cleanup # pylint:disable=unused-import
from ._greenlet import get_clocks_used_doing_optional_cleanup # pylint:disable=unused-import

# Other APIS in the _greenlet module are for test support.
