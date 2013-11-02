"""
 This module houses the GEOS exceptions, specifically, GEOSException and
 GEOSGeometryIndexError.
"""


class GEOSException(Exception):
    "The base GEOS exception, indicates a GEOS-related error."
    pass


class GEOSIndexError(GEOSException, KeyError):
    """
    This exception is raised when an invalid index is encountered, and has
    the 'silent_variable_feature' attribute set to true.  This ensures that
    django's templates proceed to use the next lookup type gracefully when
    an Exception is raised.  Fixes ticket #4740.
    """
    # "If, during the method lookup, a method raises an exception, the exception
    #  will be propagated, unless the exception has an attribute
    #  `silent_variable_failure` whose value is True." -- Django template docs.
    silent_variable_failure = True
