"""
Utilities for providing backwards compatibility for the maxlength argument,
which has been replaced by max_length. See ticket #2101.
"""

from warnings import warn

def get_maxlength(self):
    return self.max_length

def set_maxlength(self, value):
    self.max_length = value

def legacy_maxlength(max_length, maxlength):
    """
    Consolidates max_length and maxlength, providing backwards compatibilty
    for the legacy "maxlength" argument.

    If one of max_length or maxlength is given, then that value is returned.
    If both are given, a TypeError is raised. If maxlength is used at all, a
    deprecation warning is issued.
    """
    if maxlength is not None:
        warn("maxlength is deprecated. Use max_length instead.", DeprecationWarning, stacklevel=3)
        if max_length is not None:
            raise TypeError("Field cannot take both the max_length argument and the legacy maxlength argument.")
        max_length = maxlength
    return max_length

def remove_maxlength(func):
    """
    A decorator to be used on a class's __init__ that provides backwards
    compatibilty for the legacy "maxlength" keyword argument, i.e.
        name = models.CharField(maxlength=20)

    It does this by changing the passed "maxlength" keyword argument
    (if it exists) into a "max_length" keyword argument.
    """
    def inner(self, *args, **kwargs):
        max_length = kwargs.get('max_length', None)
        # pop maxlength because we don't want this going to __init__.
        maxlength = kwargs.pop('maxlength', None)
        max_length = legacy_maxlength(max_length, maxlength)
        # Only set the max_length keyword argument if we got a value back.
        if max_length is not None:
            kwargs['max_length'] = max_length
        func(self, *args, **kwargs)
    return inner

# This metaclass is used in two places, and should be removed when legacy
# support for maxlength is dropped.
#   * oldforms.FormField
#   * db.models.fields.Field

class LegacyMaxlength(type):
    """
    Metaclass for providing backwards compatibility support for the
    "maxlength" keyword argument.
    """
    def __init__(cls, name, bases, attrs):
        super(LegacyMaxlength, cls).__init__(name, bases, attrs)
        # Decorate the class's __init__ to remove any maxlength keyword.
        cls.__init__ = remove_maxlength(cls.__init__)
        # Support accessing and setting to the legacy maxlength attribute.
        cls.maxlength = property(get_maxlength, set_maxlength)
