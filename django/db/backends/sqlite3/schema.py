from django.db.backends.schema import BaseDatabaseSchemaEditor
from django.db.models.fields.related import ManyToManyField
from django.db.models.loading import BaseAppCache


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_delete_table = "DROP TABLE %(table)s"

    def _remake_table(self, model, create_fields=[], delete_fields=[], alter_fields=[], rename_fields=[], override_uniques=None):
        """
        Shortcut to transform a model from old_model into new_model
        """
        # Work out the new fields dict / mapping
        body = dict((f.name, f) for f in model._meta.local_fields)
        mapping = dict((f.column, f.column) for f in model._meta.local_fields)
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
        # Add in any altered fields
        for (old_field, new_field) in alter_fields:
            del body[old_field.name]
            del mapping[old_field.column]
            body[new_field.name] = new_field
            mapping[new_field.column] = old_field.column
        # Remove any deleted fields
        for field in delete_fields:
            del body[field.name]
            del mapping[field.column]
        # Work inside a new AppCache
        app_cache = BaseAppCache()
        # Construct a new model for the new state
        meta_contents = {
            'app_label': model._meta.app_label,
            'db_table': model._meta.db_table + "__new",
            'unique_together': model._meta.unique_together if override_uniques is None else override_uniques,
            'app_cache': app_cache,
        }
        meta = type("Meta", tuple(), meta_contents)
        body['Meta'] = meta
        body['__module__'] = model.__module__
        temp_model = type(model._meta.object_name, model.__bases__, body)
        # Create a new table with that format
        self.create_model(temp_model)
        # Copy data from the old table
        field_maps = list(mapping.items())
        self.execute("INSERT INTO %s (%s) SELECT %s FROM %s" % (
            self.quote_name(temp_model._meta.db_table),
            ', '.join(x for x, y in field_maps),
            ', '.join(y for x, y in field_maps),
            self.quote_name(model._meta.db_table),
        ))
        # Delete the old table
        self.delete_model(model)
        # Rename the new to the old
        self.alter_db_table(model, temp_model._meta.db_table, model._meta.db_table)
        # Run deferred SQL on correct table
        for sql in self.deferred_sql:
            self.execute(sql.replace(temp_model._meta.db_table, model._meta.db_table))
        self.deferred_sql = []
        # Fix any PK-removed field
        if restore_pk_field:
            restore_pk_field.primary_key = True

    def add_field(self, model, field):
        """
        Creates a field on a model.
        Usually involves adding a column, but may involve adding a
        table instead (for M2M fields)
        """
        # Special-case implicit M2M tables
        if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
            return self.create_model(field.rel.through)
        # Detect bad field combinations
        if (not field.null and
           (not field.has_default() or field.get_default() is None) and
           not field.empty_strings_allowed):
            raise ValueError("You cannot add a null=False column without a default value on SQLite.")
        self._remake_table(model, create_fields=[field])

    def remove_field(self, model, field):
        """
        Removes a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        # Special-case implicit M2M tables
        if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
            return self.delete_model(field.rel.through)
        # For everything else, remake.
        self._remake_table(model, delete_fields=[field])

    def alter_field(self, model, old_field, new_field, strict=False):
        """
        Allows a field's type, uniqueness, nullability, default, column,
        constraints etc. to be modified.
        Requires a copy of the old field as well so we can only perform
        changes that are required.
        If strict is true, raises errors if the old column does not match old_field precisely.
        """
        old_db_params = old_field.db_parameters(connection=self.connection)
        old_type = old_db_params['type']
        new_db_params = new_field.db_parameters(connection=self.connection)
        new_type = new_db_params['type']
        if old_type is None and new_type is None and (old_field.rel.through and new_field.rel.through and old_field.rel.through._meta.auto_created and new_field.rel.through._meta.auto_created):
            return self._alter_many_to_many(model, old_field, new_field, strict)
        elif old_type is None or new_type is None:
            raise ValueError("Cannot alter field %s into %s - they are not compatible types (probably means only one is an M2M with implicit through model)" % (
                old_field,
                new_field,
            ))
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
