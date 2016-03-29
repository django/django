import codecs
import contextlib
import copy
from decimal import Decimal

from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.utils import six


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_delete_table = "DROP TABLE %(table)s"
    sql_create_inline_fk = "REFERENCES %(to_table)s (%(to_column)s)"
    sql_create_unique = "CREATE UNIQUE INDEX %(name)s ON %(table)s (%(columns)s)"
    sql_delete_unique = "DROP INDEX %(name)s"

    def __enter__(self):
        with self.connection.cursor() as c:
            # Some SQLite schema alterations need foreign key constraints to be
            # disabled. This is the default in SQLite but can be changed with a
            # build flag and might change in future, so can't be relied upon.
            # We enforce it here for the duration of the transaction.
            c.execute('PRAGMA foreign_keys')
            self._initial_pragma_fk = c.fetchone()[0]
            c.execute('PRAGMA foreign_keys = 0')
        return super(DatabaseSchemaEditor, self).__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super(DatabaseSchemaEditor, self).__exit__(exc_type, exc_value, traceback)
        with self.connection.cursor() as c:
            # Restore initial FK setting - PRAGMA values can't be parametrized
            c.execute('PRAGMA foreign_keys = %s' % int(self._initial_pragma_fk))

    def quote_value(self, value):
        # The backend "mostly works" without this function and there are use
        # cases for compiling Python without the sqlite3 libraries (e.g.
        # security hardening).
        import sqlite3
        try:
            value = sqlite3.adapt(value)
        except sqlite3.ProgrammingError:
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

    def _remake_table(self, model, create_fields=[], delete_fields=[], alter_fields=[], override_uniques=None,
                      override_indexes=None):
        """
        Shortcut to transform a model from old_model into new_model

        The essential steps are:
          1. rename the model's existing table, e.g. "app_model" to "app_model__old"
          2. create a table with the updated definition called "app_model"
          3. copy the data from the old renamed table to the new table
          4. delete the "app_model__old" table
        """
        # Self-referential fields must be recreated rather than copied from
        # the old model to ensure their remote_field.field_name doesn't refer
        # to an altered field.
        def is_self_referential(f):
            return f.is_relation and f.remote_field.model is model
        # Work out the new fields dict / mapping
        body = {
            f.name: f.clone() if is_self_referential(f) else f
            for f in model._meta.local_concrete_fields
        }
        # Since mapping might mix column names and default values,
        # its values must be already quoted.
        mapping = {f.column: self.quote_name(f.column) for f in model._meta.local_concrete_fields}
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
            # Choose a default and insert it into the copy map
            if not field.many_to_many and field.concrete:
                mapping[field.column] = self.quote_value(
                    self.effective_default(field)
                )
        # Add in any altered fields
        for (old_field, new_field) in alter_fields:
            body.pop(old_field.name, None)
            mapping.pop(old_field.column, None)
            body[new_field.name] = new_field
            if old_field.null and not new_field.null:
                case_sql = "coalesce(%(col)s, %(default)s)" % {
                    'col': self.quote_name(old_field.column),
                    'default': self.quote_value(self.effective_default(new_field))
                }
                mapping[new_field.column] = case_sql
            else:
                mapping[new_field.column] = self.quote_name(old_field.column)
            rename_mapping[old_field.name] = new_field.name
        # Remove any deleted fields
        for field in delete_fields:
            del body[field.name]
            del mapping[field.column]
            # Remove any implicit M2M tables
            if field.many_to_many and field.remote_field.through._meta.auto_created:
                return self.delete_model(field.remote_field.through)
        # Work inside a new app registry
        apps = Apps()

        # Provide isolated instances of the fields to the new model body so
        # that the existing model's internals aren't interfered with when
        # the dummy model is constructed.
        body = copy.deepcopy(body)

        # Work out the new value of unique_together, taking renames into
        # account
        if override_uniques is None:
            override_uniques = [
                [rename_mapping.get(n, n) for n in unique]
                for unique in model._meta.unique_together
            ]

        # Work out the new value for index_together, taking renames into
        # account
        if override_indexes is None:
            override_indexes = [
                [rename_mapping.get(n, n) for n in index]
                for index in model._meta.index_together
            ]

        # Construct a new model for the new state
        meta_contents = {
            'app_label': model._meta.app_label,
            'db_table': model._meta.db_table,
            'unique_together': override_uniques,
            'index_together': override_indexes,
            'apps': apps,
        }
        meta = type("Meta", tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = model.__module__

        temp_model = type(model._meta.object_name, model.__bases__, body)

        # We need to modify model._meta.db_table, but everything explodes
        # if the change isn't reversed before the end of this method. This
        # context manager helps us avoid that situation.
        @contextlib.contextmanager
        def altered_table_name(model, temporary_table_name):
            original_table_name = model._meta.db_table
            model._meta.db_table = temporary_table_name
            yield
            model._meta.db_table = original_table_name

        with altered_table_name(model, model._meta.db_table + "__old"):
            # Rename the old table to make way for the new
            self.alter_db_table(model, temp_model._meta.db_table, model._meta.db_table)

            # Create a new table with the updated schema. We remove things
            # from the deferred SQL that match our table name, too
            self.deferred_sql = [x for x in self.deferred_sql if temp_model._meta.db_table not in x]
            self.create_model(temp_model)

            # Copy data from the old table into the new table
            field_maps = list(mapping.items())
            self.execute("INSERT INTO %s (%s) SELECT %s FROM %s" % (
                self.quote_name(temp_model._meta.db_table),
                ', '.join(self.quote_name(x) for x, y in field_maps),
                ', '.join(y for x, y in field_maps),
                self.quote_name(model._meta.db_table),
            ))

            # Delete the old table
            self.delete_model(model, handle_autom2m=False)

        # Run deferred SQL on correct table
        for sql in self.deferred_sql:
            self.execute(sql)
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
        if field.many_to_many and field.remote_field.through._meta.auto_created:
            return self.create_model(field.remote_field.through)
        self._remake_table(model, create_fields=[field])

    def remove_field(self, model, field):
        """
        Removes a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        # M2M fields are a special case
        if field.many_to_many:
            # For implicit M2M tables, delete the auto-created table
            if field.remote_field.through._meta.auto_created:
                self.delete_model(field.remote_field.through)
            # For explicit "through" M2M fields, do nothing
        # For everything else, remake.
        else:
            # It might not actually have a column behind it
            if field.db_parameters(connection=self.connection)['type'] is None:
                return
            self._remake_table(model, delete_fields=[field])

    def _alter_field(self, model, old_field, new_field, old_type, new_type,
                     old_db_params, new_db_params, strict=False):
        """Actually perform a "physical" (non-ManyToMany) field update."""
        # Alter by remaking table
        self._remake_table(model, alter_fields=[(old_field, new_field)])

    def alter_index_together(self, model, old_index_together, new_index_together):
        """
        Deals with a model changing its index_together.
        Note: The input index_togethers must be doubly-nested, not the single-
        nested ["foo", "bar"] format.
        """
        self._remake_table(model, override_indexes=new_index_together)

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
        if old_field.remote_field.through._meta.db_table == new_field.remote_field.through._meta.db_table:
            # The field name didn't change, but some options did; we have to propagate this altering.
            self._remake_table(
                old_field.remote_field.through,
                alter_fields=[(
                    # We need the field that points to the target model, so we can tell alter_field to change it -
                    # this is m2m_reverse_field_name() (as opposed to m2m_field_name, which points to our model)
                    old_field.remote_field.through._meta.get_field(old_field.m2m_reverse_field_name()),
                    new_field.remote_field.through._meta.get_field(new_field.m2m_reverse_field_name()),
                )],
                override_uniques=(new_field.m2m_field_name(), new_field.m2m_reverse_field_name()),
            )
            return

        # Make a new through table
        self.create_model(new_field.remote_field.through)
        # Copy the data across
        self.execute("INSERT INTO %s (%s) SELECT %s FROM %s" % (
            self.quote_name(new_field.remote_field.through._meta.db_table),
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
            self.quote_name(old_field.remote_field.through._meta.db_table),
        ))
        # Delete the old through table
        self.delete_model(old_field.remote_field.through)
