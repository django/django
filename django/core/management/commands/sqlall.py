from __future__ import unicode_literals

from django.core.management.base import AppCommand
from django.core.management.sql import sql_all
from django.db import DEFAULT_DB_ALIAS, connections


class Command(AppCommand):
    help = "Prints the CREATE TABLE, custom SQL and CREATE INDEX SQL statements for the given model module name(s)."

    output_transaction = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to print the SQL for. Defaults to the '
                 '"default" database.')

    def handle_app_config(self, app_config, **options):
        if app_config.models_module is None:
            return
        connection = connections[options['database']]
        statements = sql_all(app_config, self.style, connection)
        return '\n'.join(statements)
