from optparse import make_option

from django.core.management.base import AppCommand
from django.db import connections, models

class Command(AppCommand):
    help = 'Prints the SQL statements for resetting sequences for the given app name(s).'

    option_list = AppCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default='default', help='Selects what database to print the SQL for.'),
    )

    output_transaction = True

    def handle_app(self, app, **options):
        connection = connections[options['database']]
        return u'\n'.join(connection.ops.sequence_reset_sql(self.style, models.get_models(app))).encode('utf-8')
