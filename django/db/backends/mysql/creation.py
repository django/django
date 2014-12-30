from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

    def sql_table_creation_suffix(self):
        suffix = []
        test_settings = self.connection.settings_dict['TEST']
        if test_settings['CHARSET']:
            suffix.append('CHARACTER SET %s' % test_settings['CHARSET'])
        if test_settings['COLLATION']:
            suffix.append('COLLATE %s' % test_settings['COLLATION'])
        return ' '.join(suffix)
