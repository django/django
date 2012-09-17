from optparse import make_option

from django.conf import settings
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
from django.core.management import call_command
from django.core.management.base import NoArgsCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import sql_flush, emit_post_sync_signal
from django.utils.importlib import import_module
from django.utils.six.moves import input


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to flush. '
                'Defaults to the "default" database.'),
        make_option('--no-initial-data', action='store_false', dest='load_initial_data', default=True,
 		            help='Tells Django not to load any initial data after database synchronization.'),
    )
    help = ('Returns the database to the state it was in immediately after '
           'syncdb was executed. This means that all data will be removed '
           'from the database, any post-synchronization handlers will be '
           're-executed, and the initial_data fixture will be re-installed.')

    def handle_noargs(self, **options):
        db = options.get('database')
        connection = connections[db]
        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        # 'reset_sequences' is a stealth option
        reset_sequences = options.get('reset_sequences', True)

        self.style = no_style()

        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        for app_name in settings.INSTALLED_APPS:
            try:
                import_module('.management', app_name)
            except ImportError:
                pass

        sql_list = sql_flush(self.style, connection, only_django=True, reset_sequences=reset_sequences)

        if interactive:
            confirm = input("""You have requested a flush of the database.
This will IRREVERSIBLY DESTROY all data currently in the %r database,
and return each table to the state it was in after syncdb.
Are you sure you want to do this?

    Type 'yes' to continue, or 'no' to cancel: """ % connection.settings_dict['NAME'])
        else:
            confirm = 'yes'

        if confirm == 'yes':
            try:
                cursor = connection.cursor()
                for sql in sql_list:
                    cursor.execute(sql)
            except Exception as e:
                transaction.rollback_unless_managed(using=db)
                raise CommandError("""Database %s couldn't be flushed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the expected database tables doesn't exist.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlflush'. That's the SQL this command wasn't able to run.
The full error: %s""" % (connection.settings_dict['NAME'], e))
            transaction.commit_unless_managed(using=db)

            # Emit the post sync signal. This allows individual
            # applications to respond as if the database had been
            # sync'd from scratch.
            all_models = []
            for app in models.get_apps():
                all_models.extend([
                    m for m in models.get_models(app, include_auto_created=True)
                    if router.allow_syncdb(db, m)
                ])
            emit_post_sync_signal(set(all_models), verbosity, interactive, db)

            # Reinstall the initial_data fixture.
            kwargs = options.copy()
            kwargs['database'] = db
            if options.get('load_initial_data'):
                # Reinstall the initial_data fixture.
                call_command('loaddata', 'initial_data', **options)

        else:
            self.stdout.write("Flush cancelled.\n")
