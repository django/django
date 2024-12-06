from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.loader import AmbiguityError, MigrationLoader


class Command(BaseCommand):
    help = "Prints the SQL statements for the named migration."

    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label", help="App label of the application containing the migration."
        )
        parser.add_argument(
            "migration_name", help="Migration name to print the SQL for."
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help=(
                'Nominates a database to create SQL for. Defaults to the "default" '
                "database."
            ),
        )
        parser.add_argument(
            "--backwards",
            action="store_true",
            help="Creates SQL to unapply the migration, rather than to apply it",
        )

    def execute(self, *args, **options):
        # sqlmigrate doesn't support coloring its output, so make the
        # BEGIN/COMMIT statements added by output_transaction colorless also.
        self.style.SQL_KEYWORD = lambda noop: noop
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        # Get the database we're operating from
        connection = connections[options["database"]]

        # Load up a loader to get all the migration data, but don't replace
        # migrations.
        loader = MigrationLoader(connection, replace_migrations=False)

        # Resolve command-line arguments into a migration
        app_label, migration_name = options["app_label"], options["migration_name"]
        # Validate app_label
        try:
            apps.get_app_config(app_label)
        except LookupError as err:
            raise CommandError(str(err))
        if app_label not in loader.migrated_apps:
            raise CommandError("App '%s' does not have migrations" % app_label)
        try:
            migration = loader.get_migration_by_prefix(app_label, migration_name)
        except AmbiguityError:
            raise CommandError(
                "More than one migration matches '%s' in app '%s'. Please be more "
                "specific." % (migration_name, app_label)
            )
        except KeyError:
            raise CommandError(
                "Cannot find a migration matching '%s' from app '%s'. Is it in "
                "INSTALLED_APPS?" % (migration_name, app_label)
            )
        target = (app_label, migration.name)

        # Show begin/end around output for atomic migrations, if the database
        # supports transactional DDL.
        self.output_transaction = (
            migration.atomic and connection.features.can_rollback_ddl
        )

        # Make a plan that represents just the requested migrations and show SQL
        # for it
        plan = [(loader.graph.nodes[target], options["backwards"])]
        sql_statements = loader.collect_sql(plan)
        if not sql_statements and options["verbosity"] >= 1:
            self.stderr.write("No operations found.")
        return "\n".join(sql_statements)
