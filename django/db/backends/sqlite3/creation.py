import os
import sys
from django.conf import settings
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
        'IPAddressField':               'char(15)',
        'NullBooleanField':             'bool',
        'OneToOneField':                'integer',
        'PhoneNumberField':             'varchar(20)',
        'PositiveIntegerField':         'integer unsigned',
        'PositiveSmallIntegerField':    'smallint unsigned',
        'SlugField':                    'varchar(%(max_length)s)',
        'SmallIntegerField':            'smallint',
        'TextField':                    'text',
        'TimeField':                    'time',
        'USStateField':                 'varchar(2)',
    }
    
    def sql_for_pending_references(self, model, style, pending_references):
        "SQLite3 doesn't support constraints"
        return []

    def sql_remove_table_constraints(self, model, references_to_delete, style):
        "SQLite3 doesn't support constraints"
        return []
        
    def _create_test_db(self, verbosity, autoclobber):
        if settings.TEST_DATABASE_NAME and settings.TEST_DATABASE_NAME != ":memory:":
            test_database_name = settings.TEST_DATABASE_NAME
            # Erase the old test database
            if verbosity >= 1:
                print "Destroying old test database..."
            if os.access(test_database_name, os.F_OK):
                if not autoclobber:
                    confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % test_database_name)
                if autoclobber or confirm == 'yes':
                  try:
                      if verbosity >= 1:
                          print "Destroying old test database..."
                      os.remove(test_database_name)
                  except Exception, e:
                      sys.stderr.write("Got an error deleting the old test database: %s\n" % e)
                      sys.exit(2)
                else:
                    print "Tests cancelled."
                    sys.exit(1)
            if verbosity >= 1:
                print "Creating test database..."
        else:
            test_database_name = ":memory:"
        return test_database_name
        
    def _destroy_test_db(self, test_database_name, verbosity):
        if test_database_name and test_database_name != ":memory:":
            # Remove the SQLite database file
            os.remove(test_database_name)
