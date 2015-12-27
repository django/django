# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import AmbiguityError


class Command(BaseCommand):
    help = "Prints the SQL statements for the named migration."

    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument('app_label', nargs='?',
            help='App label of the application containing the migration.')
        parser.add_argument('migration_name', nargs='?',
            help='Migration name to print the SQL for.')
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to create SQL for. Defaults to the '
                 '"default" database.')
        parser.add_argument('--backwards', action='store_true', dest='backwards',
            default=False, help='Creates SQL to unapply the migration, rather than to apply it')

    def execute(self, *args, **options):
        # sqlmigrate doesn't support coloring its output but we need to force
        # no_color=True so that the BEGIN/COMMIT statements added by
        # output_transaction don't get colored either.
        options['no_color'] = True
        return super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
        # Get the database we're operating from
        connection = connections[options['database']]

        # Hook for backends needing any database preparation
        connection.prepare_database()
        # Load up an executor to get all the migration data
        executor = MigrationExecutor(connection)

        # Resolve command-line arguments into a migration
        if options['app_label'] and options['migration_name']:
            app_label, migration_name = options['app_label'], options['migration_name']
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
            # Make a plan that represents just the requested migrations
            plan = [(executor.loader.graph.nodes[targets[0]], options['backwards'])]
        elif options['app_label']:
            if options['backwards']:
                raise CommandError("Need specific 'migration_name' to provide 'backwards' sql.")
            app_label = options['app_label']
            if app_label not in executor.loader.migrated_apps:
                raise CommandError("App '%s' does not have migrations." % app_label)
            targets = [key for key in executor.loader.graph.leaf_nodes() if key[0] == app_label]
            # Make a plan for forwards migrations of given app_label
            plan = executor.migration_plan(targets)
        else:
            if options['backwards']:
                raise CommandError("Need 'app_label' and 'migration_name' to provide 'backwards' sql.")
            targets = executor.loader.graph.leaf_nodes()
            # Make a plan for all forwards migrations
            plan = executor.migration_plan(targets)

        # Show SQL
        sql_statements = executor.collect_sql(plan)
        return '\n'.join(sql_statements)
