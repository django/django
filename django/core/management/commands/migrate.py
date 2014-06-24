# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from optparse import make_option
from collections import OrderedDict
from importlib import import_module
import itertools
import traceback

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import custom_sql_for_model, emit_post_migrate_signal, emit_pre_migrate_signal
from django.db import connections, router, transaction, DEFAULT_DB_ALIAS
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader, AmbiguityError
from django.db.migrations.state import ProjectState
from django.db.migrations.autodetector import MigrationAutodetector
from django.utils.module_loading import module_has_submodule


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--no-initial-data', action='store_false', dest='load_initial_data', default=True,
            help='Tells Django not to load any initial data after database synchronization.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to synchronize. '
                'Defaults to the "default" database.'),
        make_option('--fake', action='store_true', dest='fake', default=False,
            help='Mark migrations as run without actually running them'),
        make_option('--list', '-l', action='store_true', dest='list', default=False,
            help='Show a list of all known migrations and which are applied'),
    )

    help = "Updates database schema. Manages both apps with migrations and those without."
    args = "[app_label] [migration_name]"

    def handle(self, *args, **options):

        self.verbosity = int(options.get('verbosity'))
        self.interactive = options.get('interactive')
        self.show_traceback = options.get('traceback')
        self.load_initial_data = options.get('load_initial_data')
        self.test_database = options.get('test_database', False)

        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        for app_config in apps.get_app_configs():
            if module_has_submodule(app_config.module, "management"):
                import_module('.management', app_config.name)

        # Get the database we're operating from
        db = options.get('database')
        connection = connections[db]

        # If they asked for a migration listing, quit main execution flow and show it
        if options.get("list", False):
            return self.show_migration_list(connection, args)

        # Work out which apps have migrations and which do not
        executor = MigrationExecutor(connection, self.migration_progress_callback)

        # Before anything else, see if there's conflicting apps and drop out
        # hard if there are any
        conflicts = executor.loader.detect_conflicts()
        if conflicts:
            name_str = "; ".join(
                "%s in %s" % (", ".join(names), app)
                for app, names in conflicts.items()
            )
            raise CommandError("Conflicting migrations detected (%s).\nTo fix them run 'python manage.py makemigrations --merge'" % name_str)

        # If they supplied command line arguments, work out what they mean.
        run_syncdb = False
        target_app_labels_only = True
        if len(args) > 2:
            raise CommandError("Too many command-line arguments (expecting 'app_label' or 'app_label migrationname')")
        elif len(args) == 2:
            app_label, migration_name = args
            if app_label not in executor.loader.migrated_apps:
                raise CommandError("App '%s' does not have migrations (you cannot selectively sync unmigrated apps)" % app_label)
            if migration_name == "zero":
                targets = [(app_label, None)]
            else:
                try:
                    migration = executor.loader.get_migration_by_prefix(app_label, migration_name)
                except AmbiguityError:
                    raise CommandError("More than one migration matches '%s' in app '%s'. Please be more specific." % (
                        migration_name, app_label))
                except KeyError:
                    raise CommandError("Cannot find a migration matching '%s' from app '%s'." % (
                        migration_name, app_label))
                targets = [(app_label, migration.name)]
            target_app_labels_only = False
        elif len(args) == 1:
            app_label = args[0]
            if app_label not in executor.loader.migrated_apps:
                raise CommandError("App '%s' does not have migrations (you cannot selectively sync unmigrated apps)" % app_label)
            targets = [key for key in executor.loader.graph.leaf_nodes() if key[0] == app_label]
        else:
            targets = executor.loader.graph.leaf_nodes()
            run_syncdb = True

        plan = executor.migration_plan(targets)

        # Print some useful info
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Operations to perform:"))
            if run_syncdb and executor.loader.unmigrated_apps:
                self.stdout.write(self.style.MIGRATE_LABEL("  Synchronize unmigrated apps: ") + (", ".join(executor.loader.unmigrated_apps)))
            if target_app_labels_only:
                self.stdout.write(self.style.MIGRATE_LABEL("  Apply all migrations: ") + (", ".join(set(a for a, n in targets)) or "(none)"))
            else:
                if targets[0][1] is None:
                    self.stdout.write(self.style.MIGRATE_LABEL("  Unapply all migrations: ") + "%s" % (targets[0][0], ))
                else:
                    self.stdout.write(self.style.MIGRATE_LABEL("  Target specific migration: ") + "%s, from %s" % (targets[0][1], targets[0][0]))

        # Run the syncdb phase.
        # If you ever manage to get rid of this, I owe you many, many drinks.
        # Note that pre_migrate is called from inside here, as it needs
        # the list of models about to be installed.
        if run_syncdb and executor.loader.unmigrated_apps:
            if self.verbosity >= 1:
                self.stdout.write(self.style.MIGRATE_HEADING("Synchronizing apps without migrations:"))
            created_models = self.sync_apps(connection, executor.loader.unmigrated_apps)
        else:
            created_models = []

        # The test runner requires us to flush after a syncdb but before migrations,
        # so do that here.
        if options.get("test_flush", False):
            call_command(
                'flush',
                verbosity=max(self.verbosity - 1, 0),
                interactive=False,
                database=db,
                reset_sequences=False,
                inhibit_post_migrate=True,
            )

        # Migrate!
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Running migrations:"))
        if not plan:
            if self.verbosity >= 1:
                self.stdout.write("  No migrations to apply.")
                # If there's changes that aren't in migrations yet, tell them how to fix it.
                autodetector = MigrationAutodetector(
                    executor.loader.project_state(),
                    ProjectState.from_apps(apps),
                )
                changes = autodetector.changes(graph=executor.loader.graph)
                if changes:
                    self.stdout.write(self.style.NOTICE("  Your models have changes that are not yet reflected in a migration, and so won't be applied."))
                    self.stdout.write(self.style.NOTICE("  Run 'manage.py makemigrations' to make new migrations, and then re-run 'manage.py migrate' to apply them."))
        else:
            executor.migrate(targets, plan, fake=options.get("fake", False))

        # Send the post_migrate signal, so individual apps can do whatever they need
        # to do at this point.
        emit_post_migrate_signal(created_models, self.verbosity, self.interactive, connection.alias)

    def migration_progress_callback(self, action, migration, fake=False):
        if self.verbosity >= 1:
            if action == "apply_start":
                self.stdout.write("  Applying %s..." % migration, ending="")
                self.stdout.flush()
            elif action == "apply_success":
                if fake:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" FAKED"))
                else:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" OK"))
            elif action == "unapply_start":
                self.stdout.write("  Unapplying %s..." % migration, ending="")
                self.stdout.flush()
            elif action == "unapply_success":
                if fake:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" FAKED"))
                else:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" OK"))

    def sync_apps(self, connection, app_labels):
        "Runs the old syncdb-style operation on a list of app_labels."
        cursor = connection.cursor()

        try:
            # Get a list of already installed *models* so that references work right.
            tables = connection.introspection.table_names(cursor)
            seen_models = connection.introspection.installed_models(tables)
            created_models = set()
            pending_references = {}

            # Build the manifest of apps and models that are to be synchronized
            all_models = [
                (app_config.label,
                    router.get_migratable_models(app_config, connection.alias, include_auto_created=True))
                for app_config in apps.get_app_configs()
                if app_config.models_module is not None and app_config.label in app_labels
            ]

            def model_installed(model):
                opts = model._meta
                converter = connection.introspection.table_name_converter
                # Note that if a model is unmanaged we short-circuit and never try to install it
                return not ((converter(opts.db_table) in tables) or
                    (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))

            manifest = OrderedDict(
                (app_name, list(filter(model_installed, model_list)))
                for app_name, model_list in all_models
            )

            create_models = set(itertools.chain(*manifest.values()))
            emit_pre_migrate_signal(create_models, self.verbosity, self.interactive, connection.alias)

            # Create the tables for each model
            if self.verbosity >= 1:
                self.stdout.write("  Creating tables...\n")
            with transaction.atomic(using=connection.alias, savepoint=False):
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

            # We force a commit here, as that was the previous behavior.
            # If you can prove we don't need this, remove it.
            transaction.set_dirty(using=connection.alias)
        finally:
            cursor.close()

        # The connection may have been closed by a syncdb handler.
        cursor = connection.cursor()
        try:
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
        finally:
            cursor.close()

        # Load initial_data fixtures (unless that has been disabled)
        if self.load_initial_data:
            for app_label in app_labels:
                call_command('loaddata', 'initial_data', verbosity=self.verbosity, database=connection.alias, skip_validation=True, app_label=app_label, hide_empty=True)

        return created_models

    def show_migration_list(self, connection, app_names=None):
        """
        Shows a list of all migrations on the system, or only those of
        some named apps.
        """
        # Load migrations from disk/DB
        loader = MigrationLoader(connection)
        graph = loader.graph
        # If we were passed a list of apps, validate it
        if app_names:
            invalid_apps = []
            for app_name in app_names:
                if app_name not in loader.migrated_apps:
                    invalid_apps.append(app_name)
            if invalid_apps:
                raise CommandError("No migrations present for: %s" % (", ".join(invalid_apps)))
        # Otherwise, show all apps in alphabetic order
        else:
            app_names = sorted(loader.migrated_apps)
        # For each app, print its migrations in order from oldest (roots) to
        # newest (leaves).
        for app_name in app_names:
            self.stdout.write(app_name, self.style.MIGRATE_LABEL)
            shown = set()
            for node in graph.leaf_nodes(app_name):
                for plan_node in graph.forwards_plan(node):
                    if plan_node not in shown and plan_node[0] == app_name:
                        # Give it a nice title if it's a squashed one
                        title = plan_node[1]
                        if graph.nodes[plan_node].replaces:
                            title += " (%s squashed migrations)" % len(graph.nodes[plan_node].replaces)
                        # Mark it as applied/unapplied
                        if plan_node in loader.applied_migrations:
                            self.stdout.write(" [X] %s" % title)
                        else:
                            self.stdout.write(" [ ] %s" % title)
                        shown.add(plan_node)
            # If we didn't print anything, then a small message
            if not shown:
                self.stdout.write(" (no migrations)", self.style.MIGRATE_FAILURE)
