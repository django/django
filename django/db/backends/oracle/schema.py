import copy
import datetime
import re

from django.db import DatabaseError
from django.db.backends.base.schema import (
    BaseDatabaseSchemaEditor, _related_non_m2m_objects,
)


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_column = "ALTER TABLE %(table)s ADD %(column)s %(definition)s"
    sql_alter_column_type = "MODIFY %(column)s %(type)s"
    sql_alter_column_null = "MODIFY %(column)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s NOT NULL"
    sql_alter_column_default = "MODIFY %(column)s DEFAULT %(default)s"
    sql_alter_column_no_default = "MODIFY %(column)s DEFAULT NULL"
    sql_alter_column_no_default_null = sql_alter_column_no_default
    sql_alter_column_collate = "MODIFY %(column)s %(type)s%(collation)s"

    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s"
    sql_create_column_inline_fk = 'CONSTRAINT %(name)s REFERENCES %(to_table)s(%(to_column)s)%(deferrable)s'
    sql_delete_table = "DROP TABLE %(table)s CASCADE CONSTRAINTS"
    sql_create_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s)%(extra)s"

    def quote_value(self, value):
        if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
            return "'%s'" % value
        elif isinstance(value, str):
            return "'%s'" % value.replace("\'", "\'\'").replace('%', '%%')
        elif isinstance(value, (bytes, bytearray, memoryview)):
            return "'%s'" % value.hex()
        elif isinstance(value, bool):
            return "1" if value else "0"
        else:
            return str(value)

    def remove_field(self, model, field):
        # If the column is an identity column, drop the identity before
        # removing the field.
        if self._is_identity_column(model._meta.db_table, field.column):
            self._drop_identity(model._meta.db_table, field.column)
        super().remove_field(model, field)

    def delete_model(self, model):
        # Run superclass action
        super().delete_model(model)
        # Clean up manually created sequence.
        self.execute("""
            DECLARE
                i INTEGER;
            BEGIN
                SELECT COUNT(1) INTO i FROM USER_SEQUENCES
                    WHERE SEQUENCE_NAME = '%(sq_name)s';
                IF i = 1 THEN
                    EXECUTE IMMEDIATE 'DROP SEQUENCE "%(sq_name)s"';
                END IF;
            END;
        /""" % {'sq_name': self.connection.ops._get_no_autofield_sequence_name(model._meta.db_table)})

    def alter_field(self, model, old_field, new_field, strict=False):
        try:
            super().alter_field(model, old_field, new_field, strict)
        except DatabaseError as e:
            description = str(e)
            # If we're changing type to an unsupported type we need a
            # SQLite-ish workaround
            if 'ORA-22858' in description or 'ORA-22859' in description:
                self._alter_field_type_workaround(model, old_field, new_field)
            # If an identity column is changing to a non-numeric type, drop the
            # identity first.
            elif 'ORA-30675' in description:
                self._drop_identity(model._meta.db_table, old_field.column)
                self.alter_field(model, old_field, new_field, strict)
            # If a primary key column is changing to an identity column, drop
            # the primary key first.
            elif 'ORA-30673' in description and old_field.primary_key:
                self._delete_primary_key(model, strict=True)
                self._alter_field_type_workaround(model, old_field, new_field)
            else:
                raise

    def _alter_field_type_workaround(self, model, old_field, new_field):
        """
        Oracle refuses to change from some type to other type.
        What we need to do instead is:
        - Add a nullable version of the desired field with a temporary name. If
          the new column is an auto field, then the temporary column can't be
          nullable.
        - Update the table to transfer values from old to new
        - Drop old column
        - Rename the new column and possibly drop the nullable property
        """
        # Make a new field that's like the new one but with a temporary
        # column name.
        new_temp_field = copy.deepcopy(new_field)
        new_temp_field.null = (new_field.get_internal_type() not in ('AutoField', 'BigAutoField', 'SmallAutoField'))
        new_temp_field.column = self._generate_temp_name(new_field.column)
        # Add it
        self.add_field(model, new_temp_field)
        # Explicit data type conversion
        # https://docs.oracle.com/en/database/oracle/oracle-database/18/sqlrf
        # /Data-Type-Comparison-Rules.html#GUID-D0C5A47E-6F93-4C2D-9E49-4F2B86B359DD
        new_value = self.quote_name(old_field.column)
        old_type = old_field.db_type(self.connection)
        if re.match('^N?CLOB', old_type):
            new_value = "TO_CHAR(%s)" % new_value
            old_type = 'VARCHAR2'
        if re.match('^N?VARCHAR2', old_type):
            new_internal_type = new_field.get_internal_type()
            if new_internal_type == 'DateField':
                new_value = "TO_DATE(%s, 'YYYY-MM-DD')" % new_value
            elif new_internal_type == 'DateTimeField':
                new_value = "TO_TIMESTAMP(%s, 'YYYY-MM-DD HH24:MI:SS.FF')" % new_value
            elif new_internal_type == 'TimeField':
                # TimeField are stored as TIMESTAMP with a 1900-01-01 date part.
                new_value = "TO_TIMESTAMP(CONCAT('1900-01-01 ', %s), 'YYYY-MM-DD HH24:MI:SS.FF')" % new_value
        # Transfer values across
        self.execute("UPDATE %s set %s=%s" % (
            self.quote_name(model._meta.db_table),
            self.quote_name(new_temp_field.column),
            new_value,
        ))
        # Drop the old field
        self.remove_field(model, old_field)
        # Rename and possibly make the new field NOT NULL
        super().alter_field(model, new_temp_field, new_field)
        # Recreate foreign key (if necessary) because the old field is not
        # passed to the alter_field() and data types of new_temp_field and
        # new_field always match.
        new_type = new_field.db_type(self.connection)
        if (
            (old_field.primary_key and new_field.primary_key) or
            (old_field.unique and new_field.unique)
        ) and old_type != new_type:
            for _, rel in _related_non_m2m_objects(new_temp_field, new_field):
                if rel.field.db_constraint:
                    self.execute(self._create_fk_sql(rel.related_model, rel.field, '_fk'))

    def _alter_column_type_sql(self, model, old_field, new_field, new_type):
        auto_field_types = {'AutoField', 'BigAutoField', 'SmallAutoField'}
        # Drop the identity if migrating away from AutoField.
        if (
            old_field.get_internal_type() in auto_field_types and
            new_field.get_internal_type() not in auto_field_types and
            self._is_identity_column(model._meta.db_table, new_field.column)
        ):
            self._drop_identity(model._meta.db_table, new_field.column)
        return super()._alter_column_type_sql(model, old_field, new_field, new_type)

    def normalize_name(self, name):
        """
        Get the properly shortened and uppercased identifier as returned by
        quote_name() but without the quotes.
        """
        nn = self.quote_name(name)
        if nn[0] == '"' and nn[-1] == '"':
            nn = nn[1:-1]
        return nn

    def _generate_temp_name(self, for_name):
        """Generate temporary names for workarounds that need temp columns."""
        suffix = hex(hash(for_name)).upper()[1:]
        return self.normalize_name(for_name + "_" + suffix)

    def prepare_default(self, value):
        return self.quote_value(value)

    def _field_should_be_indexed(self, model, field):
        create_index = super()._field_should_be_indexed(model, field)
        db_type = field.db_type(self.connection)
        if db_type is not None and db_type.lower() in self.connection._limited_data_types:
            return False
        return create_index

    def _unique_should_be_added(self, old_field, new_field):
        return (
            super()._unique_should_be_added(old_field, new_field) and
            not self._field_became_primary_key(old_field, new_field)
        )

    def _is_identity_column(self, table_name, column_name):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    CASE WHEN identity_column = 'YES' THEN 1 ELSE 0 END
                FROM user_tab_cols
                WHERE table_name = %s AND
                      column_name = %s
            """, [self.normalize_name(table_name), self.normalize_name(column_name)])
            row = cursor.fetchone()
            return row[0] if row else False

    def _drop_identity(self, table_name, column_name):
        self.execute('ALTER TABLE %(table)s MODIFY %(column)s DROP IDENTITY' % {
            'table': self.quote_name(table_name),
            'column': self.quote_name(column_name),
        })

    def _get_default_collation(self, table_name):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT default_collation FROM user_tables WHERE table_name = %s
            """, [self.normalize_name(table_name)])
            return cursor.fetchone()[0]

    def _alter_column_collation_sql(self, model, new_field, new_type, new_collation):
        if new_collation is None:
            new_collation = self._get_default_collation(model._meta.db_table)
        return super()._alter_column_collation_sql(model, new_field, new_type, new_collation)
