from django.db.backends.base.creation import BaseAsyncDatabaseCreation
from django.db.backends.sqlite3.creation import (
    DatabaseCreation as SQLiteDatabaseCreation,
)


class DatabaseCreation(BaseAsyncDatabaseCreation, SQLiteDatabaseCreation):
    pass
