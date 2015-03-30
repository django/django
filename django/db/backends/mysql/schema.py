from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import NOT_PROVIDED


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_rename_table = "RENAME TABLE %(old_table)s TO %(new_table)s"

    sql_alter_column_null = "MODIFY %(column)s %(type)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s %(type)s NOT NULL"
    sql_alter_column_type = "MODIFY %(column)s %(type)s"
    sql_rename_column = "ALTER TABLE %(table)s CHANGE %(old_column)s %(new_column)s %(type)s"

    sql_delete_unique = "ALTER TABLE %(table)s DROP INDEX %(name)s"

    sql_create_fk = (
        "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY "
        "(%(column)s) REFERENCES %(to_table)s (%(to_column)s)"
    )
    sql_delete_fk = "ALTER TABLE %(table)s DROP FOREIGN KEY %(name)s"

    sql_delete_index = "DROP INDEX %(name)s ON %(table)s"

    alter_string_set_null = 'MODIFY %(column)s %(type)s NULL;'
    alter_string_drop_null = 'MODIFY %(column)s %(type)s NOT NULL;'

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(columns)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    def quote_value(self, value):
        # Inner import to allow module to fail to load gracefully
        import MySQLdb.converters
        return MySQLdb.escape(value, MySQLdb.converters.conversions)

    def skip_default(self, field):
        """
        MySQL doesn't accept default values for longtext and longblob
        and implicitly treats these columns as nullable.
        """
        return field.db_type(self.connection) in {'longtext', 'longblob'}

    def add_field(self, model, field):
        super(DatabaseSchemaEditor, self).add_field(model, field)

        # Simulate the effect of a one-off default.
        if self.skip_default(field) and field.default not in {None, NOT_PROVIDED}:
            effective_default = self.effective_default(field)
            self.execute('UPDATE %(table)s SET %(column)s = %%s' % {
                'table': self.quote_name(model._meta.db_table),
                'column': self.quote_name(field.column),
            }, [effective_default])

    def _model_indexes_sql(self, model):
        storage = self.connection.introspection.get_storage_engine(
            self.connection.cursor(), model._meta.db_table
        )
        if storage == "InnoDB":
            for field in model._meta.local_fields:
                if field.db_index and not field.unique and field.get_internal_type() == "ForeignKey":
                    # Temporary setting db_index to False (in memory) to disable
                    # index creation for FKs (index automatically created by MySQL)
                    field.db_index = False
        return super(DatabaseSchemaEditor, self)._model_indexes_sql(model)
