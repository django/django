import codecs
import copy
from decimal import Decimal
from django.utils import six
from django.apps.registry import Apps
from django.db.backends.schema import BaseDatabaseSchemaEditor
from django.db.models.fields.related import ManyToManyField


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_delete_table = "DROP TABLE %(table)s"
    sql_create_inline_fk = "REFERENCES %(to_table)s (%(to_column)s)"

    def quote_value(self, value):
        # Inner import to allow nice failure for backend if not present
        import _sqlite3
        try:
            value = _sqlite3.adapt(value)
        except _sqlite3.ProgrammingError:
            pass
        # Manual emulation of SQLite parameter quoting
        if isinstance(value, type(True)):
            return str(int(value))
        elif isinstance(value, (Decimal, float)):
            return str(value)
        elif isinstance(value, six.integer_types):
            return str(value)
        elif isinstance(value, six.string_types):
            return "'%s'" % six.text_type(value).replace("\'", "\'\'")
        elif value is None:
            return "NULL"
        elif isinstance(value, (bytes, bytearray, six.memoryview)):
            # Bytes are only allowed for BLOB fields, encoded as string
            # literals containing hexadecimal data and preceded by a single "X"
            # character:
            # value = b'\x01\x02' => value_hex = b'0102' => return X'0102'
            value = bytes(value)
            hex_encoder = codecs.getencoder('hex_codec')
            value_hex, _length = hex_encoder(value)
            # Use 'ascii' encoding for b'01' => '01', no need to use force_text here.
            return "X'%s'" % value_hex.decode('ascii')
        else:
            raise ValueError("Cannot quote parameter value %r of type %s" % (value, type(value)))

    def _remake_table(self, model, create_fields=[], delete_fields=[], alter_fields=[], override_uniques=None):
        """
        Shortcut to transform a model from old_model into new_model
        """
        # Work out the new fields dict / mapping
        body = dict((f.name, f) for f in model._meta.local_fields)
        # Since mapping might mix column names and default values,
        # its values must be already quoted.
        mapping = dict((f.column, self.quote_name(f.column)) for f in model._meta.local_fields)
        # This maps field names (not columns) for things like unique_together
        rename_mapping = {}
        # If any of the new or altered fields is introducing a new PK,
        # remove the old one
        restore_pk_field = None
        if any(f.primary_key for f in create_fields) or any(n.primary_key for o, n in alter_fields):
            for name, field in list(body.items()):
                if field.primary_key:
                    field.primary_key = False
                    restore_pk_field = field
                    if field.auto_created:
                        del body[name]
                        del mapping[field.column]
        # Add in any created fields
        for field in create_fields:
            body[field.name] = field
            # If there's a default, insert it into the copy map
            if field.has_default():
                mapping[field.column] = self.quote_value(
                    self.effective_default(field)
                )
        # Add in any altered fields
        for (old_field, new_field) in alter_fields:
            del body[old_field.name]
            del mapping[old_field.column]
            body[new_field.name] = new_field
            mapping[new_field.column] = self.quote_name(old_field.column)
            rename_mapping[old_field.name] = new_field.name
        # Remove any deleted fields
        for field in delete_fields:
            del body[field.name]
            del mapping[field.column]
            # Remove any implicit M2M tables
            if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
                return self.delete_model(field.rel.through)
        # Work inside a new app registry
        apps = Apps()

        # Provide isolated instances of the fields to the new model body
        # Instantiating the new model with an alternate db_table will alter
        # the internal references of some of the provided fields.
        body = copy.deepcopy(body)

        # Work out the new value of unique_together, taking renames into
        # account
        if override_uniques is None:
            override_uniques = [
                [rename_mapping.get(n, n) for n in unique]
                for unique in model._meta.unique_together
            ]

        # Construct a new model for the new state
        meta_contents = {
            'app_label': model._meta.app_label,
            'db_table': model._meta.db_table + "__new",
            'unique_together': override_uniques,
            'apps': apps,
        }
        meta = type("Meta", tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = model.__module__

        temp_model = type(model._meta.object_name, model.__bases__, body)
        # Create a new table with that format. We remove things from the
        # deferred SQL that match our table name, too
        self.deferred_sql = [x for x in self.deferred_sql if model._meta.db_table not in x]
        self.create_model(temp_model)
        # Copy data from the old table
        field_maps = list(mapping.items())
        self.execute("INSERT INTO %s (%s) SELECT %s FROM %s" % (
            self.quote_name(temp_model._meta.db_table),
            ', '.join(self.quote_name(x) for x, y in field_maps),
            ', '.join(y for x, y in field_maps),
            self.quote_name(model._meta.db_table),
        ))
        # Delete the old table
        self.delete_model(model, handle_autom2m=False)
        # Rename the new to the old
        self.alter_db_table(temp_model, temp_model._meta.db_table, model._meta.db_table)
        # Run deferred SQL on correct table
        for sql in self.deferred_sql:
            self.execute(sql.replace(temp_model._meta.db_table, model._meta.db_table))
        self.deferred_sql = []
        # Fix any PK-removed field
        if restore_pk_field:
            restore_pk_field.primary_key = True

    def delete_model(self, model, handle_autom2m=True):
        if handle_autom2m:
            super(DatabaseSchemaEditor, self).delete_model(model)
        else:
            # Delete the table (and only that)
            self.execute(self.sql_delete_table % {
                "table": self.quote_name(model._meta.db_table),
            })

    def add_field(self, model, field):
        """
        Creates a field on a model.
        Usually involves adding a column, but may involve adding a
        table instead (for M2M fields)
        """
        # Special-case implicit M2M tables
        if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
            return self.create_model(field.rel.through)
        self._remake_table(model, create_fields=[field])

    def remove_field(self, model, field):
        """
        Removes a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        # M2M fields are a special case
        if isinstance(field, ManyToManyField):
            # For implicit M2M tables, delete the auto-created table
            if field.rel.through._meta.auto_created:
                self.delete_model(field.rel.through)
            # For explicit "through" M2M fields, do nothing
        # For everything else, remake.
        else:
            # It might not actually have a column behind it
            if field.db_parameters(connection=self.connection)['type'] is None:
                return
            self._remake_table(model, delete_fields=[field])

    def _alter_field(self, model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict=False):
        """Actually perform a "physical" (non-ManyToMany) field update."""
        # Alter by remaking table
        self._remake_table(model, alter_fields=[(old_field, new_field)])

    def alter_unique_together(self, model, old_unique_together, new_unique_together):
        """
        Deals with a model changing its unique_together.
        Note: The input unique_togethers must be doubly-nested, not the single-
        nested ["foo", "bar"] format.
        """
        self._remake_table(model, override_uniques=new_unique_together)

    def _alter_many_to_many(self, model, old_field, new_field, strict):
        """
        Alters M2Ms to repoint their to= endpoints.
        """
        if old_field.rel.through._meta.db_table == new_field.rel.through._meta.db_table:
            # The field name didn't change, but some options did; we have to propagate this altering.
            self._remake_table(
                old_field.rel.through,
                alter_fields=[(
                    # We need the field that points to the target model, so we can tell alter_field to change it -
                    # this is m2m_reverse_field_name() (as opposed to m2m_field_name, which points to our model)
                    old_field.rel.through._meta.get_field_by_name(old_field.m2m_reverse_field_name())[0],
                    new_field.rel.through._meta.get_field_by_name(new_field.m2m_reverse_field_name())[0],
                )],
                override_uniques=(new_field.m2m_field_name(), new_field.m2m_reverse_field_name()),
            )
            return

        # Make a new through table
        self.create_model(new_field.rel.through)
        # Copy the data across
        self.execute("INSERT INTO %s (%s) SELECT %s FROM %s" % (
            self.quote_name(new_field.rel.through._meta.db_table),
            ', '.join([
                "id",
                new_field.m2m_column_name(),
                new_field.m2m_reverse_name(),
            ]),
            ', '.join([
                "id",
                old_field.m2m_column_name(),
                old_field.m2m_reverse_name(),
            ]),
            self.quote_name(old_field.rel.through._meta.db_table),
        ))
        # Delete the old through table
        self.delete_model(old_field.rel.through)
