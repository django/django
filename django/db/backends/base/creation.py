import hashlib
import sys
import time
import warnings

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import router
from django.db.backends.utils import truncate_name
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_bytes
from django.utils.six import StringIO
from django.utils.six.moves import input

# The prefix to put on the default database name when creating
# the test database.
TEST_DATABASE_PREFIX = 'test_'


class BaseDatabaseCreation(object):
    """
    This class encapsulates all backend-specific differences that pertain to
    database *creation*, such as the column types to use for particular Django
    Fields, the SQL used to create and destroy tables, and the creation and
    destruction of test databases.
    """
    def __init__(self, connection):
        self.connection = connection

    @property
    def _nodb_connection(self):
        """
        Used to be defined here, now moved to DatabaseWrapper.
        """
        return self.connection._nodb_connection

    @classmethod
    def _digest(cls, *args):
        """
        Generates a 32-bit digest of a set of arguments that can be used to
        shorten identifying names.
        """
        h = hashlib.md5()
        for arg in args:
            h.update(force_bytes(arg))
        return h.hexdigest()[:8]

    def sql_create_model(self, model, style, known_models=set()):
        """
        Returns the SQL required to create a single model, as a tuple of:
            (list_of_sql, pending_references_dict)
        """
        opts = model._meta
        if not opts.managed or opts.proxy or opts.swapped:
            return [], {}
        final_output = []
        table_output = []
        pending_references = {}
        qn = self.connection.ops.quote_name
        for f in opts.local_fields:
            db_params = f.db_parameters(connection=self.connection)
            col_type = db_params['type']
            if db_params['check']:
                col_type = '%s CHECK (%s)' % (col_type, db_params['check'])
            col_type_suffix = f.db_type_suffix(connection=self.connection)
            tablespace = f.db_tablespace or opts.db_tablespace
            if col_type is None:
                # Skip ManyToManyFields, because they're not represented as
                # database columns in this table.
                continue
            # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
            field_output = [style.SQL_FIELD(qn(f.column)),
                style.SQL_COLTYPE(col_type)]
            # Oracle treats the empty string ('') as null, so coerce the null
            # option whenever '' is a possible value.
            null = f.null
            if (f.empty_strings_allowed and not f.primary_key and
                    self.connection.features.interprets_empty_strings_as_nulls):
                null = True
            if not null:
                field_output.append(style.SQL_KEYWORD('NOT NULL'))
            if f.primary_key:
                field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
            elif f.unique:
                field_output.append(style.SQL_KEYWORD('UNIQUE'))
            if tablespace and f.unique:
                # We must specify the index tablespace inline, because we
                # won't be generating a CREATE INDEX statement for this field.
                tablespace_sql = self.connection.ops.tablespace_sql(
                    tablespace, inline=True)
                if tablespace_sql:
                    field_output.append(tablespace_sql)
            if f.rel and f.db_constraint:
                ref_output, pending = self.sql_for_inline_foreign_key_references(
                    model, f, known_models, style)
                if pending:
                    pending_references.setdefault(f.rel.to, []).append(
                        (model, f))
                else:
                    field_output.extend(ref_output)
            if col_type_suffix:
                field_output.append(style.SQL_KEYWORD(col_type_suffix))
            table_output.append(' '.join(field_output))
        for field_constraints in opts.unique_together:
            table_output.append(style.SQL_KEYWORD('UNIQUE') + ' (%s)' %
                ", ".join(
                    [style.SQL_FIELD(qn(opts.get_field(f).column))
                     for f in field_constraints]))

        full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' +
                          style.SQL_TABLE(qn(opts.db_table)) + ' (']
        for i, line in enumerate(table_output):  # Combine and add commas.
            full_statement.append(
                '    %s%s' % (line, ',' if i < len(table_output) - 1 else ''))
        full_statement.append(')')
        if opts.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(
                opts.db_tablespace)
            if tablespace_sql:
                full_statement.append(tablespace_sql)
        full_statement.append(';')
        final_output.append('\n'.join(full_statement))

        if opts.has_auto_field:
            # Add any extra SQL needed to support auto-incrementing primary
            # keys.
            auto_column = opts.auto_field.db_column or opts.auto_field.name
            autoinc_sql = self.connection.ops.autoinc_sql(opts.db_table,
                                                          auto_column)
            if autoinc_sql:
                for stmt in autoinc_sql:
                    final_output.append(stmt)

        return final_output, pending_references

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """
        Return the SQL snippet defining the foreign key reference for a field.
        """
        qn = self.connection.ops.quote_name
        rel_to = field.rel.to
        if rel_to in known_models or rel_to == model:
            output = [style.SQL_KEYWORD('REFERENCES') + ' ' +
                style.SQL_TABLE(qn(rel_to._meta.db_table)) + ' (' +
                style.SQL_FIELD(qn(rel_to._meta.get_field(
                    field.rel.field_name).column)) + ')' +
                self.connection.ops.deferrable_sql()
            ]
            pending = False
        else:
            # We haven't yet created the table to which this field
            # is related, so save it for later.
            output = []
            pending = True

        return output, pending

    def sql_for_pending_references(self, model, style, pending_references):
        """
        Returns any ALTER TABLE statements to add constraints after the fact.
        """
        opts = model._meta
        if not opts.managed or opts.swapped:
            return []
        qn = self.connection.ops.quote_name
        final_output = []
        if model in pending_references:
            for rel_class, f in pending_references[model]:
                rel_opts = rel_class._meta
                r_table = rel_opts.db_table
                r_col = f.column
                table = opts.db_table
                col = opts.get_field(f.rel.field_name).column
                # For MySQL, r_name must be unique in the first 64 characters.
                # So we are careful with character usage here.
                r_name = '%s_refs_%s_%s' % (
                    r_col, col, self._digest(r_table, table))
                final_output.append(style.SQL_KEYWORD('ALTER TABLE') +
                    ' %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s (%s)%s;' %
                    (qn(r_table), qn(truncate_name(
                        r_name, self.connection.ops.max_name_length())),
                    qn(r_col), qn(table), qn(col),
                    self.connection.ops.deferrable_sql()))
            del pending_references[model]
        return final_output

    def sql_indexes_for_model(self, model, style):
        """
        Returns the CREATE INDEX SQL statements for a single model.
        """
        warnings.warn("DatabaseCreation.sql_indexes_for_model is deprecated, "
                      "use the equivalent method of the schema editor instead.",
                      RemovedInDjango20Warning)
        if not model._meta.managed or model._meta.proxy or model._meta.swapped:
            return []
        output = []
        for f in model._meta.local_fields:
            output.extend(self.sql_indexes_for_field(model, f, style))
        for fs in model._meta.index_together:
            fields = [model._meta.get_field(f) for f in fs]
            output.extend(self.sql_indexes_for_fields(model, fields, style))
        return output

    def sql_indexes_for_field(self, model, f, style):
        """
        Return the CREATE INDEX SQL statements for a single model field.
        """
        if f.db_index and not f.unique:
            return self.sql_indexes_for_fields(model, [f], style)
        else:
            return []

    def sql_indexes_for_fields(self, model, fields, style):
        if len(fields) == 1 and fields[0].db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(fields[0].db_tablespace)
        elif model._meta.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(model._meta.db_tablespace)
        else:
            tablespace_sql = ""
        if tablespace_sql:
            tablespace_sql = " " + tablespace_sql

        field_names = []
        qn = self.connection.ops.quote_name
        for f in fields:
            field_names.append(style.SQL_FIELD(qn(f.column)))

        index_name = "%s_%s" % (model._meta.db_table, self._digest([f.name for f in fields]))

        return [
            style.SQL_KEYWORD("CREATE INDEX") + " " +
            style.SQL_TABLE(qn(truncate_name(index_name, self.connection.ops.max_name_length()))) + " " +
            style.SQL_KEYWORD("ON") + " " +
            style.SQL_TABLE(qn(model._meta.db_table)) + " " +
            "(%s)" % style.SQL_FIELD(", ".join(field_names)) +
            "%s;" % tablespace_sql,
        ]

    def sql_destroy_model(self, model, references_to_delete, style):
        """
        Return the DROP TABLE and restraint dropping statements for a single
        model.
        """
        if not model._meta.managed or model._meta.proxy or model._meta.swapped:
            return []
        # Drop the table now
        qn = self.connection.ops.quote_name
        output = ['%s %s;' % (style.SQL_KEYWORD('DROP TABLE'),
                              style.SQL_TABLE(qn(model._meta.db_table)))]
        if model in references_to_delete:
            output.extend(self.sql_remove_table_constraints(
                model, references_to_delete, style))
        if model._meta.has_auto_field:
            ds = self.connection.ops.drop_sequence_sql(model._meta.db_table)
            if ds:
                output.append(ds)
        return output

    def sql_remove_table_constraints(self, model, references_to_delete, style):
        if not model._meta.managed or model._meta.proxy or model._meta.swapped:
            return []
        output = []
        qn = self.connection.ops.quote_name
        for rel_class, f in references_to_delete[model]:
            table = rel_class._meta.db_table
            col = f.column
            r_table = model._meta.db_table
            r_col = model._meta.get_field(f.rel.field_name).column
            r_name = '%s_refs_%s_%s' % (
                col, r_col, self._digest(table, r_table))
            output.append('%s %s %s %s;' % (
                style.SQL_KEYWORD('ALTER TABLE'),
                style.SQL_TABLE(qn(table)),
                style.SQL_KEYWORD(self.connection.ops.drop_foreignkey_sql()),
                style.SQL_FIELD(qn(truncate_name(
                    r_name, self.connection.ops.max_name_length())))
            ))
        del references_to_delete[model]
        return output

    def sql_destroy_indexes_for_model(self, model, style):
        """
        Returns the DROP INDEX SQL statements for a single model.
        """
        if not model._meta.managed or model._meta.proxy or model._meta.swapped:
            return []
        output = []
        for f in model._meta.local_fields:
            output.extend(self.sql_destroy_indexes_for_field(model, f, style))
        for fs in model._meta.index_together:
            fields = [model._meta.get_field(f) for f in fs]
            output.extend(self.sql_destroy_indexes_for_fields(model, fields, style))
        return output

    def sql_destroy_indexes_for_field(self, model, f, style):
        """
        Return the DROP INDEX SQL statements for a single model field.
        """
        if f.db_index and not f.unique:
            return self.sql_destroy_indexes_for_fields(model, [f], style)
        else:
            return []

    def sql_destroy_indexes_for_fields(self, model, fields, style):
        if len(fields) == 1 and fields[0].db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(fields[0].db_tablespace)
        elif model._meta.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(model._meta.db_tablespace)
        else:
            tablespace_sql = ""
        if tablespace_sql:
            tablespace_sql = " " + tablespace_sql

        field_names = []
        qn = self.connection.ops.quote_name
        for f in fields:
            field_names.append(style.SQL_FIELD(qn(f.column)))

        index_name = "%s_%s" % (model._meta.db_table, self._digest([f.name for f in fields]))

        return [
            style.SQL_KEYWORD("DROP INDEX") + " " +
            style.SQL_TABLE(qn(truncate_name(index_name, self.connection.ops.max_name_length()))) + " " +
            ";",
        ]

    def create_test_db(self, verbosity=1, autoclobber=False, serialize=True, keepdb=False):
        """
        Creates a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        # Don't import django.core.management if it isn't needed.
        from django.core.management import call_command

        test_database_name = self._get_test_db_name()

        if verbosity >= 1:
            test_db_repr = ''
            action = 'Creating'
            if verbosity >= 2:
                test_db_repr = " ('%s')" % test_database_name
            if keepdb:
                action = "Using existing"

            print("%s test database for alias '%s'%s..." % (
                action, self.connection.alias, test_db_repr))

        # We could skip this call if keepdb is True, but we instead
        # give it the keepdb param. This is to handle the case
        # where the test DB doesn't exist, in which case we need to
        # create it, then just not destroy it. If we instead skip
        # this, we will get an exception.
        self._create_test_db(verbosity, autoclobber, keepdb)

        self.connection.close()
        settings.DATABASES[self.connection.alias]["NAME"] = test_database_name
        self.connection.settings_dict["NAME"] = test_database_name

        # We report migrate messages at one level lower than that requested.
        # This ensures we don't get flooded with messages during testing
        # (unless you really ask to be flooded).
        call_command(
            'migrate',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias,
            test_flush=True,
        )

        # We then serialize the current state of the database into a string
        # and store it on the connection. This slightly horrific process is so people
        # who are testing on databases without transactions or who are using
        # a TransactionTestCase still get a clean database on every test run.
        if serialize:
            self.connection._test_serialized_contents = self.serialize_db_to_string()

        call_command('createcachetable', database=self.connection.alias)

        # Ensure a connection for the side effect of initializing the test database.
        self.connection.ensure_connection()

        return test_database_name

    def serialize_db_to_string(self):
        """
        Serializes all data in the database into a JSON string.
        Designed only for test runner usage; will not handle large
        amounts of data.
        """
        # Build list of all apps to serialize
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(self.connection)
        app_list = []
        for app_config in apps.get_app_configs():
            if (
                app_config.models_module is not None and
                app_config.label in loader.migrated_apps and
                app_config.name not in settings.TEST_NON_SERIALIZED_APPS
            ):
                app_list.append((app_config, None))

        # Make a function to iteratively return every object
        def get_objects():
            for model in serializers.sort_dependencies(app_list):
                if (not model._meta.proxy and model._meta.managed and
                        router.allow_migrate_model(self.connection.alias, model)):
                    queryset = model._default_manager.using(self.connection.alias).order_by(model._meta.pk.name)
                    for obj in queryset.iterator():
                        yield obj
        # Serialize to a string
        out = StringIO()
        serializers.serialize("json", get_objects(), indent=None, stream=out)
        return out.getvalue()

    def deserialize_db_from_string(self, data):
        """
        Reloads the database with data from a string generated by
        the serialize_db_to_string method.
        """
        data = StringIO(data)
        for obj in serializers.deserialize("json", data, using=self.connection.alias):
            obj.save()

    def _get_test_db_name(self):
        """
        Internal implementation - returns the name of the test DB that will be
        created. Only useful when called from create_test_db() and
        _create_test_db() and when no external munging is done with the 'NAME'
        or 'TEST_NAME' settings.
        """
        if self.connection.settings_dict['TEST']['NAME']:
            return self.connection.settings_dict['TEST']['NAME']
        return TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        """
        Internal implementation - creates the test db tables.
        """
        suffix = self.sql_table_creation_suffix()

        test_database_name = self._get_test_db_name()

        qn = self.connection.ops.quote_name

        # Create the test database and connect to it.
        with self._nodb_connection.cursor() as cursor:
            try:
                cursor.execute(
                    "CREATE DATABASE %s %s" % (qn(test_database_name), suffix))
            except Exception as e:
                # if we want to keep the db, then no need to do any of the below,
                # just return and skip it all.
                if keepdb:
                    return test_database_name

                sys.stderr.write(
                    "Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test database '%s'..."
                                  % self.connection.alias)
                        cursor.execute(
                            "DROP DATABASE %s" % qn(test_database_name))
                        cursor.execute(
                            "CREATE DATABASE %s %s" % (qn(test_database_name),
                                                       suffix))
                    except Exception as e:
                        sys.stderr.write(
                            "Got an error recreating the test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

        return test_database_name

    def destroy_test_db(self, old_database_name, verbosity=1, keepdb=False):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists.
        """
        self.connection.close()
        test_database_name = self.connection.settings_dict['NAME']
        if verbosity >= 1:
            test_db_repr = ''
            action = 'Destroying'
            if verbosity >= 2:
                test_db_repr = " ('%s')" % test_database_name
            if keepdb:
                action = 'Preserving'
            print("%s test database for alias '%s'%s..." % (
                action, self.connection.alias, test_db_repr))

        # if we want to preserve the database
        # skip the actual destroying piece.
        if not keepdb:
            self._destroy_test_db(test_database_name, verbosity)

        # Restore the original database name
        settings.DATABASES[self.connection.alias]["NAME"] = old_database_name
        self.connection.settings_dict["NAME"] = old_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        """
        Internal implementation - remove the test db tables.
        """
        # Remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        with self._nodb_connection.cursor() as cursor:
            # Wait to avoid "database is being accessed by other users" errors.
            time.sleep(1)
            cursor.execute("DROP DATABASE %s"
                           % self.connection.ops.quote_name(test_database_name))

    def sql_table_creation_suffix(self):
        """
        SQL to append to the end of the test table creation statements.
        """
        return ''

    def test_db_signature(self):
        """
        Returns a tuple with elements of self.connection.settings_dict (a
        DATABASES setting value) that uniquely identify a database
        accordingly to the RDBMS particularities.
        """
        settings_dict = self.connection.settings_dict
        return (
            settings_dict['HOST'],
            settings_dict['PORT'],
            settings_dict['ENGINE'],
            settings_dict['NAME']
        )
