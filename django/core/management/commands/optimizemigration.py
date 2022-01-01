import sys

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import run_formatters
from django.db import migrations
from django.db.migrations.exceptions import AmbiguityError
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.writer import MigrationWriter
from django.utils.version import get_docs_version


class Command(BaseCommand):
    help = "Optimizes the operations for the named migration."

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="App label of the application to optimize the migration for.",
        )
        parser.add_argument(
            "migration_name", help="Migration name to optimize the operations for."
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with a non-zero status if the migration can be optimized.",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        app_label = options["app_label"]
        migration_name = options["migration_name"]
        check = options["check"]

        # Validate app_label.
        try:
            apps.get_app_config(app_label)
        except LookupError as err:
            raise CommandError(str(err))

        # Load the current graph state.
        loader = MigrationLoader(None)
        if app_label not in loader.migrated_apps:
            raise CommandError(f"App '{app_label}' does not have migrations.")
        # Find a migration.
        try:
            migration = loader.get_migration_by_prefix(app_label, migration_name)
        except AmbiguityError:
            raise CommandError(
                f"More than one migration matches '{migration_name}' in app "
                f"'{app_label}'. Please be more specific."
            )
        except KeyError:
            raise CommandError(
                f"Cannot find a migration matching '{migration_name}' from app "
                f"'{app_label}'."
            )

        # Optimize the migration.
        optimizer = MigrationOptimizer()
        new_operations = optimizer.optimize(migration.operations, migration.app_label)
        if len(migration.operations) == len(new_operations):
            if verbosity > 0:
                self.stdout.write("No optimizations possible.")
            return
        else:
            if verbosity > 0:
                self.stdout.write(
                    "Optimizing from %d operations to %d operations."
                    % (len(migration.operations), len(new_operations))
                )
            if check:
                sys.exit(1)

        # Set the new migration optimizations.
        migration.operations = new_operations

        # Write out the optimized migration file.
        writer = MigrationWriter(migration)
        migration_file_string = writer.as_string()
        if writer.needs_manual_porting:
            if migration.replaces:
                raise CommandError(
                    "Migration will require manual porting but is already a squashed "
                    "migration.\nTransition to a normal migration first: "
                    "https://docs.djangoproject.com/en/%s/topics/migrations/"
                    "#squashing-migrations" % get_docs_version()
                )
            # Make a new migration with those operations.
            subclass = type(
                "Migration",
                (migrations.Migration,),
                {
                    "dependencies": migration.dependencies,
                    "operations": new_operations,
                    "replaces": [(migration.app_label, migration.name)],
                },
            )
            optimized_migration_name = "%s_optimized" % migration.name
            optimized_migration = subclass(optimized_migration_name, app_label)
            writer = MigrationWriter(optimized_migration)
            migration_file_string = writer.as_string()
            if verbosity > 0:
                self.stdout.write(
                    self.style.MIGRATE_HEADING("Manual porting required") + "\n"
                    "  Your migrations contained functions that must be manually "
                    "copied over,\n"
                    "  as we could not safely copy their implementation.\n"
                    "  See the comment at the top of the optimized migration for "
                    "details."
                )
        with open(writer.path, "w", encoding="utf-8") as fh:
            fh.write(migration_file_string)
        run_formatters([writer.path])

        if verbosity > 0:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"Optimized migration {writer.path}")
            )
