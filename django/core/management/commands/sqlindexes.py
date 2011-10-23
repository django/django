from optparse import make_option

from django.core.management.base import AppCommand
from django.core.management.sql import sql_indexes
from django.db import connections, DEFAULT_DB_ALIAS

class Command(AppCommand):
    help = "Prints the CREATE INDEX SQL statements for the given model module name(s)."

    option_list = AppCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to print the '
                'SQL for.  Defaults to the "default" database.'),

    )

    output_transaction = True

    def handle_app(self, app, **options):
        return u'\n'.join(sql_indexes(app, self.style, connections[options.get('database')])).encode('utf-8')
