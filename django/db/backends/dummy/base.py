"""
Dummy database backend for Thibaud.

Thibaud uses this if the database ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raise
ImproperlyConfigured.
"""

from thibaud.core.exceptions import ImproperlyConfigured
from thibaud.db.backends.base.base import BaseDatabaseWrapper
from thibaud.db.backends.base.client import BaseDatabaseClient
from thibaud.db.backends.base.creation import BaseDatabaseCreation
from thibaud.db.backends.base.introspection import BaseDatabaseIntrospection
from thibaud.db.backends.base.operations import BaseDatabaseOperations
from thibaud.db.backends.dummy.features import DummyDatabaseFeatures


def complain(*args, **kwargs):
    raise ImproperlyConfigured(
        "settings.DATABASES is improperly configured. "
        "Please supply the ENGINE value. Check "
        "settings documentation for more details."
    )


def ignore(*args, **kwargs):
    pass


class DatabaseOperations(BaseDatabaseOperations):
    quote_name = complain


class DatabaseClient(BaseDatabaseClient):
    runshell = complain


class DatabaseCreation(BaseDatabaseCreation):
    create_test_db = ignore
    destroy_test_db = ignore


class DatabaseIntrospection(BaseDatabaseIntrospection):
    get_table_list = complain
    get_table_description = complain
    get_relations = complain
    get_indexes = complain


class DatabaseWrapper(BaseDatabaseWrapper):
    operators = {}
    # Override the base class implementations with null
    # implementations. Anything that tries to actually
    # do something raises complain; anything that tries
    # to rollback or undo something raises ignore.
    _cursor = complain
    ensure_connection = complain
    _commit = complain
    _rollback = ignore
    _close = ignore
    _savepoint = ignore
    _savepoint_commit = complain
    _savepoint_rollback = ignore
    _set_autocommit = complain
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DummyDatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def is_usable(self):
        return True
