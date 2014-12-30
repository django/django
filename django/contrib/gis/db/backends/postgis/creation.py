from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation


class PostGISCreation(DatabaseCreation):

    def sql_table_creation_suffix(self):
        if self.connection.template_postgis is not None:
            return ' TEMPLATE %s' % (
                self.connection.ops.quote_name(self.connection.template_postgis),)
        return ''
