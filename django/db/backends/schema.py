import hashlib
import operator

from django.db.backends.creation import BaseDatabaseCreation
from django.db.backends.utils import truncate_name
from django.db.models.fields.related import ManyToManyField
from django.db.transaction import atomic
from django.utils.encoding import force_bytes
from django.utils.log import getLogger
from django.utils.six.moves import reduce
from django.utils.six import callable

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

    sql_create_unique = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s UNIQUE (%(column)s)"
    sql_delete_unique = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s) DEFERRABLE INITIALLY DEFERRED"
    sql_create_fk_inline = ""
    sql_delete_fk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    sql_create_index = "CREATE INDEX %(name)s ON %(table)s (%(column)s)%(extra)s"
    sql_delete_index = "DROP INDEX %(name)s"

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(column)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"

    def __init__(self, connection, collect_sql=False):
        self.connection = connection
        self.collect_sql = collect_sql
        if self.collect_sql:
            self.collected_sql = []

    # State-managing methods

    def __enter__(self):
        # deferred_sql is a list of (sql, params) tuples
        self.deferred_sql = []
        atomic(self.connection.alias, self.connection.features.can_rollback_ddl).__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            for sql, params in self.deferred_sql:
                self.execute(sql)
        atomic(self.connection.alias, self.connection.features.can_rollback_ddl).__exit__(exc_type, exc_value, traceback)

    # Core utility functions

    def execute(self, sql, params=[]):
        """
        Executes the given SQL statement, with optional parameters.
        """
        if not sql:
            return
        # Log the command we're running, then run it
        logger.debug("%s; (params %r)" % (sql, params))
        if self.collect_sql:
            self.collected_sql.append((sql % tuple(map(self._quote_parameter, params))) + ";")
        else:
            # Get the cursor
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
        if include_default and default_value is not None:
            default_sql, default_params = self.prepare_default(default_value)
            sql += " DEFAULT %s" % default_sql
            params += default_params
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
        # Optionally add the tablespace if it's an implicitly indexed column
        tablespace = field.db_tablespace or model._meta.db_tablespace
        if tablespace and self.connection.features.supports_tablespaces and field.unique:
            sql += " %s" % self.connection.ops.tablespace_sql(tablespace, inline=True)
        # Return the sql
        return sql, params

    def prepare_default(self, value):
        """
        Return a tuple containing the default's value SQL and params. Any 
        database that doesn't support literal strings or params in ALTER TABLE 
        statements should override this.
        """
        return "%s", [value]

    def effective_default(self, field):
        """
        Returns a field's effective database default value
        """
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
                self.deferred_sql.append(self._create_db_constraint_sql(
                    model,
                    field.column,
                    constraint_type='index',
                    values={
                        'extra': '',
                    },
                ))
            # FK
            if field.rel:
                to_table = field.rel.to._meta.db_table
                to_column = field.rel.to._meta.get_field(field.rel.field_name).column

                constraint_type = 'fk' if self.connection.features.supports_foreign_keys else 'inline_fk'
                constraint_sql, constraint_params = self._create_db_constraint_sql(
                    model,
                    field.column,
                    constraint_type=constraint_type,
                    values={
                        'name': self._create_constraint_name(model, field.column, constraint_type=constraint_type,
                            suffix="_%s_%s" % (to_table, to_column)),
                        'field': field,
                        'to_table': self.quote_name(to_table),
                        'to_column': self.quote_name(to_column),
                    },
                )

                if constraint_type == 'fk':
                    self.deferred_sql.append((constraint_sql, constraint_params))
                elif constraint_sql:
                    definition += ' ' + constraint_sql
                    params.extend(constraint_params)
            # Add the SQL to our big list
            column_sqls.append("%s %s" % (
                self.quote_name(field.column),
                definition,
            ))
            # Autoincrement SQL (for backends with post table definition variant)
            if field.get_internal_type() == "AutoField":
                autoinc_sql = self.connection.ops.autoinc_sql(model._meta.db_table, field.column)
                if autoinc_sql:
                    self.deferred_sql.extend([(sql, []) for sql in autoinc_sql])
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
            self.execute(*self._create_db_constraint_sql(
                model,
                columns,
                constraint_type='index',
                values={
                    'extra': '',
                }
            ))
        # Make M2M tables
        for field in model._meta.local_many_to_many:
            self.create_model(field.rel.through)

    def delete_model(self, model):
        """
        Deletes a model from the database. If the backend doesn't support
        CASCADE, it will need to override this method manually delete all
        incoming FKs.
        """
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
            self.execute(*self._delete_db_constraint_sql(model, constraint_names[0], constraint_type='unique'))
        # Created uniques
        for fields in news.difference(olds):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            self.execute(*self._create_db_constraint_sql(
                model,
                column=columns,
                constraint_type='unique',
            ))

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
            self.execute(*self._delete_db_constraint_sql(model, constraint_names[0], constraint_type='index'))
        # Created indexes
        for fields in news.difference(olds):
            columns = [model._meta.get_field_by_name(field)[0].column for field in fields]
            self.execute(*self._create_db_constraint_sql(
                model,
                columns,
                constraint_type='index',
                values={
                    'extra': '',
                }
            ))

    def alter_db_table(self, model, old_db_table, new_db_table):
        """
        Renames the table a model points to.
        """
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

    def rename_db_column(self, model, old_db_column, new_db_column, new_type):
        """
        Renames a column on a table.
        """
        self.execute(self.sql_rename_column % {
            "table": self.quote_name(model._meta.db_table),
            "old_column": self.quote_name(old_db_column),
            "new_column": self.quote_name(new_db_column),
            "type": new_type,
        })

    def delete_db_column(self, model, column):
        """
        Delete a column from the model's table.
        """
        # Delete the column
        sql = self.sql_delete_column % {
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(column),
        }
        self.execute(sql)

    def _alter_db_column_sql(self, model, column, alteration=None, values={}, fragment=False, params=None):
        """
        Returns a pair of lists representing combinable SQL fragments and
        non-combinable full SQL statements needed for the column alteration.
        Each list contains tuples of (SQL, params).

        'model'         The model containing the column that is being modified.
        'column'        The column name that is being modified.
        'alteration'    The name of the column alternation that corresponds to
                        the property with the prefix 'sql_alter_column_'.
        'values'        The named values that will be provided to the SQL format
                        string.
        'fragment'      Indicates whether the caller wants SQL framents and is
                        capable of combining the framents to execute.
        'params'        The default params for the SQL format string.
        """
        if alteration is None:
            format_str = self.sql_alter_column
            fragment = None # generic alteration doesn't have a fragment only version
        else:
            format_str = getattr(self, 'sql_alter_column_' + alteration)
        default_values = {
            'column': self.quote_name(column),
        }
        default_values.update(values)
        if 'default' in alteration:
            default_values['constraint_name'] = self.quote_name(
                self._create_constraint_name(model, column, constraint_type='default')
            )
        sql = format_str % default_values
        if fragment == False:
            sql = self.sql_alter_column % {
                'table': self.quote_name(model._meta.db_table),
                'column': self.quote_name(column),
            }
        return [(sql, params or [])], [(None, [])]

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
        if field.default is not None:
            actions, post_actions = self._alter_db_column_sql(model, field.column, 'no_default', fragment=False)
            if actions:
                for sql, params in actions:
                    self.execute(sql, params)
            if post_actions:
                for sql, params in post_actions:
                    self.execute(sql, params)
        # Add an index, if required
        if field.db_index and not field.unique:
            self.deferred_sql.append(
                self._create_db_constraint_sql(
                    model,
                    field.column,
                    constraint_type='index',
                    values={
                        'extra': '',
                    }
                )
            )
        # Add any FK constraints later
        if field.rel and self.connection.features.supports_foreign_keys:
            to_table = field.rel.to._meta.db_table
            to_column = field.rel.to._meta.get_field(field.rel.field_name).column
            self.deferred_sql.append(
                self._create_db_constraint_sql(
                    model,
                    field.column,
                    constraint_type='fk',
                    values={
                        'name': self._create_constraint_name(model, field.column, constraint_type='fk',
                            suffix="_refs_%s_%s" % (to_table, to_column)),
                        'field': field,
                        'to_table': self.quote_name(to_table),
                        'to_column': self.quote_name(to_column),
                    }
                )
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
        self.delete_db_column(model, field.column)
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
        if old_type is None and new_type is None and (old_field.rel.through and new_field.rel.through and old_field.rel.through._meta.auto_created and new_field.rel.through._meta.auto_created):
            return self._alter_many_to_many(model, old_field, new_field, strict)
        elif old_type is None or new_type is None:
            raise ValueError("Cannot alter field %s into %s - they are not compatible types (probably means only one is an M2M with implicit through model)" % (
                old_field,
                new_field,
            ))
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
                self.execute(*self._delete_db_constraint_sql(model, constraint_name, constraint_type='unique'))
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
                self.execute(*self._delete_db_constraint_sql(model, index_name, constraint_type='index'))
        # Drop any FK constraints, we'll remake them later
        if old_field.rel:
            fk_names = self._constraint_names(model, [old_field.column], foreign_key=True)
            if strict and len(fk_names) != 1:
                raise ValueError("Found wrong number (%s) of foreign key constraints for %s.%s" % (
                    len(fk_names),
                    model._meta.db_table,
                    old_field.column,
                ))
            for fk_name in fk_names:
                self.execute(*self._delete_db_constraint_sql(model, fk_name, constraint_type='fk'))
        # Drop incoming FK constraints if we're a primary key and things are going
        # to change.
        if old_field.primary_key and new_field.primary_key and old_type != new_type:
            for rel in new_field.model._meta.get_all_related_objects():
                rel_fk_names = self._constraint_names(rel.model, [rel.field.column], foreign_key=True)
                for fk_name in rel_fk_names:
                    self.execute(*self._delete_db_constraint_sql(model, fk_name, constraint_type='fk'))
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
                self.execute(*self._delete_db_constraint_sql(model, constraint_name, constraint_type='check'))
        # Have they renamed the column?
        if old_field.column != new_field.column:
            self.rename_db_column(model, old_field.column, new_field.column, new_type)
        # Next, start accumulating actions to do
        actions = []
        post_actions = []
        # Type change?
        if old_type != new_type:
            type_actions = self._alter_db_column_sql(model, new_field.column, 'type',
                values={'type': new_type}, fragment=True)
            actions.extend(type_actions[0])
            post_actions.extend(type_actions[1])
        # Default change?
        old_default = self.effective_default(old_field)
        new_default = self.effective_default(new_field)
        if old_default != new_default:
            if new_default is None:
                default_actions = self._alter_db_column_sql(model, new_field.column, 'no_default',
                    fragment=True)
            else:
                default_sql, default_params = self.prepare_default(new_default)
                default_actions = self._alter_db_column_sql(model, new_field.column, 'default',
                    values={'default': default_sql}, fragment=True, params=default_params)
            actions.extend(default_actions[0])
            post_actions.extend(default_actions[1])
        # Nullability change?
        if old_field.null != new_field.null:
            alteration = 'null' if new_field.null else 'not_null'
            null_actions = self._alter_db_column_sql(model, new_field.column, alteration,
                values={'type': new_type}, fragment=True)
            actions.extend(null_actions[0])
            post_actions.extend(null_actions[1])
        if actions:
            # Combine actions together if we can (e.g. postgres)
            if self.connection.features.supports_combined_alters:
                sql, params = tuple(zip(*actions))
                actions = [(", ".join(sql), reduce(operator.add, params))]
            # Apply those actions
            for sql, params in actions:
                if sql:
                    self.execute(
                        self.sql_alter_column % {
                            "table": self.quote_name(model._meta.db_table),
                            "changes": sql,
                        },
                        params,
                    )
        if post_actions:
            for sql, params in post_actions:
                if sql:
                    self.execute(sql, params)
        # Added a unique?
        if not old_field.unique and new_field.unique:
            self.execute(*self._create_db_constraint_sql(model, new_field.column, 'unique'))
        # Added an index?
        if not old_field.db_index and new_field.db_index and not new_field.unique and not (not old_field.unique and new_field.unique):
            self.execute(*self._create_db_constraint_sql(model, new_field.column, 'unique', values={'extra': ''}))
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
                self.execute(*self._delete_db_constraint_sql(model, constraint_name, constraint_type='pk'))
            # Make the new one
            self.execute(*self._create_db_constraint_sql(model, new_field.column, 'pk'))
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
        if new_field.rel:
            self.execute(*self._create_db_constraint_sql(model, new_field.column, 'fk', values={
                "to_table": self.quote_name(new_field.rel.to._meta.db_table),
                "to_column": self.quote_name(new_field.rel.get_related_field().column),
            }))
        # Rebuild FKs that pointed to us if we previously had to drop them
        if old_field.primary_key and new_field.primary_key and old_type != new_type:
            for rel in new_field.model._meta.get_all_related_objects():
                self.execute(*self._create_db_constraint_sql(model, new_field.column, 'fk', values={
                    "to_table": self.quote_name(model._meta.db_table),
                    "to_column": self.quote_name(new_field.column),
                }))
        # Does it have check constraints we need to add?
        if old_db_params['check'] != new_db_params['check'] and new_db_params['check']:
            self.execute(*self._create_db_constraint_sql(model, new_field.column, 'check', values={
                'check': new_db_params['check'],
            }))
        # Reset connection if required
        if self.connection.features.connection_persists_old_columns:
            self.connection.close()

    def _alter_many_to_many(self, model, old_field, new_field, strict):
        """
        Alters M2Ms to repoint their to= endpoints.
        """
        # Rename the through table
        self.alter_db_table(old_field.rel.through, old_field.rel.through._meta.db_table, new_field.rel.through._meta.db_table)
        # Repoint the FK to the other side
        self.alter_field(
            new_field.rel.through,
            # We need the field that points to the target model, so we can tell alter_field to change it -
            # this is m2m_reverse_field_name() (as opposed to m2m_field_name, which points to our model)
            old_field.rel.through._meta.get_field_by_name(old_field.m2m_reverse_field_name())[0],
            new_field.rel.through._meta.get_field_by_name(new_field.m2m_reverse_field_name())[0],
        )

    # Map provides a concise prefix for constraints of the same type
    constraint_type_prefix_map = {
        'UNIQUE': 'UX_',
        'INDEX': 'IX_',
        'DEFAULT': 'DF_',
        'CHECK': 'CK_',
        'PK': 'PK_',
        'FK': 'FK_',
        '': '',
    }

    def _delete_db_constraint_sql(self, model, name, constraint_type, values={}, params=[]):
        """
        Deletes a named database constraint.
        """
        sql = getattr(self, 'sql_delete_' + constraint_type.lower())
        default_values = {
            'table': self.quote_name(model._meta.db_table),
            'name': self.quote_name(name),
        }
        default_values.update(values)
        return sql % default_values, params

    def _create_db_constraint_sql(self, model, column, constraint_type, values={}, params=[]):
        """
        Creates a database constraint.
        """
        sql = getattr(self, 'sql_create_' + constraint_type.lower())
        default_values = {
            'table': self.quote_name(model._meta.db_table),
            'name': self.quote_name(self._create_constraint_name(model, column, constraint_type)),
        }
        if isinstance(column, (list, tuple)):
            default_values['column'] = ', '.join(map(self.quote_name, column))
        else:
            default_values['column'] = self.quote_name(column)
        default_values.update(values)
        return sql % default_values, params

    def _create_constraint_name(self, model, column_names, constraint_type='', suffix=""):
        """
        Generates a unique name for a constraint.
        """
        column = '_'.join(column_names) if isinstance(column_names, (list, tuple)) else column_names
        name = '%s%s_%s%s' % (
            self.constraint_type_prefix_map.get(constraint_type.upper(), ''),
            model._meta.db_table,
            column,
            suffix,
        )
        return truncate_name(name, length=self.connection.ops.max_name_length(), hash_len=8)

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

    def _quote_parameter(self, value):
        """
        Returns a quoted version of the value so it's safe to use in an SQL
        string. This should NOT be used to prepare SQL statements to send to
        the database; it is meant for outputting SQL statements to a file
        or the console for later execution by a developer/DBA.
        """
        raise NotImplementedError()

