import hashlib
import operator

from django.db.backends.creation import BaseDatabaseCreation
from django.db.backends.utils import truncate_name
from django.db.models.fields.related import ManyToManyField
from django.db.transaction import atomic
from django.utils.encoding import force_bytes
from django.utils.log import getLogger
from django.utils.six.moves import reduce
from django.utils import six

logger = getLogger('django.db.backends.schema')


class BaseDatabaseSchemaEditor(object):
    """
    This class (and its subclasses) are responsible for emitting schema-changing
    statements to the databases - model creation/removal/alteration, field
    renaming, index fiddling, and so on.

    It is intended to eventually completely replace DatabaseCreation.

    This class should be used by creating an instance for each set of schema
    changes (e.g. a syncdb run, a migration file), and by first calling start(),
    then the relevant actions, and then commit(). This is necessary to allow
    things like circular foreign key references - FKs will only be created once
    commit() is called.
    """

    # Overrideable SQL templates
    sql_create_table = "CREATE TABLE %(table)s (%(definition)s)"
    sql_create_table_unique = "UNIQUE (%(columns)s)"
    sql_rename_table = "ALTER TABLE %(old_table)s RENAME TO %(new_table)s"
    sql_retablespace_table = "ALTER TABLE %(table)s SET TABLESPACE %(new_tablespace)s"
    sql_delete_table = "DROP TABLE %(table)s CASCADE"

    sql_create_column = "ALTER TABLE %(table)s ADD COLUMN %(column)s %(definition)s"
    sql_alter_column = "ALTER TABLE %(table)s %(changes)s"
    sql_alter_column_type = "ALTER COLUMN %(column)s TYPE %(type)s"
    sql_alter_column_null = "ALTER COLUMN %(column)s DROP NOT NULL"
    sql_alter_column_not_null = "ALTER COLUMN %(column)s SET NOT NULL"
    sql_alter_column_default = "ALTER COLUMN %(column)s SET DEFAULT %(default)s"
    sql_alter_column_no_default = "ALTER COLUMN %(column)s DROP DEFAULT"
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s CASCADE"
    sql_rename_column = "ALTER TABLE %(table)s RENAME COLUMN %(old_column)s TO %(new_column)s"

    sql_create_check = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s CHECK (%(check)s)"
    sql_delete_check = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_unique = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s UNIQUE (%(columns)s)"
    sql_delete_unique = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s) DEFERRABLE INITIALLY DEFERRED"
    sql_create_inline_fk = None
    sql_delete_fk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s)%(extra)s"
    sql_delete_index = "DROP INDEX %(name)s"

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(columns)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    def __init__(self, connection, collect_sql=False):
        self.connection = connection
        self.collect_sql = collect_sql
        if self.collect_sql:
            self.collected_sql = []

    # State-managing methods

    def __enter__(self):
        self.deferred_sql = []
        if self.connection.features.can_rollback_ddl:
            self.atomic = atomic(self.connection.alias)
            self.atomic.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            for sql in self.deferred_sql:
                self.execute(sql)
        if self.connection.features.can_rollback_ddl:
            self.atomic.__exit__(exc_type, exc_value, traceback)

    # Core utility functions

    def execute(self, sql, params=[]):
        """
        Executes the given SQL statement, with optional parameters.
        """
        # Log the command we're running, then run it
        logger.debug("%s; (params %r)" % (sql, params))
        if self.collect_sql:
            self.collected_sql.append((sql % tuple(map(self.quote_value, params))) + ";")
        else:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)

    def quote_name(self, name):
        return self.connection.ops.quote_name(name)

    # Field <-> database mapping functions

    def column_sql(self, model, field, include_default=False):
        """
        Takes a field and returns its column definition.
        The field must already have had set_attributes_from_name called.
        """
        # Get the column's type and use that as the basis of the SQL
        db_params = field.db_parameters(connection=self.connection)
        sql = db_params['type']
        params = []
        # Check for fields that aren't actually columns (e.g. M2M)
        if sql is None:
            return None, None
        # Work out nullability
        null = field.null
        # If we were told to include a default value, do so
        default_value = self.effective_default(field)
        include_default = include_default and not self.skip_default(field)
        if include_default and default_value is not None:
            if self.connection.features.requires_literal_defaults:
                # Some databases can't take defaults as a parameter (oracle)
                # If this is the case, the individual schema backend should
                # implement prepare_default
                sql += " DEFAULT %s" % self.prepare_default(default_value)
            else:
                sql += " DEFAULT %s"
                params += [default_value]
        # Oracle treats the empty string ('') as null, so coerce the null
        # option whenever '' is a possible value.
        if (field.empty_strings_allowed and not field.primary_key and
                self.connection.features.interprets_empty_strings_as_nulls):
            null = True
        if null and not self.connection.features.implied_column_null:
            sql += " NULL"
        elif not null:
            sql += " NOT NULL"
        # Primary key/unique outputs
        if field.primary_key:
            sql += " PRIMARY KEY"
        elif field.unique:
            sql += " UNIQUE"
        # Optionally add the tablespace if it's an implicitly indexed column
        tablespace = field.db_tablespace or model._meta.db_tablespace
        if tablespace and self.connection.features.supports_tablespaces and field.unique:
            sql += " %s" % self.connection.ops.tablespace_sql(tablespace, inline=True)
        # Return the sql
        return sql, params

    def skip_default(self, field):
        """
        Some backends don't accept default values for certain columns types
        (i.e. MySQL longtext and longblob).
        """
        return False

    def prepare_default(self, value):
        """
        Only used for backends which have requires_literal_defaults feature
        """
        raise NotImplementedError('subclasses of BaseDatabaseSchemaEditor for backends which have requires_literal_defaults must provide a prepare_default() method')

    def effective_default(self, field):
        """
        Returns a field's effective database default value
        """
        if field.has_default():
            default = field.get_default()
        elif not field.null and field.blank and field.empty_strings_allowed:
            if field.get_internal_type() == "BinaryField":
                default = six.binary_type()
            else:
                default = six.text_type()
        else:
            default = None
        # If it's a callable, call it
        if six.callable(default):
            default = default()
        # Run it through the field's get_db_prep_save method so we can send it
        # to the database.
        default = field.get_db_prep_save(default, self.connection)
        return default

    def quote_value(self, value):
        """
        Returns a quoted version of the value so it's safe to use in an SQL
        string. This is not safe against injection from user code; it is
        intended only for use in making SQL scripts or preparing default values
        for particularly tricky backends (defaults are not user-defined, though,
        so this is safe).
        """
        raise NotImplementedError()

    # Actions

    def create_model(self, model):
        """
        Takes a model and creates a table for it in the database.
        Will also create any accompanying indexes or unique constraints.
        """
        # Create column SQL, add FK deferreds if needed
        column_sqls = []
        params = []
        for field in model._meta.local_fields:
            # SQL
            definition, extra_params = self.column_sql(model, field)
            if definition is None:
                continue
            # Check constraints can go on the column SQL here
            db_params = field.db_parameters(connection=self.connection)
            if db_params['check']:
                definition += " CHECK (%s)" % db_params['check']
            # Autoincrement SQL (for backends with inline variant)
            col_type_suffix = field.db_type_suffix(connection=self.connection)
            if col_type_suffix:
                definition += " %s" % col_type_suffix
            params.extend(extra_params)
            # Indexes
            if field.db_index and not field.unique:
                self.deferred_sql.append(
                    self.sql_create_index % {
                        "name": self._create_index_name(model, [field.column], suffix=""),
                        "table": self.quote_name(model._meta.db_table),
                        "columns": self.quote_name(field.column),
                        "extra": "",
                    }
                )
            # FK
            if field.rel and field.db_constraint:
                to_table = field.rel.to._meta.db_table
                to_column = field.rel.to._meta.get_field(field.rel.field_name).column
                if self.connection.features.supports_foreign_keys:
                    self.deferred_sql.append(
                        self.sql_create_fk % {
                            "name": self._create_index_name(model, [field.column], suffix="_fk_%s_%s" % (to_table, to_column)),
                            "table": self.quote_name(model._meta.db_table),
                            "column": self.quote_name(field.column),
                            "to_table": self.quote_name(to_table),
                            "to_column": self.quote_name(to_column),
                        }
                    )
                elif self.sql_create_inline_fk:
                    definition += " " + self.sql_create_inline_fk % {
                        "to_table": self.quote_name(to_table),
                        "to_column": self.quote_name(to_column),
                    }
            # Add the SQL to our big list
            column_sqls.append("%s %s" % (
                self.quote_name(field.column),
                definition,
            ))
            # Autoincrement SQL (for backends with post table definition variant)
            if field.get_internal_type() == "AutoField":
                autoinc_sql = self.connection.ops.autoinc_sql(model._meta.db_table, field.column)
                if autoinc_sql:
                    self.deferred_sql.extend(autoinc_sql)
        # Add any unique_togethers
        for fields in model._meta.unique_together:
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            column_sqls.append(self.sql_create_table_unique % {
                "columns": ", ".join(self.quote_name(column) for column in columns),
            })
        # Make the table
        sql = self.sql_create_table % {
            "table": self.quote_name(model._meta.db_table),
            "definition": ", ".join(column_sqls)
        }
        self.execute(sql, params)
        # Add any index_togethers
        for fields in model._meta.index_together:
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            self.execute(self.sql_create_index % {
                "table": self.quote_name(model._meta.db_table),
                "name": self._create_index_name(model, columns, suffix="_idx"),
                "columns": ", ".join(self.quote_name(column) for column in columns),
                "extra": "",
            })
        # Make M2M tables
        for field in model._meta.local_many_to_many:
            if field.rel.through._meta.auto_created:
                self.create_model(field.rel.through)

    def delete_model(self, model):
        """
        Deletes a model from the database.
        """
        # Handle auto-created intermediary models
        for field in model._meta.local_many_to_many:
            if field.rel.through._meta.auto_created:
                self.delete_model(field.rel.through)

        # Delete the table
        self.execute(self.sql_delete_table % {
            "table": self.quote_name(model._meta.db_table),
        })

    def alter_unique_together(self, model, old_unique_together, new_unique_together):
        """
        Deals with a model changing its unique_together.
        Note: The input unique_togethers must be doubly-nested, not the single-
        nested ["foo", "bar"] format.
        """
        olds = set(tuple(fields) for fields in old_unique_together)
        news = set(tuple(fields) for fields in new_unique_together)
        # Deleted uniques
        for fields in olds.difference(news):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            constraint_names = self._constraint_names(model, columns, unique=True)
            if len(constraint_names) != 1:
                raise ValueError("Found wrong number (%s) of constraints for %s(%s)" % (
                    len(constraint_names),
                    model._meta.db_table,
                    ", ".join(columns),
                ))
            self.execute(
                self.sql_delete_unique % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": constraint_names[0],
                },
            )
        # Created uniques
        for fields in news.difference(olds):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            self.execute(self.sql_create_unique % {
                "table": self.quote_name(model._meta.db_table),
                "name": self._create_index_name(model, columns, suffix="_uniq"),
                "columns": ", ".join(self.quote_name(column) for column in columns),
            })

    def alter_index_together(self, model, old_index_together, new_index_together):
        """
        Deals with a model changing its index_together.
        Note: The input index_togethers must be doubly-nested, not the single-
        nested ["foo", "bar"] format.
        """
        olds = set(tuple(fields) for fields in old_index_together)
        news = set(tuple(fields) for fields in new_index_together)
        # Deleted indexes
        for fields in olds.difference(news):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            constraint_names = self._constraint_names(model, list(columns), index=True)
            if len(constraint_names) != 1:
                raise ValueError("Found wrong number (%s) of constraints for %s(%s)" % (
                    len(constraint_names),
                    model._meta.db_table,
                    ", ".join(columns),
                ))
            self.execute(
                self.sql_delete_index % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": constraint_names[0],
                },
            )
        # Created indexes
        for fields in news.difference(olds):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            self.execute(self.sql_create_index % {
                "table": self.quote_name(model._meta.db_table),
                "name": self._create_index_name(model, columns, suffix="_idx"),
                "columns": ", ".join(self.quote_name(column) for column in columns),
                "extra": "",
            })

    def alter_db_table(self, model, old_db_table, new_db_table):
        """
        Renames the table a model points to.
        """
        if old_db_table == new_db_table:
            return
        self.execute(self.sql_rename_table % {
            "old_table": self.quote_name(old_db_table),
            "new_table": self.quote_name(new_db_table),
        })

    def alter_db_tablespace(self, model, old_db_tablespace, new_db_tablespace):
        """
        Moves a model's table between tablespaces
        """
        self.execute(self.sql_retablespace_table % {
            "table": self.quote_name(model._meta.db_table),
            "old_tablespace": self.quote_name(old_db_tablespace),
            "new_tablespace": self.quote_name(new_db_tablespace),
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
        # Get the column's definition
        definition, params = self.column_sql(model, field, include_default=True)
        # It might not actually have a column behind it
        if definition is None:
            return
        # Check constraints can go on the column SQL here
        db_params = field.db_parameters(connection=self.connection)
        if db_params['check']:
            definition += " CHECK (%s)" % db_params['check']
        # Build the SQL and run it
        sql = self.sql_create_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
            "definition": definition,
        }
        self.execute(sql, params)
        # Drop the default if we need to
        # (Django usually does not use in-database defaults)
        if not self.skip_default(field) and field.default is not None:
            sql = self.sql_alter_column % {
                "table": self.quote_name(model._meta.db_table),
                "changes": self.sql_alter_column_no_default % {
                    "column": self.quote_name(field.column),
                }
            }
            self.execute(sql)
        # Add an index, if required
        if field.db_index and not field.unique:
            self.deferred_sql.append(
                self.sql_create_index % {
                    "name": self._create_index_name(model, [field.column], suffix=""),
                    "table": self.quote_name(model._meta.db_table),
                    "columns": self.quote_name(field.column),
                    "extra": "",
                }
            )
        # Add any FK constraints later
        if field.rel and self.connection.features.supports_foreign_keys and field.db_constraint:
            to_table = field.rel.to._meta.db_table
            to_column = field.rel.to._meta.get_field(field.rel.field_name).column
            self.deferred_sql.append(
                self.sql_create_fk % {
                    "name": self._create_index_name(model, [field.column], suffix="_fk_%s_%s" % (to_table, to_column)),
                    "table": self.quote_name(model._meta.db_table),
                    "column": self.quote_name(field.column),
                    "to_table": self.quote_name(to_table),
                    "to_column": self.quote_name(to_column),
                }
            )
        # Reset connection if required
        if self.connection.features.connection_persists_old_columns:
            self.connection.close()

    def remove_field(self, model, field):
        """
        Removes a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        # Special-case implicit M2M tables
        if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
            return self.delete_model(field.rel.through)
        # It might not actually have a column behind it
        if field.db_parameters(connection=self.connection)['type'] is None:
            return
        # Drop any FK constraints, MySQL requires explicit deletion
        if field.rel:
            fk_names = self._constraint_names(model, [field.column], foreign_key=True)
            for fk_name in fk_names:
                self.execute(
                    self.sql_delete_fk % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": fk_name,
                    }
                )
        # Delete the column
        sql = self.sql_delete_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
        }
        self.execute(sql)
        # Reset connection if required
        if self.connection.features.connection_persists_old_columns:
            self.connection.close()

    def alter_field(self, model, old_field, new_field, strict=False):
        """
        Allows a field's type, uniqueness, nullability, default, column,
        constraints etc. to be modified.
        Requires a copy of the old field as well so we can only perform
        changes that are required.
        If strict is true, raises errors if the old column does not match old_field precisely.
        """
        # Ensure this field is even column-based
        old_db_params = old_field.db_parameters(connection=self.connection)
        old_type = old_db_params['type']
        new_db_params = new_field.db_parameters(connection=self.connection)
        new_type = new_db_params['type']
        if (old_type is None and old_field.rel is None) or (new_type is None and new_field.rel is None):
            raise ValueError("Cannot alter field %s into %s - they do not properly define db_type (are you using PostGIS 1.5 or badly-written custom fields?)" % (
                old_field,
                new_field,
            ))
        elif old_type is None and new_type is None and (old_field.rel.through and new_field.rel.through and old_field.rel.through._meta.auto_created and new_field.rel.through._meta.auto_created):
            return self._alter_many_to_many(model, old_field, new_field, strict)
        elif old_type is None and new_type is None and (old_field.rel.through and new_field.rel.through and not old_field.rel.through._meta.auto_created and not new_field.rel.through._meta.auto_created):
            # Both sides have through models; this is a no-op.
            return
        elif old_type is None or new_type is None:
            raise ValueError("Cannot alter field %s into %s - they are not compatible types (you cannot alter to or from M2M fields, or add or remove through= on M2M fields)" % (
                old_field,
                new_field,
            ))

        self._alter_field(model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict)

    def _alter_field(self, model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict=False):
        """Actually perform a "physical" (non-ManyToMany) field update."""

        # Has unique been removed?
        if old_field.unique and (not new_field.unique or (not old_field.primary_key and new_field.primary_key)):
            # Find the unique constraint for this field
            constraint_names = self._constraint_names(model, [old_field.column], unique=True)
            if strict and len(constraint_names) != 1:
                raise ValueError("Found wrong number (%s) of unique constraints for %s.%s" % (
                    len(constraint_names),
                    model._meta.db_table,
                    old_field.column,
                ))
            for constraint_name in constraint_names:
                self.execute(
                    self.sql_delete_unique % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": constraint_name,
                    },
                )
        # Drop any FK constraints, we'll remake them later
        fks_dropped = set()
        if old_field.rel and old_field.db_constraint:
            fk_names = self._constraint_names(model, [old_field.column], foreign_key=True)
            if strict and len(fk_names) != 1:
                raise ValueError("Found wrong number (%s) of foreign key constraints for %s.%s" % (
                    len(fk_names),
                    model._meta.db_table,
                    old_field.column,
                ))
            for fk_name in fk_names:
                fks_dropped.add((old_field.column,))
                self.execute(
                    self.sql_delete_fk % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": fk_name,
                    }
                )
        # Drop incoming FK constraints if we're a primary key and things are going
        # to change.
        if old_field.primary_key and new_field.primary_key and old_type != new_type:
            for rel in new_field.model._meta.get_all_related_objects():
                rel_fk_names = self._constraint_names(rel.model, [rel.field.column], foreign_key=True)
                for fk_name in rel_fk_names:
                    self.execute(
                        self.sql_delete_fk % {
                            "table": self.quote_name(rel.model._meta.db_table),
                            "name": fk_name,
                        }
                    )
        # Removed an index?
        if old_field.db_index and not new_field.db_index and not old_field.unique and not (not new_field.unique and old_field.unique):
            # Find the index for this field
            index_names = self._constraint_names(model, [old_field.column], index=True)
            if strict and len(index_names) != 1:
                raise ValueError("Found wrong number (%s) of indexes for %s.%s" % (
                    len(index_names),
                    model._meta.db_table,
                    old_field.column,
                ))
            for index_name in index_names:
                self.execute(
                    self.sql_delete_index % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": index_name,
                    }
                )
        # Change check constraints?
        if old_db_params['check'] != new_db_params['check'] and old_db_params['check']:
            constraint_names = self._constraint_names(model, [old_field.column], check=True)
            if strict and len(constraint_names) != 1:
                raise ValueError("Found wrong number (%s) of check constraints for %s.%s" % (
                    len(constraint_names),
                    model._meta.db_table,
                    old_field.column,
                ))
            for constraint_name in constraint_names:
                self.execute(
                    self.sql_delete_check % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": constraint_name,
                    }
                )
        # Have they renamed the column?
        if old_field.column != new_field.column:
            self.execute(self.sql_rename_column % {
                "table": self.quote_name(model._meta.db_table),
                "old_column": self.quote_name(old_field.column),
                "new_column": self.quote_name(new_field.column),
                "type": new_type,
            })
        # Next, start accumulating actions to do
        actions = []
        post_actions = []
        # Type change?
        if old_type != new_type:
            fragment, other_actions = self._alter_column_type_sql(model._meta.db_table, new_field.column, new_type)
            actions.append(fragment)
            post_actions.extend(other_actions)
        # Default change?
        old_default = self.effective_default(old_field)
        new_default = self.effective_default(new_field)
        if old_default != new_default:
            if new_default is None:
                actions.append((
                    self.sql_alter_column_no_default % {
                        "column": self.quote_name(new_field.column),
                    },
                    [],
                ))
            else:
                if self.connection.features.requires_literal_defaults:
                    # Some databases can't take defaults as a parameter (oracle)
                    # If this is the case, the individual schema backend should
                    # implement prepare_default
                    actions.append((
                        self.sql_alter_column_default % {
                            "column": self.quote_name(new_field.column),
                            "default": self.prepare_default(new_default),
                        },
                        [],
                    ))
                else:
                    actions.append((
                        self.sql_alter_column_default % {
                            "column": self.quote_name(new_field.column),
                            "default": "%s",
                        },
                        [new_default],
                    ))
        # Nullability change?
        if old_field.null != new_field.null:
            if new_field.null:
                actions.append((
                    self.sql_alter_column_null % {
                        "column": self.quote_name(new_field.column),
                        "type": new_type,
                    },
                    [],
                ))
            else:
                actions.append((
                    self.sql_alter_column_not_null % {
                        "column": self.quote_name(new_field.column),
                        "type": new_type,
                    },
                    [],
                ))
        if actions:
            # Combine actions together if we can (e.g. postgres)
            if self.connection.features.supports_combined_alters:
                sql, params = tuple(zip(*actions))
                actions = [(", ".join(sql), reduce(operator.add, params))]
            # Apply those actions
            for sql, params in actions:
                self.execute(
                    self.sql_alter_column % {
                        "table": self.quote_name(model._meta.db_table),
                        "changes": sql,
                    },
                    params,
                )
        if post_actions:
            for sql, params in post_actions:
                self.execute(sql, params)
        # Added a unique?
        if not old_field.unique and new_field.unique:
            self.execute(
                self.sql_create_unique % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self._create_index_name(model, [new_field.column], suffix="_uniq"),
                    "columns": self.quote_name(new_field.column),
                }
            )
        # Added an index?
        if not old_field.db_index and new_field.db_index and not new_field.unique and not (not old_field.unique and new_field.unique):
            self.execute(
                self.sql_create_index % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self._create_index_name(model, [new_field.column], suffix="_uniq"),
                    "columns": self.quote_name(new_field.column),
                    "extra": "",
                }
            )
        # Type alteration on primary key? Then we need to alter the column
        # referring to us.
        rels_to_update = []
        if old_field.primary_key and new_field.primary_key and old_type != new_type:
            rels_to_update.extend(new_field.model._meta.get_all_related_objects())
        # Changed to become primary key?
        # Note that we don't detect unsetting of a PK, as we assume another field
        # will always come along and replace it.
        if not old_field.primary_key and new_field.primary_key:
            # First, drop the old PK
            constraint_names = self._constraint_names(model, primary_key=True)
            if strict and len(constraint_names) != 1:
                raise ValueError("Found wrong number (%s) of PK constraints for %s" % (
                    len(constraint_names),
                    model._meta.db_table,
                ))
            for constraint_name in constraint_names:
                self.execute(
                    self.sql_delete_pk % {
                        "table": self.quote_name(model._meta.db_table),
                        "name": constraint_name,
                    },
                )
            # Make the new one
            self.execute(
                self.sql_create_pk % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self._create_index_name(model, [new_field.column], suffix="_pk"),
                    "columns": self.quote_name(new_field.column),
                }
            )
            # Update all referencing columns
            rels_to_update.extend(new_field.model._meta.get_all_related_objects())
        # Handle our type alters on the other end of rels from the PK stuff above
        for rel in rels_to_update:
            rel_db_params = rel.field.db_parameters(connection=self.connection)
            rel_type = rel_db_params['type']
            self.execute(
                self.sql_alter_column % {
                    "table": self.quote_name(rel.model._meta.db_table),
                    "changes": self.sql_alter_column_type % {
                        "column": self.quote_name(rel.field.column),
                        "type": rel_type,
                    }
                }
            )
        # Does it have a foreign key?
        if new_field.rel and \
           (fks_dropped or (old_field.rel and not old_field.db_constraint)) and \
           new_field.db_constraint:
            to_table = new_field.rel.to._meta.db_table
            to_column = new_field.rel.get_related_field().column
            self.execute(
                self.sql_create_fk % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self._create_index_name(model, [new_field.column], suffix="_fk_%s_%s" % (to_table, to_column)),
                    "column": self.quote_name(new_field.column),
                    "to_table": self.quote_name(to_table),
                    "to_column": self.quote_name(to_column),
                }
            )
        # Rebuild FKs that pointed to us if we previously had to drop them
        if old_field.primary_key and new_field.primary_key and old_type != new_type:
            for rel in new_field.model._meta.get_all_related_objects():
                self.execute(
                    self.sql_create_fk % {
                        "table": self.quote_name(rel.model._meta.db_table),
                        "name": self._create_index_name(rel.model, [rel.field.column], suffix="_fk"),
                        "column": self.quote_name(rel.field.column),
                        "to_table": self.quote_name(model._meta.db_table),
                        "to_column": self.quote_name(new_field.column),
                    }
                )
        # Does it have check constraints we need to add?
        if old_db_params['check'] != new_db_params['check'] and new_db_params['check']:
            self.execute(
                self.sql_create_check % {
                    "table": self.quote_name(model._meta.db_table),
                    "name": self._create_index_name(model, [new_field.column], suffix="_check"),
                    "column": self.quote_name(new_field.column),
                    "check": new_db_params['check'],
                }
            )
        # Drop the default if we need to
        # (Django usually does not use in-database defaults)
        if not self.skip_default(new_field) and new_field.default is not None:
            sql = self.sql_alter_column % {
                "table": self.quote_name(model._meta.db_table),
                "changes": self.sql_alter_column_no_default % {
                    "column": self.quote_name(new_field.column),
                }
            }
            self.execute(sql)
        # Reset connection if required
        if self.connection.features.connection_persists_old_columns:
            self.connection.close()

    def _alter_column_type_sql(self, table, column, type):
        """
        Hook to specialize column type alteration for different backends,
        for cases when a creation type is different to an alteration type
        (e.g. SERIAL in PostgreSQL, PostGIS fields).

        Should return two things; an SQL fragment of (sql, params) to insert
        into an ALTER TABLE statement, and a list of extra (sql, params) tuples
        to run once the field is altered.
        """
        return (
            (
                self.sql_alter_column_type % {
                    "column": self.quote_name(column),
                    "type": type,
                },
                [],
            ),
            [],
        )

    def _alter_many_to_many(self, model, old_field, new_field, strict):
        """
        Alters M2Ms to repoint their to= endpoints.
        """
        # Rename the through table
        if old_field.rel.through._meta.db_table != new_field.rel.through._meta.db_table:
            self.alter_db_table(old_field.rel.through, old_field.rel.through._meta.db_table, new_field.rel.through._meta.db_table)
        # Repoint the FK to the other side
        self.alter_field(
            new_field.rel.through,
            # We need the field that points to the target model, so we can tell alter_field to change it -
            # this is m2m_reverse_field_name() (as opposed to m2m_field_name, which points to our model)
            old_field.rel.through._meta.get_field_by_name(old_field.m2m_reverse_field_name())[0],
            new_field.rel.through._meta.get_field_by_name(new_field.m2m_reverse_field_name())[0],
        )

    def _create_index_name(self, model, column_names, suffix=""):
        """
        Generates a unique name for an index/unique constraint.
        """
        # If there is just one column in the index, use a default algorithm from Django
        if len(column_names) == 1 and not suffix:
            return truncate_name(
                '%s_%s' % (model._meta.db_table, BaseDatabaseCreation._digest(column_names[0])),
                self.connection.ops.max_name_length()
            )
        # Else generate the name for the index using a different algorithm
        table_name = model._meta.db_table.replace('"', '').replace('.', '_')
        index_unique_name = '_%x' % abs(hash((table_name, ','.join(column_names))))
        max_length = self.connection.ops.max_name_length() or 200
        # If the index name is too long, truncate it
        index_name = ('%s_%s%s%s' % (table_name, column_names[0], index_unique_name, suffix)).replace('"', '').replace('.', '_')
        if len(index_name) > max_length:
            part = ('_%s%s%s' % (column_names[0], index_unique_name, suffix))
            index_name = '%s%s' % (table_name[:(max_length - len(part))], part)
        # It shouldn't start with an underscore (Oracle hates this)
        if index_name[0] == "_":
            index_name = index_name[1:]
        # If it's STILL too long, just hash it down
        if len(index_name) > max_length:
            index_name = hashlib.md5(force_bytes(index_name)).hexdigest()[:max_length]
        # It can't start with a number on Oracle, so prepend D if we need to
        if index_name[0].isdigit():
            index_name = "D%s" % index_name[:-1]
        return index_name

    def _constraint_names(self, model, column_names=None, unique=None, primary_key=None, index=None, foreign_key=None, check=None):
        """
        Returns all constraint names matching the columns and conditions
        """
        column_names = list(column_names) if column_names else None
        with self.connection.cursor() as cursor:
            constraints = self.connection.introspection.get_constraints(cursor, model._meta.db_table)
        result = []
        for name, infodict in constraints.items():
            if column_names is None or column_names == infodict['columns']:
                if unique is not None and infodict['unique'] != unique:
                    continue
                if primary_key is not None and infodict['primary_key'] != primary_key:
                    continue
                if index is not None and infodict['index'] != index:
                    continue
                if check is not None and infodict['check'] != check:
                    continue
                if foreign_key is not None and not infodict['foreign_key']:
                    continue
                result.append(name)
        return result
