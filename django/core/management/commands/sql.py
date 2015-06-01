from __future__ import unicode_literals

import sys

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState


class Command(BaseCommand):
    help = (
        "Returns the CREATE TABLE, CREATE INDEX and other SQL statements"
        "needed to set up a copy of the database, ignoring existing migrations"
    )

    output_transaction = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('args', metavar='app_label', nargs='*',
            help='Specify the app label(s) to create migrations for.')
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to print the SQL for. Defaults to the '
                 '"default" database.')

    def handle(self, *app_labels, **options):
        # Verify app labels
        app_labels = set(app_labels)
        bad_app_labels = set()
        for app_label in app_labels:
            try:
                apps.get_app_config(app_label)
            except LookupError:
                bad_app_labels.add(app_label)
        if bad_app_labels:
            for app_label in bad_app_labels:
                self.stderr.write("App '%s' could not be found. Is it in INSTALLED_APPS?" % app_label)
            sys.exit(2)
        all_app_labels = {config.label for config in apps.get_app_configs()}

        # Set up the migration autodetector to make a from-scratch set of migrations to apply
        initial_state = ProjectState()
        questioner = NonInteractiveMigrationQuestioner(specified_apps=all_app_labels, dry_run=True)
        autodetector = MigrationAutodetector(
            initial_state,
            ProjectState.from_apps(apps),
            questioner,
        )

        # Run the autodetector
        changes = autodetector.changes(
            graph=MigrationGraph(),
            trim_to_apps=all_app_labels or None,
            convert_apps=all_app_labels or None,
        )

        # Loop the changes back into a graph we can apply from
        loader = MigrationLoader.from_changes(changes)

        # Fake-apply them to get SQL
        executor = MigrationExecutor(connections[options['database']])
        executor.loader = loader
        executor.recorder = None
        plan = executor.migration_plan(
            [key for key in loader.graph.leaf_nodes() if key[0] in app_labels],
            clean_start=True,
        )
        sql_statements = executor.collect_sql(plan)
        return '\n'.join(sql_statements)
