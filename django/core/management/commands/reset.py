from optparse import make_option

from django.core.management.base import AppCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import sql_reset
from django.db import connections, transaction, DEFAULT_DB_ALIAS

class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to reset. '
                'Defaults to the "default" database.'),
    )
    help = "Executes ``sqlreset`` for the given app(s) in the current database."
    args = '[appname ...]'

    output_transaction = True

    def handle_app(self, app, **options):
        # This command breaks a lot and should be deprecated
        import warnings
        warnings.warn(
            'This command has been deprecated. The command ``flush`` can be used to delete everything. You can also use ALTER TABLE or DROP TABLE statements manually.',
            DeprecationWarning
        )
        using = options.get('database')
        connection = connections[using]

        app_name = app.__name__.split('.')[-2]
        self.style = no_style()

        sql_list = sql_reset(app, self.style, connection)

        if options.get('interactive'):
            confirm = raw_input("""
You have requested a database reset.
This will IRREVERSIBLY DESTROY any data for
the "%s" application in the database "%s".
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """ % (app_name, connection.settings_dict['NAME']))
        else:
            confirm = 'yes'

        if confirm == 'yes':
            try:
                cursor = connection.cursor()
                for sql in sql_list:
                    cursor.execute(sql)
            except Exception, e:
                transaction.rollback_unless_managed()
                raise CommandError("""Error: %s couldn't be reset. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the database tables doesn't exist.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlreset %s'. That's the SQL this command wasn't able to run.
The full error: %s""" % (app_name, app_name, e))
            transaction.commit_unless_managed()
        else:
            print "Reset cancelled."
