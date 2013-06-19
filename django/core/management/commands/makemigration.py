import sys
from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.color import color_style
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.autodetector import MigrationAutodetector, InteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.models.loading import cache


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--empty', action='store_true', dest='empty', default=False,
            help='Make a blank migration.'),
    )

    help = "Creates new migration(s) for apps."
    usage_str = "Usage: ./manage.py createmigration [--empty] [app [app ...]]"

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

        print changes
