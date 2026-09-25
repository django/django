class GEOSException(Exception):
    "The base GEOS exception, indicates a GEOS-related error."

    pass


class GEOSLibraryError(Exception):
    """Error raised by the GEOS C library."""

    pass
