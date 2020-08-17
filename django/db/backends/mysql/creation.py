import multiprocessing
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
                self.log('Got an error creating the test database: %s' % e)
                sys.exit(2)
            else:
                raise
    
    def pre_parallel_cloning(self, verbosity, keepdb=False, parallel=1):
        source_db = self.connection.settings_dict['NAME']
        dump_args = DatabaseClient.settings_to_cmd_args(self.connection.settings_dict, [])[1:]
        dump_cmd = ['mysqlpump', *dump_args[:-1], '--no-create-db', f'--default-parallelism={parallel}',
                    '--events', f'--include-databases={source_db}',
                    f'--result-file={source_db}']
        subprocess.run(dump_cmd)

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict['NAME']
        target_database_name = self.get_test_db_clone_settings(suffix)['NAME']
        test_db_params = {
            'dbname': self.connection.ops.quote_name(target_database_name),
            'suffix': self.sql_table_creation_suffix(),
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
                        self.log('Destroying old test database for alias %s...' % (
                            self._get_database_display_str(verbosity, target_database_name),
                        ))
                    cursor.execute('DROP DATABASE %(dbname)s' % test_db_params)
                    self._execute_create_test_db(cursor, test_db_params, keepdb)
                except Exception as e:
                    self.log('Got an error recreating the test database: %s' % e)
                    sys.exit(2)

        self._clone_db(source_database_name, self.connection.settings_dict, target_database_name)
        
    def _clone_db(self, source_db, settings_dict, target_db):
        load_cmd = DatabaseClient.settings_to_cmd_args(settings_dict, [])
        with open(source_db, 'r') as dump:
            with open(target_db, 'w+') as modified_dump:
                total_dump = dump.read()
                modified_dump.write(total_dump.replace(source_db, target_db))
        modified_dump = open(target_db, 'r')
        with subprocess.Popen(load_cmd, stdin=modified_dump, stdout=subprocess.DEVNULL):
            pass
        modified_dump.close()
