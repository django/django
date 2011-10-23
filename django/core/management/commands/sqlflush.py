from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.core.management.sql import sql_flush
from django.db import connections, DEFAULT_DB_ALIAS

class Command(NoArgsCommand):
    help = "Returns a list of the SQL statements required to return all tables in the database to the state they were in just after they were installed."

    option_list = NoArgsCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to print the '
                'SQL for.  Defaults to the "default" database.'),
    )

    output_transaction = True

    def handle_noargs(self, **options):
        return u'\n'.join(sql_flush(self.style, connections[options.get('database')], only_django=True)).encode('utf-8')
