from __future__ import unicode_literals

from optparse import make_option

from freedom.core.management.base import NoArgsCommand
from freedom.core.management.sql import sql_flush
from freedom.db import connections, DEFAULT_DB_ALIAS


class Command(NoArgsCommand):
    help = "Returns a list of the SQL statements required to return all tables in the database to the state they were in just after they were installed."

    option_list = NoArgsCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to print the '
                'SQL for.  Defaults to the "default" database.'),
    )

    output_transaction = True

    def handle_noargs(self, **options):
        return '\n'.join(sql_flush(self.style, connections[options.get('database')], only_freedom=True))
