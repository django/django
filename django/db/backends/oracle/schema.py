import binascii
import copy
import datetime

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.utils import DatabaseError
from django.utils import six
from django.utils.text import force_text


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_column = "ALTER TABLE %(table)s ADD %(column)s %(definition)s"
    sql_alter_column_type = "MODIFY %(column)s %(type)s"
    sql_alter_column_null = "MODIFY %(column)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s NOT NULL"
    sql_alter_column_default = "MODIFY %(column)s DEFAULT %(default)s"
    sql_alter_column_no_default = "MODIFY %(column)s DEFAULT NULL"
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s"
    sql_delete_table = "DROP TABLE %(table)s CASCADE CONSTRAINTS"

    def quote_value(self, value):
        if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
            return "'%s'" % value
        elif isinstance(value, six.string_types):
            return "'%s'" % six.text_type(value).replace("\'", "\'\'")
        elif isinstance(value, six.buffer_types):
            return "'%s'" % force_text(binascii.hexlify(value))
        elif isinstance(value, bool):
            return "1" if value else "0"
        else:
            return str(value)

    def delete_model(self, model):
        # Run superclass action
        super(DatabaseSchemaEditor, self).delete_model(model)
        # Clean up any autoincrement trigger
        self.execute("""
            DECLARE
                i INTEGER;
            BEGIN
                SELECT COUNT(*) INTO i FROM USER_CATALOG
                    WHERE TABLE_NAME = '%(sq_name)s' AND TABLE_TYPE = 'SEQUENCE';
                IF i = 1 THEN
                    EXECUTE IMMEDIATE 'DROP SEQUENCE "%(sq_name)s"';
                END IF;
            END;
        /""" % {'sq_name': self.connection.ops._get_sequence_name(model._meta.db_table)})

    def alter_field(self, model, old_field, new_field, strict=False):
        try:
            # Run superclass action
            super(DatabaseSchemaEditor, self).alter_field(model, old_field, new_field, strict)
        except DatabaseError as e:
            description = str(e)
            # If we're changing to/from LOB fields, we need to do a
            # SQLite-ish workaround
            if 'ORA-22858' in description or 'ORA-22859' in description:
                self._alter_field_lob_workaround(model, old_field, new_field)
            else:
                raise

    def _alter_field_lob_workaround(self, model, old_field, new_field):
        """
        Oracle refuses to change a column type from/to LOB to/from a regular
        column. In Django, this shows up when the field is changed from/to
        a TextField.
        What we need to do instead is:
        - Add the desired field with a temporary name
        - Update the table to transfer values from old to new
        - Drop old column
        - Rename the new column
        """
        # Make a new field that's like the new one but with a temporary
        # column name.
        new_temp_field = copy.deepcopy(new_field)
        new_temp_field.column = self._generate_temp_name(new_field.column)
        # Add it
        self.add_field(model, new_temp_field)
        # Transfer values across
        self.execute("UPDATE %s set %s=%s" % (
            self.quote_name(model._meta.db_table),
            self.quote_name(new_temp_field.column),
            self.quote_name(old_field.column),
        ))
        # Drop the old field
        self.remove_field(model, old_field)
        # Rename the new field
        self.alter_field(model, new_temp_field, new_field)

    def normalize_name(self, name):
        """
        Get the properly shortened and uppercased identifier as returned by
        quote_name(), but without the actual quotes.
        """
        nn = self.quote_name(name)
        if nn[0] == '"' and nn[-1] == '"':
            nn = nn[1:-1]
        return nn

    def _generate_temp_name(self, for_name):
        """
        Generates temporary names for workarounds that need temp columns
        """
        suffix = hex(hash(for_name)).upper()[1:]
        return self.normalize_name(for_name + "_" + suffix)

    def prepare_default(self, value):
        return self.quote_value(value)
