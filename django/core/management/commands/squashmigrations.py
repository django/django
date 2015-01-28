from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, migrations
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import AmbiguityError
from django.db.migrations.migration import SwappableTuple
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.writer import MigrationWriter
from django.utils import six
from django.utils.version import get_docs_version


class Command(BaseCommand):
    help = "Squashes an existing set of migrations (from first until specified) into a single new one."

    def add_arguments(self, parser):
        parser.add_argument('app_label',
            help='App label of the application to squash migrations for.')
        parser.add_argument('migration_name',
            help='Migrations will be squashed until and including this migration.')
        parser.add_argument('--no-optimize', action='store_true', dest='no_optimize', default=False,
            help='Do not try to optimize the squashed operations.')
        parser.add_argument('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.')

    def handle(self, **options):

        self.verbosity = options.get('verbosity')
        self.interactive = options.get('interactive')
        app_label = options['app_label']
        migration_name = options['migration_name']
        no_optimize = options['no_optimize']

        # Load the current graph state, check the app and migration they asked for exists
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        if app_label not in executor.loader.migrated_apps:
            raise CommandError(
                "App '%s' does not have migrations (so squashmigrations on "
                "it makes no sense)" % app_label
            )
        try:
            migration = executor.loader.get_migration_by_prefix(app_label, migration_name)
        except AmbiguityError:
            raise CommandError(
                "More than one migration matches '%s' in app '%s'. Please be "
                "more specific." % (migration_name, app_label)
            )
        except KeyError:
            raise CommandError(
                "Cannot find a migration matching '%s' from app '%s'." %
                (migration_name, app_label)
            )

        # Work out the list of predecessor migrations
        migrations_to_squash = [
            executor.loader.get_migration(al, mn)
            for al, mn in executor.loader.graph.forwards_plan((migration.app_label, migration.name))
            if al == migration.app_label
        ]

        # Tell them what we're doing and optionally ask if we should proceed
        if self.verbosity > 0 or self.interactive:
            self.stdout.write(self.style.MIGRATE_HEADING("Will squash the following migrations:"))
            for migration in migrations_to_squash:
                self.stdout.write(" - %s" % migration.name)

            if self.interactive:
                answer = None
                while not answer or answer not in "yn":
                    answer = six.moves.input("Do you wish to proceed? [yN] ")
                    if not answer:
                        answer = "n"
                        break
                    else:
                        answer = answer[0].lower()
                if answer != "y":
                    return

        # Load the operations from all those migrations and concat together,
        # along with collecting external dependencies and detecting
        # double-squashing
        operations = []
        dependencies = set()
        for smigration in migrations_to_squash:
            if smigration.replaces:
                raise CommandError(
                    "You cannot squash squashed migrations! Please transition "
                    "it to a normal migration first: "
                    "https://docs.djangoproject.com/en/%s/topics/migrations/#squashing-migrations" % get_docs_version()
                )
            operations.extend(smigration.operations)
            for dependency in smigration.dependencies:
                if isinstance(dependency, SwappableTuple):
                    if settings.AUTH_USER_MODEL == dependency.setting:
                        dependencies.add(("__setting__", "AUTH_USER_MODEL"))
                    else:
                        dependencies.add(dependency)
                elif dependency[0] != smigration.app_label:
                    dependencies.add(dependency)

        if no_optimize:
            if self.verbosity > 0:
                self.stdout.write(self.style.MIGRATE_HEADING("(Skipping optimization.)"))
            new_operations = operations
        else:
            if self.verbosity > 0:
                self.stdout.write(self.style.MIGRATE_HEADING("Optimizing..."))

            optimizer = MigrationOptimizer()
            new_operations = optimizer.optimize(operations, migration.app_label)

            if self.verbosity > 0:
                if len(new_operations) == len(operations):
                    self.stdout.write("  No optimizations possible.")
                else:
                    self.stdout.write(
                        "  Optimized from %s operations to %s operations." %
                        (len(operations), len(new_operations))
                    )

        # Work out the value of replaces (any squashed ones we're re-squashing)
        # need to feed their replaces into ours
        replaces = []
        for migration in migrations_to_squash:
            if migration.replaces:
                replaces.extend(migration.replaces)
            else:
                replaces.append((migration.app_label, migration.name))

        # Make a new migration with those operations
        subclass = type("Migration", (migrations.Migration, ), {
            "dependencies": dependencies,
            "operations": new_operations,
            "replaces": replaces,
        })
        new_migration = subclass("0001_squashed_%s" % migration.name, app_label)

        # Write out the new migration file
        writer = MigrationWriter(new_migration)
        with open(writer.path, "wb") as fh:
            fh.write(writer.as_string())

        if self.verbosity > 0:
            self.stdout.write(self.style.MIGRATE_HEADING("Created new squashed migration %s" % writer.path))
            self.stdout.write("  You should commit this migration but leave the old ones in place;")
            self.stdout.write("  the new migration will be used for new installs. Once you are sure")
            self.stdout.write("  all instances of the codebase have applied the migrations you squashed,")
            self.stdout.write("  you can delete them.")
            if writer.needs_manual_porting:
                self.stdout.write(self.style.MIGRATE_HEADING("Manual porting required"))
                self.stdout.write("  Your migrations contained functions that must be manually copied over,")
                self.stdout.write("  as we could not safely copy their implementation.")
                self.stdout.write("  See the comment at the top of the squashed migration for details.")
