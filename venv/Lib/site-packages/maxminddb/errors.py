"""Typed errors thrown by this library."""


class InvalidDatabaseError(RuntimeError):
    """An error thrown when unexpected data is found in the database."""
