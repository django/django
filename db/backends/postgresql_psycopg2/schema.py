from django.db.backends.schema import BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"

    def quote_value(self, value):
        # Inner import so backend fails nicely if it's not present
        import psycopg2
        return psycopg2.extensions.adapt(value)

    def _alter_column_type_sql(self, table, column, type):
        """
        Makes ALTER TYPE with SERIAL make sense.
        """
        if type.lower() == "serial":
            sequence_name = "%s_%s_seq" % (table, column)
            return (
                (
                    self.sql_alter_column_type % {
                        "column": self.quote_name(column),
                        "type": "integer",
                    },
                    [],
                ),
                [
                    (
                        self.sql_delete_sequence % {
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                    (
                        self.sql_create_sequence % {
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                    (
                        self.sql_alter_column % {
                            "table": table,
                            "changes": self.sql_alter_column_default % {
                                "column": column,
                                "default": "nextval('%s')" % sequence_name,
                            }
                        },
                        [],
                    ),
                    (
                        self.sql_set_sequence_max % {
                            "table": table,
                            "column": column,
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                ],
            )
        else:
            return super(DatabaseSchemaEditor, self)._alter_column_type_sql(table, column, type)
