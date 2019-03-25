"""
maxminddb.errors
~~~~~~~~~~~~~~~~

This module contains custom errors for the MaxMind DB reader
"""


class InvalidDatabaseError(RuntimeError):
    """This error is thrown when unexpected data is found in the database."""
