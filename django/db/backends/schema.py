import sys
import time

from django.conf import settings
from django.db import transaction
from django.db.utils import load_backend
from django.utils.log import getLogger

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

    sql_create_column = "ALTER TABLE %(table)s ADD COLUMN %(definition)s"
    sql_alter_column_type = "ALTER COLUMN %(column)s TYPE %(type)s"
    sql_alter_column_null = "ALTER COLUMN %(column)s DROP NOT NULL"
    sql_alter_column_not_null = "ALTER COLUMN %(column)s SET NOT NULL"
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s CASCADE;"

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

    # Actions

    def create_model(self, model):
        """
        Takes a model and creates a table for it in the database.
        Will also create any accompanying indexes or unique constraints.
        """
        # Do nothing if this is an unmanaged or proxy model
        if not model._meta.managed or model._meta.proxy:
            return [], {}
        # Create column SQL, add FK deferreds if needed
        column_sqls = []
        for field in model._meta.local_fields:
            # SQL
            definition = self.column_sql(model, field)
            if definition is None:
                continue
            column_sqls.append("%s %s" % (
                self.quote_name(field.column),
                definition,
            ))
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
        self.execute(sql)

    def column_sql(self, model, field, include_default=False):
        """
        Takes a field and returns its column definition.
        The field must already have had set_attributes_from_name called.
        """
        # Get the column's type and use that as the basis of the SQL
        sql = field.db_type(connection=self.connection)
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
            raise NotImplementedError()
        # Return the sql
        return sql

    def delete_model(self, model):
        self.execute(self.sql_delete_table % {
            "table": self.quote_name(model._meta.db_table),
        })
