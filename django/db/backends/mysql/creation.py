import subprocess
import sys

from django.db.backends.base.creation import BaseDatabaseCreation

from .client import DatabaseClient


class DatabaseCreation(BaseDatabaseCreation):

    def sql_table_creation_suffix(self):
        suffix = []
        test_settings = self.connection.settings_dict['TEST']
        if test_settings['CHARSET']:
            suffix.append('CHARACTER SET %s' % test_settings['CHARSET'])
        if test_settings['COLLATION']:
            suffix.append('COLLATE %s' % test_settings['COLLATION'])
        return ' '.join(suffix)

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        try:
            super()._execute_create_test_db(cursor, parameters, keepdb)
        except Exception as e:
            if len(e.args) < 1 or e.args[0] != 1007:
                # All errors except "database exists" (1007) cancel tests.
                sys.stderr.write('Got an error creating the test database: %s\n' % e)
                sys.exit(2)
            else:
                raise e

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict['NAME']
        target_database_name = self.get_test_db_clone_settings(suffix)['NAME']
        test_db_params = {
            'dbname': self.connection.ops.quote_name(target_database_name),
            'suffix': self.sql_table_creation_suffix(),
        }
        with self._nodb_connection.cursor() as cursor:
            try:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
            except Exception:
                if keepdb:
                    # If the database should be kept, skip everything else.
                    return
                try:
                    if verbosity >= 1:
                        print("Destroying old test database for alias %s..." % (
                            self._get_database_display_str(verbosity, target_database_name),
                        ))
                    cursor.execute('DROP DATABASE %(dbname)s' % test_db_params)
                    self._execute_create_test_db(cursor, test_db_params, keepdb)
                except Exception as e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
        self._clone_db(source_database_name, target_database_name)

    def _clone_db(self, source_database_name, target_database_name):
        dump_cmd = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict)
        dump_cmd[0] = 'mysqldump'
        dump_cmd[-1] = source_database_name
        load_cmd = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict)
        load_cmd[-1] = target_database_name

        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE)
        load_proc = subprocess.Popen(load_cmd, stdin=dump_proc.stdout, stdout=subprocess.PIPE)
        dump_proc.stdout.close()    # allow dump_proc to receive a SIGPIPE if load_proc exits.
        load_proc.communicate()
