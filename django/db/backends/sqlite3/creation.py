import os
import sys

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.creation import BaseDatabaseCreation
from django.utils.six.moves import input


class DatabaseCreation(BaseDatabaseCreation):

    def sql_for_pending_references(self, model, style, pending_references):
        "SQLite3 doesn't support constraints"
        return []

    def sql_remove_table_constraints(self, model, references_to_delete, style):
        "SQLite3 doesn't support constraints"
        return []

    def _get_test_db_name(self):
        test_database_name = self.connection.settings_dict['TEST']['NAME']
        can_share_in_memory_db = self.connection.features.can_share_in_memory_db
        if test_database_name and test_database_name != ':memory:':
            if 'mode=memory' in test_database_name and not can_share_in_memory_db:
                raise ImproperlyConfigured(
                    "Using a shared memory database with `mode=memory` in the "
                    "database name is not supported in your environment, "
                    "use `:memory:` instead."
                )
            return test_database_name
        if can_share_in_memory_db:
            return 'file:memorydb_%s?mode=memory&cache=shared' % self.connection.alias
        return ':memory:'

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        test_database_name = self._get_test_db_name()

        if keepdb:
            return test_database_name
        if not self.connection.is_in_memory_db(test_database_name):
            # Erase the old test database
            if verbosity >= 1:
                print("Destroying old test database '%s'..." % self.connection.alias)
            if os.access(test_database_name, os.F_OK):
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name
                    )
                if autoclobber or confirm == 'yes':
                    try:
                        os.remove(test_database_name)
                    except Exception as e:
                        sys.stderr.write("Got an error deleting the old test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)
        return test_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        if test_database_name and not self.connection.is_in_memory_db(test_database_name):
            # Remove the SQLite database file
            os.remove(test_database_name)

    def test_db_signature(self):
        """
        Returns a tuple that uniquely identifies a test database.

        This takes into account the special cases of ":memory:" and "" for
        SQLite since the databases will be distinct despite having the same
        TEST NAME. See http://www.sqlite.org/inmemorydb.html
        """
        test_database_name = self._get_test_db_name()
        sig = [self.connection.settings_dict['NAME']]
        if self.connection.is_in_memory_db(test_database_name):
            sig.append(self.connection.alias)
        return tuple(sig)
