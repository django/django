import os
import sys
from django.db.backends.creation import BaseDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    # SQLite doesn't actually support most of these types, but it "does the right
    # thing" given more verbose field definitions, so leave them as is so that
    # schema inspection is more useful.
    data_types = {
        'AutoField':                    'integer',
        'BooleanField':                 'bool',
        'CharField':                    'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField':   'varchar(%(max_length)s)',
        'DateField':                    'date',
        'DateTimeField':                'datetime',
        'DecimalField':                 'decimal',
        'FileField':                    'varchar(%(max_length)s)',
        'FilePathField':                'varchar(%(max_length)s)',
        'FloatField':                   'real',
        'IntegerField':                 'integer',
        'BigIntegerField':              'bigint',
        'IPAddressField':               'char(15)',
        'GenericIPAddressField':        'char(39)',
        'NullBooleanField':             'bool',
        'OneToOneField':                'integer',
        'PositiveIntegerField':         'integer unsigned',
        'PositiveSmallIntegerField':    'smallint unsigned',
        'SlugField':                    'varchar(%(max_length)s)',
        'SmallIntegerField':            'smallint',
        'TextField':                    'text',
        'TimeField':                    'time',
    }

    def sql_for_pending_references(self, model, style, pending_references):
        "SQLite3 doesn't support constraints"
        return []

    def sql_remove_table_constraints(self, model, references_to_delete, style):
        "SQLite3 doesn't support constraints"
        return []

    def _get_test_db_name(self):
        test_database_name = self.connection.settings_dict['TEST_NAME']
        if test_database_name and test_database_name != ':memory:':
            return test_database_name
        return ':memory:'

    def _create_test_db(self, verbosity, autoclobber):
        test_database_name = self._get_test_db_name()
        if test_database_name != ':memory:':
            # Erase the old test database
            if verbosity >= 1:
                print "Destroying old test database '%s'..." % self.connection.alias
            if os.access(test_database_name, os.F_OK):
                if not autoclobber:
                    confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % test_database_name)
                if autoclobber or confirm == 'yes':
                  try:
                      os.remove(test_database_name)
                  except Exception, e:
                      sys.stderr.write("Got an error deleting the old test database: %s\n" % e)
                      sys.exit(2)
                else:
                    print "Tests cancelled."
                    sys.exit(1)
        return test_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        if test_database_name and test_database_name != ":memory:":
            # Remove the SQLite database file
            os.remove(test_database_name)

    def set_autocommit(self):
        self.connection.connection.isolation_level = None

    def test_db_signature(self):
        """
        Returns a tuple that uniquely identifies a test database.

        This takes into account the special cases of ":memory:" and "" for
        SQLite since the databases will be distinct despite having the same
        TEST_NAME. See http://www.sqlite.org/inmemorydb.html
        """
        settings_dict = self.connection.settings_dict
        test_dbname = self._get_test_db_name()
        sig = [self.connection.settings_dict['NAME']]
        if test_dbname == ':memory:':
            sig.append(self.connection.alias)
        return tuple(sig)
