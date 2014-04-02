from __future__ import absolute_import

from inspect import *

from django.utils import six


if six.PY3:
    def getargspec(func):
        """Get the names and default values of a function's arguments.

        A tuple of four things is returned: (args, varargs, varkw, defaults).
        'args' is a list of the argument names.
        'args' will include keyword-only argument names.
        'varargs' and 'varkw' are the names of the * and ** arguments or None.
        'defaults' is an n-tuple of the default values of the last n arguments.

        Safe for use in Python 3, as annotations and keyword arguments are
        ignored.
        """

        args = getfullargspec(func)[:4]
        return ArgSpec(*args)