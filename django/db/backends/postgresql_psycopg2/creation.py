from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

    def sql_table_creation_suffix(self):
        test_settings = self.connection.settings_dict['TEST']
        assert test_settings['COLLATION'] is None, (
            "PostgreSQL does not support collation setting at database creation time."
        )
        if test_settings['CHARSET']:
            return "WITH ENCODING '%s'" % test_settings['CHARSET']
        return ''
