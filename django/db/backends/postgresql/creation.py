import sys

from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

    def _quote_name(self, name):
        return self.connection.ops.quote_name(name)

    def _get_database_create_suffix(self, encoding=None, template=None):
        suffix = ""
        if encoding:
            suffix += " ENCODING '{}'".format(encoding)
        if template:
            suffix += " TEMPLATE {}".format(self._quote_name(template))
        if suffix:
            suffix = "WITH" + suffix
        return suffix

    def sql_table_creation_suffix(self):
        test_settings = self.connection.settings_dict['TEST']
        assert test_settings['COLLATION'] is None, (
            "PostgreSQL does not support collation setting at database creation time."
        )
        return self._get_database_create_suffix(
            encoding=test_settings['CHARSET'],
            template=test_settings.get('TEMPLATE'),
        )

    def _clone_test_db(self, number, verbosity, keepdb=False):
        # CREATE DATABASE ... WITH TEMPLATE ... requires closing connections
        # to the template database.
        self.connection.close()

        source_database_name = self.connection.settings_dict['NAME']
        target_database_name = self.get_test_db_clone_settings(number)['NAME']
        suffix = self._get_database_create_suffix(template=source_database_name)
        creation_sql = "CREATE DATABASE {} {}".format(self._quote_name(target_database_name), suffix)

        with self._nodb_connection.cursor() as cursor:
            try:
                cursor.execute(creation_sql)
            except Exception:
                if keepdb:
                    return
                try:
                    if verbosity >= 1:
                        print("Destroying old test database for alias %s..." % (
                            self._get_database_display_str(verbosity, target_database_name),
                        ))
                    cursor.execute("DROP DATABASE %s" % self._quote_name(target_database_name))
                    cursor.execute(creation_sql)
                except Exception as e:
                    sys.stderr.write("Got an error cloning the test database: %s\n" % e)
                    sys.exit(2)
