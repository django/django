from optparse import make_option
import itertools
import traceback

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from django.core.management.color import color_style, no_style
from django.core.management.sql import custom_sql_for_model, emit_post_sync_signal, emit_pre_sync_signal
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
from django.db.migrations.executor import MigrationExecutor
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--no-initial-data', action='store_false', dest='load_initial_data', default=True,
            help='Tells Django not to load any initial data after database synchronization.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to synchronize. '
                'Defaults to the "default" database.'),
    )

    help = "Updates database schema. Manages both apps with migrations and those without."

    def handle_noargs(self, **options):

        self.verbosity = int(options.get('verbosity'))
        self.interactive = options.get('interactive')
        self.show_traceback = options.get('traceback')
        self.load_initial_data = options.get('load_initial_data')
        self.test_database = options.get('test_database', False)

        self.style = color_style()

        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        for app_name in settings.INSTALLED_APPS:
            try:
                import_module('.management', app_name)
            except ImportError as exc:
                # This is slightly hackish. We want to ignore ImportErrors
                # if the "management" module itself is missing -- but we don't
                # want to ignore the exception if the management module exists
                # but raises an ImportError for some reason. The only way we
                # can do this is to check the text of the exception. Note that
                # we're a bit broad in how we check the text, because different
                # Python implementations may not use the same text.
                # CPython uses the text "No module named management"
                # PyPy uses "No module named myproject.myapp.management"
                msg = exc.args[0]
                if not msg.startswith('No module named') or 'management' not in msg:
                    raise

        # Get the database we're operating from
        db = options.get('database')
        connection = connections[db]

        # Work out which apps have migrations and which do not
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Calculating migration plan:"))
        executor = MigrationExecutor(connection, self.migration_progress_callback)
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_LABEL("  Apps without migrations: ") + (", ".join(executor.loader.unmigrated_apps) or "(none)"))

        # Work out what targets they want, and then make a migration plan
        # TODO: Let users select targets
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)

        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_LABEL("  Apps with migrations:    ") + (", ".join(executor.loader.migrated_apps) or "(none)"))

        # Run the syncdb phase.
        # If you ever manage to get rid of this, I owe you many, many drinks.
        self.stdout.write(self.style.MIGRATE_HEADING("Synchronizing apps without migrations:"))
        self.sync_apps(connection, executor.loader.unmigrated_apps)

        # Migrate!
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Running migrations:"))
        if not plan:
            if self.verbosity >= 1:
                self.stdout.write("  No migrations needed.")
        else:
            executor.migrate(targets, plan)

    def migration_progress_callback(self, action, migration):
        if self.verbosity >= 1:
            if action == "apply_start":
                self.stdout.write("  Applying %s... " % migration)
                self.stdout.flush()
            elif action == "apply_success":
                self.stdout.write("  OK\n")
            elif action == "unapply_start":
                self.stdout.write("  Unapplying %s... " % migration)
                self.stdout.flush()
            elif action == "unapply_success":
                self.stdout.write("  OK\n")

    def sync_apps(self, connection, apps):
        "Runs the old syncdb-style operation on a list of apps."
        cursor = connection.cursor()

        # Get a list of already installed *models* so that references work right.
        tables = connection.introspection.table_names()
        seen_models = connection.introspection.installed_models(tables)
        created_models = set()
        pending_references = {}

        # Build the manifest of apps and models that are to be synchronized
        all_models = [
            (app.__name__.split('.')[-2],
                [
                    m for m in models.get_models(app, include_auto_created=True)
                    if router.allow_syncdb(connection.alias, m)
                ])
            for app in models.get_apps() if app.__name__.split('.')[-2] in apps
        ]

        def model_installed(model):
            opts = model._meta
            converter = connection.introspection.table_name_converter
            # Note that if a model is unmanaged we short-circuit and never try to install it
            return not ((converter(opts.db_table) in tables) or
                (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))

        manifest = SortedDict(
            (app_name, list(filter(model_installed, model_list)))
            for app_name, model_list in all_models
        )

        create_models = set([x for x in itertools.chain(*manifest.values())])
        emit_pre_sync_signal(create_models, self.verbosity, self.interactive, connection.alias)

        # Create the tables for each model
        if self.verbosity >= 1:
            self.stdout.write("  Creating tables...\n")
        with transaction.commit_on_success_unless_managed(using=connection.alias):
            for app_name, model_list in manifest.items():
                for model in model_list:
                    # Create the model's database table, if it doesn't already exist.
                    if self.verbosity >= 3:
                        self.stdout.write("    Processing %s.%s model\n" % (app_name, model._meta.object_name))
                    sql, references = connection.creation.sql_create_model(model, no_style(), seen_models)
                    seen_models.add(model)
                    created_models.add(model)
                    for refto, refs in references.items():
                        pending_references.setdefault(refto, []).extend(refs)
                        if refto in seen_models:
                            sql.extend(connection.creation.sql_for_pending_references(refto, no_style(), pending_references))
                    sql.extend(connection.creation.sql_for_pending_references(model, no_style(), pending_references))
                    if self.verbosity >= 1 and sql:
                        self.stdout.write("    Creating table %s\n" % model._meta.db_table)
                    for statement in sql:
                        cursor.execute(statement)
                    tables.append(connection.introspection.table_name_converter(model._meta.db_table))

        # Send the post_syncdb signal, so individual apps can do whatever they need
        # to do at this point.
        emit_post_sync_signal(created_models, self.verbosity, self.interactive, connection.alias)

        # The connection may have been closed by a syncdb handler.
        cursor = connection.cursor()

        # Install custom SQL for the app (but only if this
        # is a model we've just created)
        if self.verbosity >= 1:
            self.stdout.write("  Installing custom SQL...\n")
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    custom_sql = custom_sql_for_model(model, no_style(), connection)
                    if custom_sql:
                        if self.verbosity >= 2:
                            self.stdout.write("    Installing custom SQL for %s.%s model\n" % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=connection.alias):
                                for sql in custom_sql:
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("    Failed to install custom SQL for %s.%s model: %s\n" % (app_name, model._meta.object_name, e))
                            if self.show_traceback:
                                traceback.print_exc()
                    else:
                        if self.verbosity >= 3:
                            self.stdout.write("    No custom SQL for %s.%s model\n" % (app_name, model._meta.object_name))

        if self.verbosity >= 1:
            self.stdout.write("  Installing indexes...\n")
        # Install SQL indices for all newly created models
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    index_sql = connection.creation.sql_indexes_for_model(model, no_style())
                    if index_sql:
                        if self.verbosity >= 2:
                            self.stdout.write("    Installing index for %s.%s model\n" % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=connection.alias):
                                for sql in index_sql:
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("    Failed to install index for %s.%s model: %s\n" % (app_name, model._meta.object_name, e))

        # Load initial_data fixtures (unless that has been disabled)
        if self.load_initial_data:
            call_command('loaddata', 'initial_data', verbosity=self.verbosity, database=connection.alias, skip_validation=True)
