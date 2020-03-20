from django.apps.registry import Apps
from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.core.management.base import BaseCommand, CommandError
from django.db import (
    DEFAULT_DB_ALIAS, DatabaseError, connections, models, router,
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

        class CacheTable(models.Model):
            # "key" is a reserved word in MySQL, so use "cache_key" instead.
            cache_key = models.CharField(max_length=255, primary_key=True)
            value = models.TextField()
            expires = models.DateTimeField(db_index=True)

            class Meta:
                apps = Apps()
                app_label = 'cache'
                db_table = tablename
                # constraints = [models.UniqueConstraint(fields=['cache_key'], name=tablename + '_cache_key')]

        if dry_run:
            with connection.schema_editor(collect_sql=True) as editor:
                editor.create_model(CacheTable)
            for statement in editor.collected_sql:
                self.stdout.write(statement)
            return

        try:
            with connection.schema_editor() as editor:
                editor.create_model(CacheTable)
        except DatabaseError as e:
            raise CommandError(
                "Cache table '%s' could not be created.\nThe error was: "
                "%s." % (tablename, e)
            )

        if self.verbosity > 1:
            self.stdout.write("Cache table '%s' created." % tablename)
