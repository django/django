import psycopg2

from django.contrib.postgres.search import SearchVectorField
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_alter_column_type = "ALTER COLUMN %(column)s TYPE %(type)s USING %(column)s::%(type)s"

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"

    sql_create_index = "CREATE INDEX %(name)s ON %(table)s%(using)s (%(columns)s)%(extra)s"
    sql_create_varchar_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s varchar_pattern_ops)%(extra)s"
    sql_create_text_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s text_pattern_ops)%(extra)s"

    # Setting the constraint to IMMEDIATE runs any deferred checks to allow
    # dropping it in the same transaction.
    sql_delete_fk = "SET CONSTRAINTS %(name)s IMMEDIATE; ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    def quote_value(self, value):
        return psycopg2.extensions.adapt(value)

    def _field_indexes_sql(self, model, field):
        output = super()._field_indexes_sql(model, field)
        like_index_statement = self._create_like_index_sql(model, field)
        if like_index_statement is not None:
            output.append(like_index_statement)
        return output

    def _create_like_index_sql(self, model, field):
        """
        Return the statement to create an index with varchar operator pattern
        when the column type is 'varchar' or 'text', otherwise return None.
        """
        db_type = field.db_type(connection=self.connection)
        if db_type is not None and (field.db_index or field.unique):
            # Fields with database column types of `varchar` and `text` need
            # a second index that specifies their operator class, which is
            # needed when performing correct LIKE queries outside the
            # C locale. See #12234.
            #
            # The same doesn't apply to array fields such as varchar[size]
            # and text[size], so skip them.
            if '[' in db_type:
                return None
            if db_type.startswith('varchar'):
                return self._create_index_sql(model, [field], suffix='_like', sql=self.sql_create_varchar_index)
            elif db_type.startswith('text'):
                return self._create_index_sql(model, [field], suffix='_like', sql=self.sql_create_text_index)
        return None

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

    def _alter_field(self, model, old_field, new_field, old_type, new_type,
                     old_db_params, new_db_params, strict=False):
        super()._alter_field(
            model, old_field, new_field, old_type, new_type, old_db_params,
            new_db_params, strict,
        )
        # Added an index? Create any PostgreSQL-specific indexes.
        if ((not (old_field.db_index or old_field.unique) and new_field.db_index) or
                (not old_field.unique and new_field.unique)):
            like_index_statement = self._create_like_index_sql(model, new_field)
            if like_index_statement is not None:
                self.execute(like_index_statement)

        # Removed an index? Drop any PostgreSQL-specific indexes.
        if old_field.unique and not (new_field.db_index or new_field.unique):
            index_to_remove = self._create_index_name(model, [old_field.column], suffix='_like')
            index_names = self._constraint_names(model, [old_field.column], index=True)
            for index_name in index_names:
                if index_name == index_to_remove:
                    self.execute(self._delete_constraint_sql(self.sql_delete_index, model, index_name))

        if isinstance(old_field, SearchVectorField) or isinstance(new_field, SearchVectorField):
            if not isinstance(new_field, SearchVectorField):
                self.deferred_sql.extend(self._drop_tsvector_trigger(model, old_field))
            elif not isinstance(old_field, SearchVectorField) and isinstance(new_field, SearchVectorField):
                self.deferred_sql.extend(self._create_tsvector_trigger(model, new_field))
            elif old_field.columns != new_field.columns:
                self.deferred_sql.extend(self._drop_tsvector_trigger(model, old_field))
                self.deferred_sql.extend(self._create_tsvector_trigger(model, new_field))

    def _tsvector_setweight(self, field):

        if field.language_column and field.language:
            language = 'COALESCE(NEW.{}::regconfig, {})'.format(
                self.quote_name(field.language_column),
                self.quote_value(field.language)
            )
        elif field.language_column:
            language = 'NEW.{}::regconfig'.format(
                self.quote_name(field.language_column)
            )
        else:
            language = self.quote_value(field.language or 'english')

        sql_setweight = (
            "setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"
        )

        weights = []
        for column in field.columns:
            weights.append(sql_setweight.format(
                language=language,
                column=self.quote_name(column.name),
                weight=self.quote_value(column.weight)
            ))
        weights[-1] = weights[-1][:-3] + ';'
        return weights

    def _tsvector_update_column_checks(self, field):
        checks = []
        for column in field.columns:
            checks.append(
                "ELSIF (NEW.{column} <> OLD.{column}) THEN do_update = true;".format(
                    column=self.quote_name(column.name)
                )
            )
        checks[0] = checks[0][3:]
        checks.append('END IF;')
        return checks

    sql_tsvector_create_trigger_function = (
        "CREATE FUNCTION {function}() RETURNS trigger AS $$\n"
        "DECLARE\n"
        " do_update bool default false;\n"
        "BEGIN\n"
        " {update_checks}\n"
        " IF do_update THEN\n"
        "  {update_body}\n"
        " END IF;\n"
        " RETURN NEW;\n"
        "END\n"
        "$$ LANGUAGE plpgsql"
    )

    def _create_tsvector_update_function(self, function, field):

        update_checks = ["do_update = true;"]
        if not field.force_update:
            update_checks = [
                "IF (TG_OP = 'INSERT') THEN do_update = true;",
                "ELSIF (TG_OP = 'UPDATE') THEN"] + [
                ' ' + check for check in self._tsvector_update_column_checks(field)] + [
                "END IF;"
            ]

        update_body = [
            "NEW.{} :=".format(self.quote_name(field.column))] + [
            ' ' + weight for weight in self._tsvector_setweight(field)
        ]

        return self.sql_tsvector_create_trigger_function.format(
            function=function,
            update_checks='\n '.join(update_checks),
            update_body='\n  '.join(update_body)
        )

    sql_create_insert_or_update_trigger = (
        "CREATE TRIGGER {trigger} BEFORE INSERT OR UPDATE"
        " ON {table} FOR EACH ROW EXECUTE PROCEDURE {function}()"
    )

    def _create_tsvector_trigger(self, model, field):

        assert field.columns, "Cannot create text search trigger without 'columns'."

        tsvector_function = self._create_index_name(model, [field.column], '_func')
        tsvector_trigger = self._create_index_name(model, [field.column], '_trig')

        yield self._create_tsvector_update_function(tsvector_function, field)

        yield self.sql_create_insert_or_update_trigger.format(
            table=self.quote_name(model._meta.db_table),
            trigger=self.quote_name(tsvector_trigger),
            function=tsvector_function,
        )

    sql_drop_trigger = "DROP TRIGGER IF EXISTS {trigger} ON {table}"
    sql_drop_trigger_function = "DROP FUNCTION IF EXISTS {function}()"

    def _drop_tsvector_trigger(self, model, field):

        tsvector_function = self._create_index_name(model, [field.column], '_func')
        tsvector_trigger = self._create_index_name(model, [field.column], '_trig')

        yield self.sql_drop_trigger.format(
            table=self.quote_name(model._meta.db_table),
            trigger=tsvector_trigger,
        )

        yield self.sql_drop_trigger_function.format(
            function=tsvector_function,
        )

    def create_model(self, model):
        super(DatabaseSchemaEditor, self).create_model(model)
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField) and field.columns:
                self.deferred_sql.extend(self._create_tsvector_trigger(model, field))

    def delete_model(self, model):
        super(DatabaseSchemaEditor, self).delete_model(model)
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField):
                self.deferred_sql.extend(self._drop_tsvector_trigger(model, field))

    def add_field(self, model, field):
        super(DatabaseSchemaEditor, self).add_field(model, field)
        if isinstance(field, SearchVectorField) and field.columns:
            self.deferred_sql.extend(self._create_tsvector_trigger(model, field))

    def remove_field(self, model, field):
        super(DatabaseSchemaEditor, self).remove_field(model, field)
        if isinstance(field, SearchVectorField):
            self.deferred_sql.extend(self._drop_tsvector_trigger(model, field))
