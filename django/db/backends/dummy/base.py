"""
Dummy database backend for Django.

Django uses this if the DATABASE_ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raises
ImproperlyConfigured.
"""

from django.core.exceptions import ImproperlyConfigured
from django.db.backends import BaseDatabaseFeatures, BaseDatabaseOperations

def complain(*args, **kwargs):
    raise ImproperlyConfigured, "You haven't set the DATABASE_ENGINE setting yet."

def ignore(*args, **kwargs):
    pass

class DatabaseError(Exception):
    pass

class IntegrityError(DatabaseError):
    pass

class DatabaseOperations(BaseDatabaseOperations):
    quote_name = complain

class DatabaseWrapper(object):
    features = BaseDatabaseFeatures()
    ops = DatabaseOperations()
    operators = {}
    cursor = complain
    _commit = complain
    _rollback = ignore

    def __init__(self, **kwargs):
        pass

    def close(self):
        pass
