from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.core.management.base import BaseCommand, CommandError
from django.db import (
    DEFAULT_DB_ALIAS, DatabaseError, connections, models, router, transaction,
)


class Command(BaseCommand):
    help = "Creates the tables needed to use the SQL cache backend."

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='table_name', nargs='*',
            help='Optional table names. Otherwise, settings.CACHES is used to find cache tables.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Nominates a database onto which the cache tables will be '
                 'installed. Defaults to the "default" database.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Does not create the table, just prints the SQL that would be run.',
        )

    def handle(self, *tablenames, **options):
        db = options['database']
        self.verbosity = options['verbosity']
        dry_run = options['dry_run']
        if tablenames:
            # Legacy behavior, tablename specified as argument
            for tablename in tablenames:
                self.create_table(db, tablename, dry_run)
        else:
            for cache_alias in settings.CACHES:
                cache = caches[cache_alias]
                if isinstance(cache, BaseDatabaseCache):
                    self.create_table(db, cache._table, dry_run)

    def create_table(self, database, tablename, dry_run):
        cache = BaseDatabaseCache(tablename, {})
        if not router.allow_migrate_model(database, cache.cache_model_class):
            return
        connection = connections[database]

        if tablename in connection.introspection.table_names():
            if self.verbosity > 0:
                self.stdout.write("Cache table '%s' already exists." % tablename)
            return

        fields = (
            # "key" is a reserved word in MySQL, so use "cache_key" instead.
            models.CharField(name='cache_key', max_length=255, unique=True, primary_key=True),
            models.TextField(name='value'),
            models.DateTimeField(name='expires', db_index=True),
        )
        table_output = []
        index_output = []
        qn = connection.ops.quote_name
        for f in fields:
            field_output = [
                qn(f.name),
                f.db_type(connection=connection),
                '%sNULL' % ('NOT ' if not f.null else ''),
            ]
            if f.primary_key:
                field_output.append("PRIMARY KEY")
            elif f.unique:
                field_output.append("UNIQUE")
            if f.db_index:
                unique = "UNIQUE " if f.unique else ""
                index_output.append(
                    "CREATE %sINDEX %s ON %s (%s);" %
                    (unique, qn('%s_%s' % (tablename, f.name)), qn(tablename), qn(f.name))
                )
            table_output.append(" ".join(field_output))
        full_statement = ["CREATE TABLE %s (" % qn(tablename)]
        for i, line in enumerate(table_output):
            full_statement.append('    %s%s' % (line, ',' if i < len(table_output) - 1 else ''))
        full_statement.append(');')

        full_statement = "\n".join(full_statement)

        if dry_run:
            self.stdout.write(full_statement)
            for statement in index_output:
                self.stdout.write(statement)
            return

        with transaction.atomic(using=database, savepoint=connection.features.can_rollback_ddl):
            with connection.cursor() as curs:
                try:
                    curs.execute(full_statement)
                except DatabaseError as e:
                    raise CommandError(
                        "Cache table '%s' could not be created.\nThe error was: %s." %
                        (tablename, e))
                for statement in index_output:
                    curs.execute(statement)

        if self.verbosity > 1:
            self.stdout.write("Cache table '%s' created." % tablename)
