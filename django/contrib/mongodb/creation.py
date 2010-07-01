from django.db.backends.creation import TEST_DATABASE_PREFIX


class DatabaseCreation(object):
    def __init__(self, connection):
        self.connection = connection
    
    def db_type(self, field):
        return None
    
    def create_test_db(self, verbosity, autoclobber):
        if self.connection.settings_dict['TEST_NAME']:
            test_database_name = self.connection.settings_dict['TEST_NAME']
        else:
            test_database_name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        self.connection.settings_dict["NAME"] = test_database_name
        self.connection.settings_dict["SUPPORTS_TRANSACTIONS"] = False
        return test_database_name
    
    def destroy_test_db(self, old_database_name, verbosity=1):
        if verbosity >= 1:
            print "Destroying test database '%s'..." % self.connection.alias
        self.connection.connection.drop_database(self.connection.settings_dict["NAME"])
        self.connection.settings_dict["NAME"] = old_database_name
