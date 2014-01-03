from django.db.backends.schema import BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_rename_table = "RENAME TABLE %(old_table)s TO %(new_table)s"

    sql_alter_column_null = "MODIFY %(column)s %(type)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s %(type)s NOT NULL"
    sql_alter_column_type = "MODIFY %(column)s %(type)s"
    sql_rename_column = "ALTER TABLE %(table)s CHANGE %(old_column)s %(new_column)s %(type)s"

    sql_delete_unique = "ALTER TABLE %(table)s DROP INDEX %(name)s"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s)"
    sql_delete_fk = "ALTER TABLE %(table)s DROP FOREIGN KEY %(name)s"

    sql_delete_index = "DROP INDEX %(name)s ON %(table)s"

    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    alter_string_set_null = 'MODIFY %(column)s %(type)s NULL;'
    alter_string_drop_null = 'MODIFY %(column)s %(type)s NOT NULL;'

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(column)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    def _quote_parameter(self, value):
        # Inner import to allow module to fail to load gracefully
        import MySQLdb.converters
        return MySQLdb.escape(value, MySQLdb.converters.conversions)

