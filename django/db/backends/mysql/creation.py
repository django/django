import os
import subprocess
import sys

from django.db.backends.base.creation import BaseDatabaseCreation

from .client import DatabaseClient


class DatabaseCreation(BaseDatabaseCreation):
    def sql_table_creation_suffix(self):
        suffix = []
        test_settings = self.connection.settings_dict["TEST"]
        if test_settings["CHARSET"]:
            suffix.append("CHARACTER SET %s" % test_settings["CHARSET"])
        if test_settings["COLLATION"]:
            suffix.append("COLLATE %s" % test_settings["COLLATION"])
        return " ".join(suffix)

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        try:
            super()._execute_create_test_db(cursor, parameters, keepdb)
        except Exception as e:
            if len(e.args) < 1 or e.args[0] != 1007:
                # All errors except "database exists" (1007) cancel tests.
                self.log("Got an error creating the test database: %s" % e)
                sys.exit(2)
            else:
                raise

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict["NAME"]
        target_database_name = self.get_test_db_clone_settings(suffix)["NAME"]
        test_db_params = {
            "dbname": self.connection.ops.quote_name(target_database_name),
            "suffix": self.sql_table_creation_suffix(),
        }
        with self._nodb_cursor() as cursor:
            try:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
            except Exception:
                if keepdb:
                    # If the database should be kept, skip everything else.
                    return
                try:
                    if verbosity >= 1:
                        self.log(
                            "Destroying old test database for alias %s..."
                            % (
                                self._get_database_display_str(
                                    verbosity, target_database_name
                                ),
                            )
                        )
                    cursor.execute("DROP DATABASE %(dbname)s" % test_db_params)
                    self._execute_create_test_db(cursor, test_db_params, keepdb)
                except Exception as e:
                    self.log("Got an error recreating the test database: %s" % e)
                    sys.exit(2)
        self._clone_db(source_database_name, target_database_name)

    def _clone_db(self, source_database_name, target_database_name):
        cmd_args, cmd_env = DatabaseClient.settings_to_cmd_args_env(
            self.connection.settings_dict, []
        )
        dump_cmd = [
            "mysqldump",
            *cmd_args[1:-1],
            "--routines",
            "--events",
            source_database_name,
        ]
        dump_env = load_env = {**os.environ, **cmd_env} if cmd_env else None
        load_cmd = cmd_args
        load_cmd[-1] = target_database_name

        with subprocess.Popen(
            dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dump_env
        ) as dump_proc:
            with subprocess.Popen(
                load_cmd,
                stdin=dump_proc.stdout,
                stdout=subprocess.DEVNULL,
                env=load_env,
            ):
                # Allow dump_proc to receive a SIGPIPE if the load process exits.
                dump_proc.stdout.close()

            err = dump_proc.stderr.read().decode()

        if dump_proc.returncode != 0:
            self.log("Got a fatal error cloning the test database: %s" % err)
            sys.exit(2)

        self.log("Got a non-fatal error cloning the test database: %s" % err)
