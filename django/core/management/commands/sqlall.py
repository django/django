from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import AppCommand
from django.core.management.sql import sql_all
from django.db import connections, DEFAULT_DB_ALIAS


class Command(AppCommand):
    help = "Prints the CREATE TABLE, custom SQL and CREATE INDEX SQL statements for the given model module name(s)."

    option_list = AppCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to print the '
                'SQL for.  Defaults to the "default" database.'),
    )

    output_transaction = True

    def handle_app_config(self, app_config, **options):
        if app_config.models_module is None:
            return
        connection = connections[options.get('database')]
        statements = sql_all(app_config, self.style, connection)
        return '\n'.join(statements)
