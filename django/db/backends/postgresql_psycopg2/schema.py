from django.db.backends.schema import BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"

    def _alter_db_column_sql(self, model, column, alteration=None, values={}, fragment=False, params=None):
        if alteration == 'type' and values.get('type', '').lower() == 'serial':
            # Makes ALTER TYPE with SERIAL make sense.
            sequence_name = "%s_%s_seq" % (model._meta.db_table, column)
            values['type'] = 'integer'

            actions, post_actions = super(DatabaseSchemaEditor, self)._alter_column_type_sql(model, column, alteration,
                values, fragment, params)
            post_actions.extend([
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
            ])
        else:
            actions, post_actions = super(DatabaseSchemaEditor, self)._alter_column_type_sql(model, column, alteration,
                values, fragment, params)
        return actions, post_actions

    def _quote_parameter(self, value):
        # Inner import so backend fails nicely if it's not present
        import psycopg2
        return psycopg2.extensions.adapt(value)

