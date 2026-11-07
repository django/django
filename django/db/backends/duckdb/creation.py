"""
Database creation for DuckDB backend.
"""

import os
from pathlib import Path

from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):
    @staticmethod
    def is_in_memory_db(database_name):
        return database_name == ":memory:" or not database_name

    def _get_test_db_name(self):
        test_database_name = self.connection.settings_dict["TEST"]["NAME"]
        if test_database_name:
            return test_database_name
        database_name = self.connection.settings_dict["NAME"]
        if self.is_in_memory_db(database_name):
            return ":memory:"
        database_path = Path(database_name)
        return str(database_path.with_name(f"test_{database_path.name}"))

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        test_database_name = self._get_test_db_name()
        if not self.is_in_memory_db(test_database_name):
            if os.path.exists(test_database_name) and not keepdb:
                os.remove(test_database_name)
        return test_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        if test_database_name and not self.is_in_memory_db(test_database_name):
            if os.path.exists(test_database_name):
                os.remove(test_database_name)

    def test_db_signature(self):
        test_database_name = self._get_test_db_name()
        sig = [self.connection.settings_dict["NAME"]]
        if self.is_in_memory_db(test_database_name):
            sig.append(self.connection.alias)
        else:
            sig.append(test_database_name)
        return tuple(sig)
