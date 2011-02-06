"""
Dummy database backend for Django.

Django uses this if the database ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raises
ImproperlyConfigured.
"""

from django.core.exceptions import ImproperlyConfigured
from django.db.backends import *
from django.db.backends.creation import BaseDatabaseCreation

def complain(*args, **kwargs):
    raise ImproperlyConfigured("You haven't set the database ENGINE setting yet.")

def ignore(*args, **kwargs):
    pass

class DatabaseError(Exception):
    pass

class IntegrityError(DatabaseError):
    pass

class DatabaseOperations(BaseDatabaseOperations):
    quote_name = complain

class DatabaseClient(BaseDatabaseClient):
    runshell = complain

class DatabaseIntrospection(BaseDatabaseIntrospection):
    get_table_list = complain
    get_table_description = complain
    get_relations = complain
    get_indexes = complain

class DatabaseWrapper(object):
    operators = {}
    cursor = complain
    _commit = complain
    _rollback = ignore

    def __init__(self, settings_dict, alias, *args, **kwargs):
        self.features = BaseDatabaseFeatures(self)
        self.ops = DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = BaseDatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

        self.settings_dict = settings_dict
        self.alias = alias

        self.transaction_state = []
        self.savepoint_state = 0
        self.dirty = None

    def close(self):
        pass
