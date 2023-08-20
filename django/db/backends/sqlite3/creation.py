import multiprocessing
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from django.db import NotSupportedError
from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):
    @staticmethod
    def is_in_memory_db(database_name):
        return not isinstance(database_name, Path) and (
            database_name == ":memory:" or "mode=memory" in database_name
        )

    def _get_test_db_name(self):
        test_database_name = self.connection.settings_dict["TEST"]["NAME"] or ":memory:"
        if test_database_name == ":memory:":
            return "file:memorydb_%s?mode=memory&cache=shared" % self.connection.alias
        return test_database_name

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        test_database_name = self._get_test_db_name()

        if keepdb:
            return test_database_name
        if not self.is_in_memory_db(test_database_name):
            # Erase the old test database
            if verbosity >= 1:
                self.log(
                    "Destroying old test database for alias %s..."
                    % (self._get_database_display_str(verbosity, test_database_name),)
                )
            if os.access(test_database_name, os.F_OK):
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name
                    )
                if autoclobber or confirm == "yes":
                    try:
                        os.remove(test_database_name)
                    except Exception as e:
                        self.log("Got an error deleting the old test database: %s" % e)
                        sys.exit(2)
                else:
                    self.log("Tests cancelled.")
                    sys.exit(1)
        return test_database_name

    def get_test_db_clone_settings(self, suffix):
        orig_settings_dict = self.connection.settings_dict
        source_database_name = orig_settings_dict["NAME"] or ":memory:"

        if not self.is_in_memory_db(source_database_name):
            root, ext = os.path.splitext(source_database_name)
            return {**orig_settings_dict, "NAME": f"{root}_{suffix}{ext}"}

        start_method = multiprocessing.get_start_method()
        if start_method == "fork":
            return orig_settings_dict
        if start_method == "spawn":
            return {
                **orig_settings_dict,
                "NAME": f"{self.connection.alias}_{suffix}.sqlite3",
            }
        raise NotSupportedError(
            f"Cloning with start method {start_method!r} is not supported."
        )

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict["NAME"]
        target_database_name = self.get_test_db_clone_settings(suffix)["NAME"]
        if not self.is_in_memory_db(source_database_name):
            # Erase the old test database
            if os.access(target_database_name, os.F_OK):
                if keepdb:
                    return
                if verbosity >= 1:
                    self.log(
                        "Destroying old test database for alias %s..."
                        % (
                            self._get_database_display_str(
                                verbosity, target_database_name
                            ),
                        )
                    )
                try:
                    os.remove(target_database_name)
                except Exception as e:
                    self.log("Got an error deleting the old test database: %s" % e)
                    sys.exit(2)
            try:
                shutil.copy(source_database_name, target_database_name)
            except Exception as e:
                self.log("Got an error cloning the test database: %s" % e)
                sys.exit(2)
        # Forking automatically makes a copy of an in-memory database.
        # Spawn requires migrating to disk which will be re-opened in
        # setup_worker_connection.
        elif multiprocessing.get_start_method() == "spawn":
            ondisk_db = sqlite3.connect(target_database_name, uri=True)
            self.connection.connection.backup(ondisk_db)
            ondisk_db.close()

    def _destroy_test_db(self, test_database_name, verbosity):
        if test_database_name and not self.is_in_memory_db(test_database_name):
            # Remove the SQLite database file
            os.remove(test_database_name)

    def test_db_signature(self):
        """
        Return a tuple that uniquely identifies a test database.

        This takes into account the special cases of ":memory:" and "" for
        SQLite since the databases will be distinct despite having the same
        TEST NAME. See https://www.sqlite.org/inmemorydb.html
        """
        test_database_name = self._get_test_db_name()
        sig = [self.connection.settings_dict["NAME"]]
        if self.is_in_memory_db(test_database_name):
            sig.append(self.connection.alias)
        else:
            sig.append(test_database_name)
        return tuple(sig)

    def setup_worker_connection(self, _worker_id):
        settings_dict = self.get_test_db_clone_settings(_worker_id)
        # connection.settings_dict must be updated in place for changes to be
        # reflected in django.db.connections. Otherwise new threads would
        # connect to the default database instead of the appropriate clone.
        start_method = multiprocessing.get_start_method()
        if start_method == "fork":
            # Update settings_dict in place.
            self.connection.settings_dict.update(settings_dict)
            self.connection.close()
        elif start_method == "spawn":
            alias = self.connection.alias
            connection_str = (
                f"file:memorydb_{alias}_{_worker_id}?mode=memory&cache=shared"
            )
            source_db = self.connection.Database.connect(
                f"file:{alias}_{_worker_id}.sqlite3", uri=True
            )
            target_db = sqlite3.connect(connection_str, uri=True)
            source_db.backup(target_db)
            source_db.close()
            # Update settings_dict in place.
            self.connection.settings_dict.update(settings_dict)
            self.connection.settings_dict["NAME"] = connection_str
            # Re-open connection to in-memory database before closing copy
            # connection.
            self.connection.connect()
            target_db.close()
            if os.environ.get("RUNNING_DJANGOS_TEST_SUITE") == "true":
                self.mark_expected_failures_and_skips()
