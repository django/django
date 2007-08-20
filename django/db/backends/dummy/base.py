"""
Dummy database backend for Django.

Django uses this if the DATABASE_ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raises
ImproperlyConfigured.
"""

from django.core.exceptions import ImproperlyConfigured

def complain(*args, **kwargs):
    raise ImproperlyConfigured, "You haven't set the DATABASE_ENGINE setting yet."

def ignore(*args, **kwargs):
    pass

class DatabaseError(Exception):
    pass

class IntegrityError(DatabaseError):
    pass

class DatabaseOperations(object):
    def __getattr__(self, *args, **kwargs):
        complain()

class DatabaseWrapper(object):
    ops = DatabaseOperations()
    cursor = complain
    _commit = complain
    _rollback = ignore

    def __init__(self, **kwargs):
        pass

    def close(self):
        pass # close()

supports_constraints = False
supports_tablespaces = False

OPERATOR_MAPPING = {}
