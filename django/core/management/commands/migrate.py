# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools
import time
import traceback
import warnings
from collections import OrderedDict
from importlib import import_module

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import (
    custom_sql_for_model, emit_post_migrate_signal, emit_pre_migrate_signal,
)
from django.db import DEFAULT_DB_ALIAS, connections, router, transaction
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import AmbiguityError
from django.db.migrations.state import ProjectState
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.module_loading import module_has_submodule


class Command(BaseCommand):
    help = "Updates database schema. Manages both apps with migrations and those without."

    def add_arguments(self, parser):
        parser.add_argument('app_label', nargs='?',
            help='App label of an application to synchronize the state.')
        parser.add_argument('migration_name', nargs='?',
            help=(
                'Database state will be brought to the state after that '
                'migration. Use the name "zero" to unapply all migrations.'
            ),
        )
        parser.add_argument('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.')
        parser.add_argument('--no-initial-data', action='store_false', dest='load_initial_data', default=True,
            help='Tells Django not to load any initial data after database synchronization.')
        parser.add_argument('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to synchronize. '
                'Defaults to the "default" database.')
        parser.add_argument('--fake', action='store_true', dest='fake', default=False,
            help='Mark migrations as run without actually running them')
        parser.add_argument('--fake-initial', action='store_true', dest='fake_initial', default=False,
            help='Detect if tables already exist and fake-apply initial migrations if so. Make sure '
                 'that the current database schema matches your initial migration before using this '
                 'flag. Django will only check for an existing table name.')
        parser.add_argument('--list', '-l', action='store_true', dest='list', default=False,
            help='Show a list of all known migrations and which are applied')

    def handle(self, *args, **options):

        self.verbosity = options.get('verbosity')
        self.interactive = options.get('interactive')
        self.show_traceback = options.get('traceback')
        self.load_initial_data = options.get('load_initial_data')

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
            warnings.warn(
                "The 'migrate --list' command is deprecated. Use 'showmigrations' instead.",
                RemovedInDjango20Warning, stacklevel=2)
            self.stdout.ending = None  # Remove when #21429 is fixed
            return call_command(
                'showmigrations',
                '--list',
                app_labels=[options['app_label']] if options['app_label'] else None,
                database=db,
                no_color=options.get('no_color'),
                settings=options.get('settings'),
                stdout=self.stdout,
                traceback=self.show_traceback,
                verbosity=self.verbosity,
            )

        # Hook for backends needing any database preparation
        connection.prepare_database()
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
            raise CommandError(
                "Conflicting migrations detected (%s).\nTo fix them run "
                "'python manage.py makemigrations --merge'" % name_str
            )

        # If they supplied command line arguments, work out what they mean.
        run_syncdb = False
        target_app_labels_only = True
        if options['app_label'] and options['migration_name']:
            app_label, migration_name = options['app_label'], options['migration_name']
            if app_label not in executor.loader.migrated_apps:
                raise CommandError(
                    "App '%s' does not have migrations (you cannot selectively "
                    "sync unmigrated apps)" % app_label
                )
            if migration_name == "zero":
                targets = [(app_label, None)]
            else:
                try:
                    migration = executor.loader.get_migration_by_prefix(app_label, migration_name)
                except AmbiguityError:
                    raise CommandError(
                        "More than one migration matches '%s' in app '%s'. "
                        "Please be more specific." %
                        (migration_name, app_label)
                    )
                except KeyError:
                    raise CommandError("Cannot find a migration matching '%s' from app '%s'." % (
                        migration_name, app_label))
                targets = [(app_label, migration.name)]
            target_app_labels_only = False
        elif options['app_label']:
            app_label = options['app_label']
            if app_label not in executor.loader.migrated_apps:
                raise CommandError(
                    "App '%s' does not have migrations (you cannot selectively "
                    "sync unmigrated apps)" % app_label
                )
            targets = [key for key in executor.loader.graph.leaf_nodes() if key[0] == app_label]
        else:
            targets = executor.loader.graph.leaf_nodes()
            run_syncdb = True

        plan = executor.migration_plan(targets)

        # Print some useful info
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Operations to perform:"))
            if run_syncdb and executor.loader.unmigrated_apps:
                self.stdout.write(
                    self.style.MIGRATE_LABEL("  Synchronize unmigrated apps: ") +
                    (", ".join(executor.loader.unmigrated_apps))
                )
            if target_app_labels_only:
                self.stdout.write(
                    self.style.MIGRATE_LABEL("  Apply all migrations: ") +
                    (", ".join(set(a for a, n in targets)) or "(none)")
                )
            else:
                if targets[0][1] is None:
                    self.stdout.write(self.style.MIGRATE_LABEL(
                        "  Unapply all migrations: ") + "%s" % (targets[0][0], )
                    )
                else:
                    self.stdout.write(self.style.MIGRATE_LABEL(
                        "  Target specific migration: ") + "%s, from %s"
                        % (targets[0][1], targets[0][0])
                    )

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
            emit_pre_migrate_signal([], self.verbosity, self.interactive, connection.alias)

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
                    self.stdout.write(self.style.NOTICE(
                        "  Your models have changes that are not yet reflected "
                        "in a migration, and so won't be applied."
                    ))
                    self.stdout.write(self.style.NOTICE(
                        "  Run 'manage.py makemigrations' to make new "
                        "migrations, and then re-run 'manage.py migrate' to "
                        "apply them."
                    ))
        else:
            fake = options.get("fake")
            fake_initial = options.get("fake_initial")
            executor.migrate(targets, plan, fake=fake, fake_initial=fake_initial)

        # Send the post_migrate signal, so individual apps can do whatever they need
        # to do at this point.
        emit_post_migrate_signal(created_models, self.verbosity, self.interactive, connection.alias)

    def migration_progress_callback(self, action, migration=None, fake=False):
        if self.verbosity >= 1:
            compute_time = self.verbosity > 1
            if action == "apply_start":
                if compute_time:
                    self.start = time.time()
                self.stdout.write("  Applying %s..." % migration, ending="")
                self.stdout.flush()
            elif action == "apply_success":
                elapsed = " (%.3fs)" % (time.time() - self.start) if compute_time else ""
                if fake:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" FAKED" + elapsed))
                else:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" OK" + elapsed))
            elif action == "unapply_start":
                if compute_time:
                    self.start = time.time()
                self.stdout.write("  Unapplying %s..." % migration, ending="")
                self.stdout.flush()
            elif action == "unapply_success":
                elapsed = " (%.3fs)" % (time.time() - self.start) if compute_time else ""
                if fake:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" FAKED" + elapsed))
                else:
                    self.stdout.write(self.style.MIGRATE_SUCCESS(" OK" + elapsed))
            elif action == "render_start":
                if compute_time:
                    self.start = time.time()
                self.stdout.write("  Rendering model states...", ending="")
                self.stdout.flush()
            elif action == "render_success":
                elapsed = " (%.3fs)" % (time.time() - self.start) if compute_time else ""
                self.stdout.write(self.style.MIGRATE_SUCCESS(" DONE" + elapsed))

    def sync_apps(self, connection, app_labels):
        "Runs the old syncdb-style operation on a list of app_labels."
        cursor = connection.cursor()

        try:
            # Get a list of already installed *models* so that references work right.
            tables = connection.introspection.table_names(cursor)
            created_models = set()

            # Build the manifest of apps and models that are to be synchronized
            all_models = [
                (app_config.label,
                    router.get_migratable_models(app_config, connection.alias, include_auto_created=False))
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
            with transaction.atomic(using=connection.alias, savepoint=connection.features.can_rollback_ddl):
                deferred_sql = []
                for app_name, model_list in manifest.items():
                    for model in model_list:
                        if model._meta.proxy or not model._meta.managed:
                            continue
                        if self.verbosity >= 3:
                            self.stdout.write(
                                "    Processing %s.%s model\n" % (app_name, model._meta.object_name)
                            )
                        with connection.schema_editor() as editor:
                            if self.verbosity >= 1:
                                self.stdout.write("    Creating table %s\n" % model._meta.db_table)
                            editor.create_model(model)
                            deferred_sql.extend(editor.deferred_sql)
                            editor.deferred_sql = []
                        created_models.add(model)

                if self.verbosity >= 1:
                    self.stdout.write("    Running deferred SQL...\n")
                for statement in deferred_sql:
                    cursor.execute(statement)
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
                                self.stdout.write(
                                    "    Installing custom SQL for %s.%s model\n" %
                                    (app_name, model._meta.object_name)
                                )
                            try:
                                with transaction.atomic(using=connection.alias):
                                    for sql in custom_sql:
                                        cursor.execute(sql)
                            except Exception as e:
                                self.stderr.write(
                                    "    Failed to install custom SQL for %s.%s model: %s\n"
                                    % (app_name, model._meta.object_name, e)
                                )
                                if self.show_traceback:
                                    traceback.print_exc()
                        else:
                            if self.verbosity >= 3:
                                self.stdout.write(
                                    "    No custom SQL for %s.%s model\n" %
                                    (app_name, model._meta.object_name)
                                )
        finally:
            cursor.close()

        # Load initial_data fixtures (unless that has been disabled)
        if self.load_initial_data:
            for app_label in app_labels:
                call_command(
                    'loaddata', 'initial_data', verbosity=self.verbosity,
                    database=connection.alias, app_label=app_label,
                    hide_empty=True,
                )

        return created_models
