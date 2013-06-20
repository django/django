import sys
import os
from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.color import color_style
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.autodetector import MigrationAutodetector, InteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.db.models.loading import cache


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--empty', action='store_true', dest='empty', default=False,
            help='Make a blank migration.'),
    )

    help = "Creates new migration(s) for apps."
    usage_str = "Usage: ./manage.py makemigrations [--empty] [app [app ...]]"

    def handle(self, *app_labels, **options):

        self.verbosity = int(options.get('verbosity'))
        self.interactive = options.get('interactive')
        self.style = color_style()

        # Make sure the app they asked for exists
        app_labels = set(app_labels)
        for app_label in app_labels:
            try:
                cache.get_app(app_label)
            except ImproperlyConfigured:
                self.stderr.write("The app you specified - '%s' - could not be found. Is it in INSTALLED_APPS?" % app_label)
                sys.exit(2)

        # Load the current graph state
        loader = MigrationLoader(connections["default"])

        # Detect changes
        autodetector = MigrationAutodetector(
            loader.graph.project_state(),
            ProjectState.from_app_cache(cache),
            InteractiveMigrationQuestioner(specified_apps=app_labels),
        )
        changes = autodetector.changes()
        changes = autodetector.arrange_for_graph(changes, loader.graph)
        if app_labels:
            changes = autodetector.trim_to_apps(changes, app_labels)

        # No changes? Tell them.
        if not changes:
            if len(app_labels) == 1:
                self.stdout.write("No changes detected in app '%s'" % app_labels.pop())
            elif len(app_labels) > 1:
                self.stdout.write("No changes detected in apps '%s'" % ("', '".join(app_labels)))
            else:
                self.stdout.write("No changes detected")
            return

        for app_label, migrations in changes.items():
            self.stdout.write(self.style.MIGRATE_HEADING("Migrations for '%s':" % app_label) + "\n")
            for migration in migrations:
                # Describe the migration
                writer = MigrationWriter(migration)
                self.stdout.write("  %s:\n" % (self.style.MIGRATE_LABEL(writer.filename),))
                for operation in migration.operations:
                    self.stdout.write("    - %s\n" % operation.describe())
                # Write it
                migrations_directory = os.path.dirname(writer.path)
                if not os.path.isdir(migrations_directory):
                    os.mkdir(migrations_directory)
                init_path = os.path.join(migrations_directory, "__init__.py")
                if not os.path.isfile(init_path):
                    open(init_path, "w").close()
                with open(writer.path, "w") as fh:
                    fh.write(writer.as_string())
