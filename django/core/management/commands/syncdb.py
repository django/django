from optparse import make_option
import itertools
import traceback

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from django.core.management.color import no_style
from django.core.management.sql import custom_sql_for_model, emit_post_sync_signal, emit_pre_sync_signal
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
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
    help = "Create the database tables for all apps in INSTALLED_APPS whose tables haven't already been created."

    def handle_noargs(self, **options):

        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        show_traceback = options.get('traceback')
        load_initial_data = options.get('load_initial_data')

        self.style = no_style()

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

        db = options.get('database')
        connection = connections[db]
        cursor = connection.cursor()

        # Get a list of already installed *models* so that references work right.
        tables = connection.introspection.table_names()
        seen_models = connection.introspection.installed_models(tables)
        created_models = set()
        pending_references = {}

        # Build the manifest of apps and models that are to be synchronized
        all_models = [
            (app.__name__.split('.')[-2],
                [m for m in models.get_models(app, include_auto_created=True)
                if router.allow_syncdb(db, m)])
            for app in models.get_apps()
        ]

        def model_installed(model):
            opts = model._meta
            converter = connection.introspection.table_name_converter
            return not ((converter(opts.db_table) in tables) or
                (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))

        manifest = SortedDict(
            (app_name, list(filter(model_installed, model_list)))
            for app_name, model_list in all_models
        )

        create_models = set([x for x in itertools.chain(*manifest.values())])
        emit_pre_sync_signal(create_models, verbosity, interactive, db)

        # Create the tables for each model
        if verbosity >= 1:
            self.stdout.write("Creating tables ...\n")
        with transaction.commit_on_success_unless_managed(using=db):
            for app_name, model_list in manifest.items():
                for model in model_list:
                    # Create the model's database table, if it doesn't already exist.
                    if verbosity >= 3:
                        self.stdout.write("Processing %s.%s model\n" % (app_name, model._meta.object_name))
                    sql, references = connection.creation.sql_create_model(model, self.style, seen_models)
                    seen_models.add(model)
                    created_models.add(model)
                    for refto, refs in references.items():
                        pending_references.setdefault(refto, []).extend(refs)
                        if refto in seen_models:
                            sql.extend(connection.creation.sql_for_pending_references(refto, self.style, pending_references))
                    sql.extend(connection.creation.sql_for_pending_references(model, self.style, pending_references))
                    if verbosity >= 1 and sql:
                        self.stdout.write("Creating table %s\n" % model._meta.db_table)
                    for statement in sql:
                        cursor.execute(statement)
                    tables.append(connection.introspection.table_name_converter(model._meta.db_table))

        # Send the post_syncdb signal, so individual apps can do whatever they need
        # to do at this point.
        emit_post_sync_signal(created_models, verbosity, interactive, db)

        # The connection may have been closed by a syncdb handler.
        cursor = connection.cursor()

        # Install custom SQL for the app (but only if this
        # is a model we've just created)
        if verbosity >= 1:
            self.stdout.write("Installing custom SQL ...\n")
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    custom_sql = custom_sql_for_model(model, self.style, connection)
                    if custom_sql:
                        if verbosity >= 2:
                            self.stdout.write("Installing custom SQL for %s.%s model\n" % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=db):
                                for sql in custom_sql:
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("Failed to install custom SQL for %s.%s model: %s\n" % \
                                                (app_name, model._meta.object_name, e))
                            if show_traceback:
                                traceback.print_exc()
                    else:
                        if verbosity >= 3:
                            self.stdout.write("No custom SQL for %s.%s model\n" % (app_name, model._meta.object_name))

        if verbosity >= 1:
            self.stdout.write("Installing indexes ...\n")
        # Install SQL indices for all newly created models
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    index_sql = connection.creation.sql_indexes_for_model(model, self.style)
                    if index_sql:
                        if verbosity >= 2:
                            self.stdout.write("Installing index for %s.%s model\n" % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=db):
                                for sql in index_sql:
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("Failed to install index for %s.%s model: %s\n" % \
                                                (app_name, model._meta.object_name, e))

        # Load initial_data fixtures (unless that has been disabled)
        if load_initial_data:
            call_command('loaddata', 'initial_data', verbosity=verbosity,
                         database=db, skip_validation=True)
