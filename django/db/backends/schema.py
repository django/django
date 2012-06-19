import sys
import time

from django.conf import settings
from django.db import transaction
from django.db.utils import load_backend
from django.utils.log import getLogger
from django.db.models.fields.related import ManyToManyField

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
    sql_rename_table = "ALTER TABLE %(old_table)s RENAME TO %(new_table)s"
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

    sql_create_check = "ADD CONSTRAINT %(name)s CHECK (%(check)s)"
    sql_delete_check = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_unique = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s UNIQUE (%(columns)s)"
    sql_delete_unique = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s) DEFERRABLE INITIALLY DEFERRED"
    sql_delete_fk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_index = "CREATE %(unique)s INDEX %(name)s ON %(table)s (%(columns)s)%s;"
    sql_delete_index = "DROP INDEX %(name)s"

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(constraint)s PRIMARY KEY (%(columns)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP CONSTRAINT %(constraint)s"

    def __init__(self, connection):
        self.connection = connection

    # State-managing methods

    def start(self):
        "Marks the start of a schema-altering run"
        self.deferred_sql = []
        self.connection.commit_unless_managed()
        self.connection.enter_transaction_management()
        self.connection.managed(True)

    def commit(self):
        "Finishes a schema-altering run"
        for sql in self.deferred_sql:
            self.execute(sql)
        self.connection.commit()
        self.connection.leave_transaction_management()

    def rollback(self):
        "Tries to roll back a schema-altering run. Call instead of commit()"
        if not self.connection.features.can_rollback_ddl:
            raise RuntimeError("Cannot rollback schema changes on this backend")
        self.connection.rollback()
        self.connection.leave_transaction_management()

    # Core utility functions

    def execute(self, sql, params=[], fetch_results=False):
        """
        Executes the given SQL statement, with optional parameters.
        """
        # Get the cursor
        cursor = self.connection.cursor()
        # Log the command we're running, then run it
        logger.info("%s; (params %r)" % (sql, params))
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
        sql = field.db_type(connection=self.connection)
        params = []
        # Check for fields that aren't actually columns (e.g. M2M)
        if sql is None:
            return None
        # Optionally add the tablespace if it's an implicitly indexed column
        tablespace = field.db_tablespace or model._meta.db_tablespace
        if tablespace and self.connection.features.supports_tablespaces and field.unique:
            sql += " %s" % self.connection.ops.tablespace_sql(tablespace, inline=True)
        # Work out nullability
        null = field.null
        # Oracle treats the empty string ('') as null, so coerce the null
        # option whenever '' is a possible value.
        if (field.empty_strings_allowed and not field.primary_key and
                self.connection.features.interprets_empty_strings_as_nulls):
            null = True
        if null:
            sql += " NULL"
        else:
            sql += " NOT NULL"
        # Primary key/unique outputs
        if field.primary_key:
            sql += " PRIMARY KEY"
        elif field.unique:
            sql += " UNIQUE"
        # If we were told to include a default value, do so
        if include_default:
            sql += " DEFAULT %s"
            params += [self.effective_default(field)]
        # Return the sql
        return sql, params

    def effective_default(self, field):
        "Returns a field's effective database default value"
        if field.has_default():
            default = field.get_default()
        elif not field.null and field.blank and field.empty_strings_allowed:
            default = ""
        else:
            default = None
        # If it's a callable, call it
        if callable(default):
            default = default()
        return default

    # Actions

    def create_model(self, model):
        """
        Takes a model and creates a table for it in the database.
        Will also create any accompanying indexes or unique constraints.
        """
        # Do nothing if this is an unmanaged or proxy model
        if not model._meta.managed or model._meta.proxy:
            return
        # Create column SQL, add FK deferreds if needed
        column_sqls = []
        params = []
        for field in model._meta.local_fields:
            # SQL
            definition, extra_params = self.column_sql(model, field)
            if definition is None:
                continue
            column_sqls.append("%s %s" % (
                self.quote_name(field.column),
                definition,
            ))
            params.extend(extra_params)
            # FK
            if field.rel:
                to_table = field.rel.to._meta.db_table
                to_column = field.rel.to._meta.get_field(field.rel.field_name).column
                self.deferred_sql.append(
                    self.sql_create_fk % {
                        "name": '%s_refs_%s_%x' % (
                            field.column,
                            to_column,
                            abs(hash((model._meta.db_table, to_table)))
                        ),
                        "table": self.quote_name(model._meta.db_table),
                        "column": self.quote_name(field.column),
                        "to_table": self.quote_name(to_table),
                        "to_column": self.quote_name(to_column),
                    }
                )
        # Make the table
        sql = self.sql_create_table % {
            "table": model._meta.db_table,
            "definition": ", ".join(column_sqls)
        }
        self.execute(sql, params)

    def delete_model(self, model):
        """
        Deletes a model from the database.
        """
        # Do nothing if this is an unmanaged or proxy model
        if not model._meta.managed or model._meta.proxy:
            return
        # Delete the table
        self.execute(self.sql_delete_table % {
            "table": self.quote_name(model._meta.db_table),
        })

    def create_field(self, model, field, keep_default=False):
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
        # Build the SQL and run it
        sql = self.sql_create_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
            "definition": definition,
        }
        self.execute(sql, params)
        # Drop the default if we need to
        # (Django usually does not use in-database defaults)
        if not keep_default and field.default is not None:
            sql = self.sql_alter_column % {
                "table": self.quote_name(model._meta.db_table),
                "changes": self.sql_alter_column_no_default % {
                    "column": self.quote_name(field.column),
                }
            }
        # Add any FK constraints later
        if field.rel:
            to_table = field.rel.to._meta.db_table
            to_column = field.rel.to._meta.get_field(field.rel.field_name).column
            self.deferred_sql.append(
                self.sql_create_fk % {
                    "name": '%s_refs_%s_%x' % (
                        field.column,
                        to_column,
                        abs(hash((model._meta.db_table, to_table)))
                    ),
                    "table": self.quote_name(model._meta.db_table),
                    "column": self.quote_name(field.column),
                    "to_table": self.quote_name(to_table),
                    "to_column": self.quote_name(to_column),
                }
            )

    def delete_field(self, model, field):
        """
        Removes a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        # Special-case implicit M2M tables
        if isinstance(field, ManyToManyField) and field.rel.through._meta.auto_created:
            return self.delete_model(field.rel.through)
        # Get the column's definition
        definition, params = self.column_sql(model, field)
        # It might not actually have a column behind it
        if definition is None:
            return
        # Delete the column
        sql = self.sql_delete_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
        }
        self.execute(sql)

    def alter_field(self, model, old_field, new_field):
        """
        Allows a field's type, uniqueness, nullability, default, column,
        constraints etc. to be modified.
        Requires a copy of the old field as well so we can only perform
        changes that are required.
        """
        # Ensure this field is even column-based
        old_type = old_field.db_type(connection=self.connection)
        new_type = new_field.db_type(connection=self.connection)
        if old_type is None and new_type is None:
            # TODO: Handle M2M fields being repointed
            return
        elif old_type is None or new_type is None:
            raise ValueError("Cannot alter field %s into %s - they are not compatible types" % (
                    old_field,
                    new_field,
                ))
        # First, have they renamed the column?
        if old_field.column != new_field.column:
            self.execute(self.sql_rename_column % {
                "table": self.quote_name(model._meta.db_table),
                "old_column": self.quote_name(old_field.column),
                "new_column": self.quote_name(new_field.column),
            })
        # Next, start accumulating actions to do
        actions = []
        # Type change?
        if old_type != new_type:
            actions.append((
                self.sql_alter_column_type % {
                    "column": self.quote_name(new_field.column),
                    "type": new_type,
                },
                [],
            ))
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
                    },
                    [],
                ))
            else:
                actions.append((
                    self.sql_alter_column_null % {
                        "column": self.quote_name(new_field.column),
                    },
                    [],
                ))
        # Combine actions together if we can (e.g. postgres)
        if self.connection.features.supports_combined_alters:
            sql, params = tuple(zip(*actions))
            actions = [(", ".join(sql), params)]
        # Apply those actions
        for sql, params in actions:
            self.execute(
                self.sql_alter_column % {
                    "table": self.quote_name(model._meta.db_table),
                    "changes": sql,
                },
                params,
            )
