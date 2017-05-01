import psycopg2

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models.indexes import Index


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_alter_column_type = "ALTER COLUMN %(column)s TYPE %(type)s USING %(column)s::%(type)s"

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"

    sql_create_index = "CREATE INDEX %(name)s ON %(table)s%(using)s (%(columns)s)%(extra)s"
    sql_delete_index = "DROP INDEX IF EXISTS %(name)s"

    # Setting the constraint to IMMEDIATE runs any deferred checks to allow
    # dropping it in the same transaction.
    sql_delete_fk = "SET CONSTRAINTS %(name)s IMMEDIATE; ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    def quote_value(self, value):
        return psycopg2.extensions.adapt(value)

    def _get_db_specific_indexes(self, model, field):
        db_type = field.db_type(connection=self.connection)
        if db_type is not None and (field.db_index or field.unique):
            if '[' in db_type:
                return []
            if db_type.startswith('varchar') or db_type.startswith('text'):
                # TODO: make this accept the ops class somehow, currently
                # creates a normal index. It will also need to swap the ops
                # depending on the underlying type:
                # varchar: varchar_pattern_ops
                # text: text_pattern_ops
                index = Index(fields=[field.name])
                name = self._create_index_name(model, [field.column], suffix='_like')
                index.name = name
                return [index]
        return []

    def _alter_column_type_sql(self, table, old_field, new_field, new_type):
        """Make ALTER TYPE with SERIAL make sense."""
        if new_type.lower() in ("serial", "bigserial"):
            column = new_field.column
            sequence_name = "%s_%s_seq" % (table, column)
            col_type = "integer" if new_type.lower() == "serial" else "bigint"
            return (
                (
                    self.sql_alter_column_type % {
                        "column": self.quote_name(column),
                        "type": col_type,
                    },
                    [],
                ),
                [
                    (
                        self.sql_delete_sequence % {
                            "sequence": self.quote_name(sequence_name),
                        },
                        [],
                    ),
                    (
                        self.sql_create_sequence % {
                            "sequence": self.quote_name(sequence_name),
                        },
                        [],
                    ),
                    (
                        self.sql_alter_column % {
                            "table": self.quote_name(table),
                            "changes": self.sql_alter_column_default % {
                                "column": self.quote_name(column),
                                "default": "nextval('%s')" % self.quote_name(sequence_name),
                            }
                        },
                        [],
                    ),
                    (
                        self.sql_set_sequence_max % {
                            "table": self.quote_name(table),
                            "column": self.quote_name(column),
                            "sequence": self.quote_name(sequence_name),
                        },
                        [],
                    ),
                ],
            )
        else:
            return super()._alter_column_type_sql(table, old_field, new_field, new_type)
