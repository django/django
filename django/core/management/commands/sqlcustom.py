from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import AppCommand
from django.core.management.sql import sql_custom
from django.db import connections, DEFAULT_DB_ALIAS

class Command(AppCommand):
    help = "Prints the custom table modifying SQL statements for the given app name(s)."

    option_list = AppCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to print the '
                'SQL for.  Defaults to the "default" database.'),
    )

    output_transaction = True

    def handle_app(self, app, **options):
        return '\n'.join(sql_custom(app, self.style, connections[options.get('database')]))
