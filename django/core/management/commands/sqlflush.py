from django.core.management.base import BaseCommand
from django.core.management.sql import sql_flush
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = (
        "Returns a list of the SQL statements required to return all tables in "
        "the database to the state they were in just after they were installed."
    )

    output_transaction = True

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to print the SQL for. Defaults to the "default" database.',
        )

    def handle(self, **options):
        sql_statements = sql_flush(self.style, connections[options['database']], only_django=True)
        if not sql_statements and options['verbosity'] >= 1:
            self.stderr.write('No tables found.')
        return '\n'.join(sql_statements)
