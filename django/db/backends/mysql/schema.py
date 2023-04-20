from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import NOT_PROVIDED, F, UniqueConstraint
from django.db.models.constants import LOOKUP_SEP


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    sql_rename_table = "RENAME TABLE %(old_table)s TO %(new_table)s"

    sql_alter_column_null = "MODIFY %(column)s %(type)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s %(type)s NOT NULL"
    sql_alter_column_type = "MODIFY %(column)s %(type)s%(collation)s%(comment)s"
    sql_alter_column_no_default_null = "ALTER COLUMN %(column)s SET DEFAULT NULL"

    # No 'CASCADE' which works as a no-op in MySQL but is undocumented
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s"

    sql_delete_unique = "ALTER TABLE %(table)s DROP INDEX %(name)s"
    sql_create_column_inline_fk = (
        ", ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) "
        "REFERENCES %(to_table)s(%(to_column)s)"
    )
    sql_delete_fk = "ALTER TABLE %(table)s DROP FOREIGN KEY %(name)s"

    sql_delete_index = "DROP INDEX %(name)s ON %(table)s"
    sql_rename_index = "ALTER TABLE %(table)s RENAME INDEX %(old_name)s TO %(new_name)s"

    sql_create_pk = (
        "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(columns)s)"
    )
    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    sql_create_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s)%(extra)s"

    sql_alter_table_comment = "ALTER TABLE %(table)s COMMENT = %(comment)s"
    sql_alter_column_comment = None

    @property
    def sql_delete_check(self):
        if self.connection.mysql_is_mariadb:
            # The name of the column check constraint is the same as the field
            # name on MariaDB. Adding IF EXISTS clause prevents migrations
            # crash. Constraint is removed during a "MODIFY" column statement.
            return "ALTER TABLE %(table)s DROP CONSTRAINT IF EXISTS %(name)s"
        return "ALTER TABLE %(table)s DROP CHECK %(name)s"

    @property
    def sql_rename_column(self):
        # MariaDB >= 10.5.2 and MySQL >= 8.0.4 support an
        # "ALTER TABLE ... RENAME COLUMN" statement.
        if self.connection.mysql_is_mariadb:
            if self.connection.mysql_version >= (10, 5, 2):
                return super().sql_rename_column
        elif self.connection.mysql_version >= (8, 0, 4):
            return super().sql_rename_column
        return "ALTER TABLE %(table)s CHANGE %(old_column)s %(new_column)s %(type)s"

    def quote_value(self, value):
        self.connection.ensure_connection()
        if isinstance(value, str):
            value = value.replace("%", "%%")
        # MySQLdb escapes to string, PyMySQL to bytes.
        quoted = self.connection.connection.escape(
            value, self.connection.connection.encoders
        )
        if isinstance(value, str) and isinstance(quoted, bytes):
            quoted = quoted.decode()
        return quoted

    def _is_limited_data_type(self, field):
        db_type = field.db_type(self.connection)
        return (
            db_type is not None
            and db_type.lower() in self.connection._limited_data_types
        )

    def skip_default(self, field):
        if not self._supports_limited_data_type_defaults:
            return self._is_limited_data_type(field)
        return False

    def skip_default_on_alter(self, field):
        if self._is_limited_data_type(field) and not self.connection.mysql_is_mariadb:
            # MySQL doesn't support defaults for BLOB and TEXT in the
            # ALTER COLUMN statement.
            return True
        return False

    @property
    def _supports_limited_data_type_defaults(self):
        # MariaDB and MySQL >= 8.0.13 support defaults for BLOB and TEXT.
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 13)

    def _column_default_sql(self, field):
        if (
            not self.connection.mysql_is_mariadb
            and self._supports_limited_data_type_defaults
            and self._is_limited_data_type(field)
        ):
            # MySQL supports defaults for BLOB and TEXT columns only if the
            # default value is written as an expression i.e. in parentheses.
            return "(%s)"
        return super()._column_default_sql(field)

    def add_field(self, model, field):
        super().add_field(model, field)

        # Simulate the effect of a one-off default.
        # field.default may be unhashable, so a set isn't used for "in" check.
        if self.skip_default(field) and field.default not in (None, NOT_PROVIDED):
            effective_default = self.effective_default(field)
            self.execute(
                "UPDATE %(table)s SET %(column)s = %%s"
                % {
                    "table": self.quote_name(model._meta.db_table),
                    "column": self.quote_name(field.column),
                },
                [effective_default],
            )

    def remove_constraint(self, model, constraint):
        if (
            isinstance(constraint, UniqueConstraint)
            and constraint.create_sql(model, self) is not None
        ):
            self._create_missing_fk_index(
                model,
                fields=constraint.fields,
                expressions=constraint.expressions,
            )
        super().remove_constraint(model, constraint)

    def remove_index(self, model, index):
        self._create_missing_fk_index(
            model,
            fields=[field_name for field_name, _ in index.fields_orders],
            expressions=index.expressions,
        )
        super().remove_index(model, index)

    def _field_should_be_indexed(self, model, field):
        if not super()._field_should_be_indexed(model, field):
            return False

        storage = self.connection.introspection.get_storage_engine(
            self.connection.cursor(), model._meta.db_table
        )
        # No need to create an index for ForeignKey fields except if
        # db_constraint=False because the index from that constraint won't be
        # created.
        if (
            storage == "InnoDB"
            and field.get_internal_type() == "ForeignKey"
            and field.db_constraint
        ):
            return False
        return not self._is_limited_data_type(field)

    def _create_missing_fk_index(
        self,
        model,
        *,
        fields,
        expressions=None,
    ):
        """
        MySQL can remove an implicit FK index on a field when that field is
        covered by another index like a unique_together. "covered" here means
        that the more complex index has the FK field as its first field (see
        https://bugs.mysql.com/bug.php?id=37910).

        Manually create an implicit FK index to make it possible to remove the
        composed index.
        """
        first_field_name = None
        if fields:
            first_field_name = fields[0]
        elif (
            expressions
            and self.connection.features.supports_expression_indexes
            and isinstance(expressions[0], F)
            and LOOKUP_SEP not in expressions[0].name
        ):
            first_field_name = expressions[0].name

        if not first_field_name:
            return

        first_field = model._meta.get_field(first_field_name)
        if first_field.get_internal_type() == "ForeignKey":
            column = self.connection.introspection.identifier_converter(
                first_field.column
            )
            with self.connection.cursor() as cursor:
                constraint_names = [
                    name
                    for name, infodict in self.connection.introspection.get_constraints(
                        cursor, model._meta.db_table
                    ).items()
                    if infodict["index"] and infodict["columns"][0] == column
                ]
            # There are no other indexes that starts with the FK field, only
            # the index that is expected to be deleted.
            if len(constraint_names) == 1:
                self.execute(
                    self._create_index_sql(model, fields=[first_field], suffix="")
                )

    def _delete_composed_index(self, model, fields, *args):
        self._create_missing_fk_index(model, fields=fields)
        return super()._delete_composed_index(model, fields, *args)

    def _set_field_new_type_null_status(self, field, new_type):
        """
        Keep the null property of the old field. If it has changed, it will be
        handled separately.
        """
        if field.null:
            new_type += " NULL"
        else:
            new_type += " NOT NULL"
        return new_type

    def _alter_column_type_sql(
        self, model, old_field, new_field, new_type, old_collation, new_collation
    ):
        new_type = self._set_field_new_type_null_status(old_field, new_type)
        return super()._alter_column_type_sql(
            model, old_field, new_field, new_type, old_collation, new_collation
        )

    def _field_db_check(self, field, field_db_params):
        if self.connection.mysql_is_mariadb and self.connection.mysql_version >= (
            10,
            5,
            2,
        ):
            return super()._field_db_check(field, field_db_params)
        # On MySQL and MariaDB < 10.5.2 (no support for
        # "ALTER TABLE ... RENAME COLUMN" statements), check constraints with
        # the column name as it requires explicit recreation when the column is
        # renamed.
        return field_db_params["check"]

    def _rename_field_sql(self, table, old_field, new_field, new_type):
        new_type = self._set_field_new_type_null_status(old_field, new_type)
        return super()._rename_field_sql(table, old_field, new_field, new_type)

    def _alter_column_comment_sql(self, model, new_field, new_type, new_db_comment):
        # Comment is alter when altering the column type.
        return "", []

    def _comment_sql(self, comment):
        comment_sql = super()._comment_sql(comment)
        return f" COMMENT {comment_sql}"
