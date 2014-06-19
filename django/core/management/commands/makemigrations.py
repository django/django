import sys
import os
import operator
from optparse import make_option

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db.migrations import Migration
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.questioner import MigrationQuestioner, InteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.utils.six import iteritems
from django.utils.six.moves import reduce


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--dry-run', action='store_true', dest='dry_run', default=False,
            help="Just show what migrations would be made; don't actually write them."),
        make_option('--merge', action='store_true', dest='merge', default=False,
            help="Enable fixing of migration conflicts."),
        make_option('--empty', action='store_true', dest='empty', default=False,
            help="Create an empty migration."),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
    )

    help = "Creates new migration(s) for apps."
    usage_str = "Usage: ./manage.py makemigrations [--dry-run] [app [app ...]]"
    args = "[app_label [app_label ...]]"

    def handle(self, *app_labels, **options):

        self.verbosity = int(options.get('verbosity'))
        self.interactive = options.get('interactive')
        self.dry_run = options.get('dry_run', False)
        self.merge = options.get('merge', False)
        self.empty = options.get('empty', False)

        # Make sure the app they asked for exists
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

        # Load the current graph state. Pass in None for the connection so
        # the loader doesn't try to resolve replaced migrations from DB.
        loader = MigrationLoader(None, ignore_no_migrations=True)

        # Before anything else, see if there's conflicting apps and drop out
        # hard if there are any and they don't want to merge
        conflicts = loader.detect_conflicts()

        # If app_labels is specified, filter out conflicting migrations for unspecified apps
        if app_labels:
            conflicts = dict(
                (app_label, conflict) for app_label, conflict in iteritems(conflicts)
                if app_label in app_labels
            )

        if conflicts and not self.merge:
            name_str = "; ".join(
                "%s in %s" % (", ".join(names), app)
                for app, names in conflicts.items()
            )
            raise CommandError("Conflicting migrations detected (%s).\nTo fix them run 'python manage.py makemigrations --merge'" % name_str)

        # If they want to merge and there's nothing to merge, then politely exit
        if self.merge and not conflicts:
            self.stdout.write("No conflicts detected to merge.")
            return

        # If they want to merge and there is something to merge, then
        # divert into the merge code
        if self.merge and conflicts:
            return self.handle_merge(loader, conflicts)

        # Set up autodetector
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(apps),
            InteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=self.dry_run),
        )

        # If they want to make an empty migration, make one for each app
        if self.empty:
            if not app_labels:
                raise CommandError("You must supply at least one app label when using --empty.")
            # Make a fake changes() result we can pass to arrange_for_graph
            changes = dict(
                (app, [Migration("custom", app)])
                for app in app_labels
            )
            changes = autodetector.arrange_for_graph(changes, loader.graph)
            self.write_migration_files(changes)
            return

        # Detect changes
        changes = autodetector.changes(
            graph=loader.graph,
            trim_to_apps=app_labels or None,
            convert_apps=app_labels or None,
        )

        # No changes? Tell them.
        if not changes and self.verbosity >= 1:
            if len(app_labels) == 1:
                self.stdout.write("No changes detected in app '%s'" % app_labels.pop())
            elif len(app_labels) > 1:
                self.stdout.write("No changes detected in apps '%s'" % ("', '".join(app_labels)))
            else:
                self.stdout.write("No changes detected")
            return

        self.write_migration_files(changes)

    def write_migration_files(self, changes):
        """
        Takes a changes dict and writes them out as migration files.
        """
        directory_created = {}
        for app_label, app_migrations in changes.items():
            if self.verbosity >= 1:
                self.stdout.write(self.style.MIGRATE_HEADING("Migrations for '%s':" % app_label) + "\n")
            for migration in app_migrations:
                # Describe the migration
                writer = MigrationWriter(migration)
                if self.verbosity >= 1:
                    self.stdout.write("  %s:\n" % (self.style.MIGRATE_LABEL(writer.filename),))
                    for operation in migration.operations:
                        self.stdout.write("    - %s\n" % operation.describe())
                if not self.dry_run:
                    # Write the migrations file to the disk.
                    migrations_directory = os.path.dirname(writer.path)
                    if not directory_created.get(app_label, False):
                        if not os.path.isdir(migrations_directory):
                            os.mkdir(migrations_directory)
                        init_path = os.path.join(migrations_directory, "__init__.py")
                        if not os.path.isfile(init_path):
                            open(init_path, "w").close()
                        # We just do this once per app
                        directory_created[app_label] = True
                    migration_string = writer.as_string()
                    with open(writer.path, "wb") as fh:
                        fh.write(migration_string)
                elif self.verbosity == 3:
                    # Alternatively, makemigrations --dry-run --verbosity 3
                    # will output the migrations to stdout rather than saving
                    # the file to the disk.
                    self.stdout.write(self.style.MIGRATE_HEADING("Full migrations file '%s':" % writer.filename) + "\n")
                    self.stdout.write("%s\n" % writer.as_string())

    def handle_merge(self, loader, conflicts):
        """
        Handles merging together conflicted migrations interactively,
        if it's safe; otherwise, advises on how to fix it.
        """
        if self.interactive:
            questioner = InteractiveMigrationQuestioner()
        else:
            questioner = MigrationQuestioner(defaults={'ask_merge': True})
        for app_label, migration_names in conflicts.items():
            # Grab out the migrations in question, and work out their
            # common ancestor.
            merge_migrations = []
            for migration_name in migration_names:
                migration = loader.get_migration(app_label, migration_name)
                migration.ancestry = loader.graph.forwards_plan((app_label, migration_name))
                merge_migrations.append(migration)
            common_ancestor = None
            for level in zip(*[m.ancestry for m in merge_migrations]):
                if reduce(operator.eq, level):
                    common_ancestor = level[0]
                else:
                    break
            if common_ancestor is None:
                raise ValueError("Could not find common ancestor of %s" % migration_names)
            # Now work out the operations along each divergent branch
            for migration in merge_migrations:
                migration.branch = migration.ancestry[
                    (migration.ancestry.index(common_ancestor) + 1):
                ]
                migration.merged_operations = []
                for node_app, node_name in migration.branch:
                    migration.merged_operations.extend(
                        loader.get_migration(node_app, node_name).operations
                    )
            # In future, this could use some of the Optimizer code
            # (can_optimize_through) to automatically see if they're
            # mergeable. For now, we always just prompt the user.
            if self.verbosity > 0:
                self.stdout.write(self.style.MIGRATE_HEADING("Merging %s" % app_label))
                for migration in merge_migrations:
                    self.stdout.write(self.style.MIGRATE_LABEL("  Branch %s" % migration.name))
                    for operation in migration.merged_operations:
                        self.stdout.write("    - %s\n" % operation.describe())
            if questioner.ask_merge(app_label):
                # If they still want to merge it, then write out an empty
                # file depending on the migrations needing merging.
                numbers = [
                    MigrationAutodetector.parse_number(migration.name)
                    for migration in merge_migrations
                ]
                try:
                    biggest_number = max([x for x in numbers if x is not None])
                except ValueError:
                    biggest_number = 1
                subclass = type("Migration", (Migration, ), {
                    "dependencies": [(app_label, migration.name) for migration in merge_migrations],
                })
                new_migration = subclass("%04i_merge" % (biggest_number + 1), app_label)
                writer = MigrationWriter(new_migration)
                with open(writer.path, "wb") as fh:
                    fh.write(writer.as_string())
                if self.verbosity > 0:
                    self.stdout.write("\nCreated new merge migration %s" % writer.path)
