import os
import shutil

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import run_formatters
from django.db import DEFAULT_DB_ALIAS, connections, migrations
from django.db.migrations.loader import AmbiguityError, MigrationLoader
from django.db.migrations.migration import SwappableTuple
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.writer import MigrationWriter
from django.utils.version import get_docs_version


class Command(BaseCommand):
    help = (
        "Squashes an existing set of migrations (from first until specified) into a "
        "single new one."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="App label of the application to squash migrations for.",
        )
        parser.add_argument(
            "start_migration_name",
            nargs="?",
            help=(
                "Migrations will be squashed starting from and including this "
                "migration."
            ),
        )
        parser.add_argument(
            "migration_name",
            help="Migrations will be squashed until and including this migration.",
        )
        parser.add_argument(
            "--no-optimize",
            action="store_true",
            help="Do not try to optimize the squashed operations.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--squashed-name",
            help="Sets the name of the new squashed migration.",
        )
        parser.add_argument(
            "--no-header",
            action="store_false",
            dest="include_header",
            help="Do not add a header comment to the new squashed migration.",
        )

    def handle(self, **options):
        self.verbosity = options["verbosity"]
        self.interactive = options["interactive"]
        app_label = options["app_label"]
        start_migration_name = options["start_migration_name"]
        migration_name = options["migration_name"]
        no_optimize = options["no_optimize"]
        squashed_name = options["squashed_name"]
        include_header = options["include_header"]
        # Validate app_label.
        try:
            apps.get_app_config(app_label)
        except LookupError as err:
            raise CommandError(str(err))
        # Load the current graph state, check the app and migration they asked
        # for exists.
        loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
        if app_label not in loader.migrated_apps:
            raise CommandError(
                "App '%s' does not have migrations (so squashmigrations on "
                "it makes no sense)" % app_label
            )

        migration = self.find_migration(loader, app_label, migration_name)

        # Work out the list of predecessor migrations
        migrations_to_squash = [
            loader.get_migration(al, mn)
            for al, mn in loader.graph.forwards_plan(
                (migration.app_label, migration.name)
            )
            if al == migration.app_label
        ]

        if start_migration_name:
            start_migration = self.find_migration(
                loader, app_label, start_migration_name
            )
            start = loader.get_migration(
                start_migration.app_label, start_migration.name
            )
            try:
                start_index = migrations_to_squash.index(start)
                migrations_to_squash = migrations_to_squash[start_index:]
            except ValueError:
                raise CommandError(
                    "The migration '%s' cannot be found. Maybe it comes after "
                    "the migration '%s'?\n"
                    "Have a look at:\n"
                    "  python manage.py showmigrations %s\n"
                    "to debug this issue." % (start_migration, migration, app_label)
                )

        # Tell them what we're doing and optionally ask if we should proceed
        if self.verbosity > 0 or self.interactive:
            self.stdout.write(
                self.style.MIGRATE_HEADING("Will squash the following migrations:")
            )
            for migration in migrations_to_squash:
                self.stdout.write(" - %s" % migration.name)

            if self.interactive:
                answer = None
                while not answer or answer not in "yn":
                    answer = input("Do you wish to proceed? [yN] ")
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
        # We need to take all dependencies from the first migration in the list
        # as it may be 0002 depending on 0001
        first_migration = True
        for smigration in migrations_to_squash:
            if smigration.replaces:
                raise CommandError(
                    "You cannot squash squashed migrations! Please transition it to a "
                    "normal migration first: https://docs.djangoproject.com/en/%s/"
                    "topics/migrations/#squashing-migrations" % get_docs_version()
                )
            operations.extend(smigration.operations)
            for dependency in smigration.dependencies:
                if isinstance(dependency, SwappableTuple):
                    if settings.AUTH_USER_MODEL == dependency.setting:
                        dependencies.add(("__setting__", "AUTH_USER_MODEL"))
                    else:
                        dependencies.add(dependency)
                elif dependency[0] != smigration.app_label or first_migration:
                    dependencies.add(dependency)
            first_migration = False

        if no_optimize:
            if self.verbosity > 0:
                self.stdout.write(
                    self.style.MIGRATE_HEADING("(Skipping optimization.)")
                )
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
                        "  Optimized from %s operations to %s operations."
                        % (len(operations), len(new_operations))
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
        subclass = type(
            "Migration",
            (migrations.Migration,),
            {
                "dependencies": dependencies,
                "operations": new_operations,
                "replaces": replaces,
            },
        )
        if start_migration_name:
            if squashed_name:
                # Use the name from --squashed-name.
                prefix, _ = start_migration.name.split("_", 1)
                name = "%s_%s" % (prefix, squashed_name)
            else:
                # Generate a name.
                name = "%s_squashed_%s" % (start_migration.name, migration.name)
            new_migration = subclass(name, app_label)
        else:
            name = "0001_%s" % (squashed_name or "squashed_%s" % migration.name)
            new_migration = subclass(name, app_label)
            new_migration.initial = True

        # Write out the new migration file
        writer = MigrationWriter(new_migration, include_header)
        if os.path.exists(writer.path):
            raise CommandError(
                f"Migration {new_migration.name} already exists. Use a different name."
            )
        with open(writer.path, "w", encoding="utf-8") as fh:
            fh.write(writer.as_string())
        run_formatters([writer.path])

        if self.verbosity > 0:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "Created new squashed migration %s" % writer.path
                )
                + "\n"
                "  You should commit this migration but leave the old ones in place;\n"
                "  the new migration will be used for new installs. Once you are sure\n"
                "  all instances of the codebase have applied the migrations you "
                "squashed,\n"
                "  you can delete them."
            )
            if writer.needs_manual_porting:
                self.stdout.write(
                    self.style.MIGRATE_HEADING("Manual porting required") + "\n"
                    "  Your migrations contained functions that must be manually "
                    "copied over,\n"
                    "  as we could not safely copy their implementation.\n"
                    "  See the comment at the top of the squashed migration for "
                    "details."
                )
                if shutil.which("black"):
                    self.stdout.write(
                        self.style.WARNING(
                            "Squashed migration couldn't be formatted using the "
                            '"black" command. You can call it manually.'
                        )
                    )

    def find_migration(self, loader, app_label, name):
        try:
            return loader.get_migration_by_prefix(app_label, name)
        except AmbiguityError:
            raise CommandError(
                "More than one migration matches '%s' in app '%s'. Please be "
                "more specific." % (name, app_label)
            )
        except KeyError:
            raise CommandError(
                "Cannot find a migration matching '%s' from app '%s'."
                % (name, app_label)
            )
