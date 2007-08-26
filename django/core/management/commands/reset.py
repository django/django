from django.core.management.base import AppCommand, CommandError
from django.core.management.color import no_style

class Command(AppCommand):
    help = "Executes ``sqlreset`` for the given app(s) in the current database."
    args = '[--noinput] [appname ...]'

    output_transaction = True

    def handle_app(self, app, **options):
        from django.db import connection, transaction
        from django.conf import settings
        from django.core.management.sql import sql_reset

        app_name = app.__name__.split('.')[-2]

        self.style = no_style()

        sql_list = sql_reset(app, self.style)

        if options.get('interactive'):
            confirm = raw_input("""
You have requested a database reset.
This will IRREVERSIBLY DESTROY any data for
the "%s" application in the database "%s".
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """ % (app_name, settings.DATABASE_NAME))
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
