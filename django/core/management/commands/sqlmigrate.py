# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import AmbiguityError


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to create SQL for. '
                'Defaults to the "default" database.'),
        make_option('--backwards', action='store_true', dest='backwards',
            default=False, help='Creates SQL to unapply the migration, rather than to apply it'),
    )

    help = "Prints the SQL statements for the named migration."
    output_transaction = True

    def execute(self, *args, **options):
        # sqlmigrate doesn't support coloring its output but we need to force
        # no_color=True so that the BEGIN/COMMIT statements added by
        # output_transaction don't get colored either.
        options['no_color'] = True
        return super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):

        # Get the database we're operating from
        db = options.get('database')
        connection = connections[db]

        # Load up an executor to get all the migration data
        executor = MigrationExecutor(connection)

        # Resolve command-line arguments into a migration
        if len(args) != 2:
            raise CommandError("Wrong number of arguments (expecting 'sqlmigrate app_label migrationname')")
        else:
            app_label, migration_name = args
            if app_label not in executor.loader.migrated_apps:
                raise CommandError("App '%s' does not have migrations" % app_label)
            try:
                migration = executor.loader.get_migration_by_prefix(app_label, migration_name)
            except AmbiguityError:
                raise CommandError("More than one migration matches '%s' in app '%s'. Please be more specific." % (
                    migration_name, app_label))
            except KeyError:
                raise CommandError("Cannot find a migration matching '%s' from app '%s'. Is it in INSTALLED_APPS?" % (
                    migration_name, app_label))
            targets = [(app_label, migration.name)]

        # Make a plan that represents just the requested migrations and show SQL
        # for it
        plan = [(executor.loader.graph.nodes[targets[0]], options.get("backwards", False))]
        sql_statements = executor.collect_sql(plan)
        return '\n'.join(sql_statements)
