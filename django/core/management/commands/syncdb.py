import warnings
from optparse import make_option

from django.db import DEFAULT_DB_ALIAS
from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from django.utils.deprecation import RemovedInDjango19Warning


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--no-initial-data', action='store_false', dest='load_initial_data', default=True,
            help='Tells Django not to load any initial data after database synchronization.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to synchronize. '
                'Defaults to the "default" database.'),
    )
    help = "Deprecated - use 'migrate' instead."

    def handle_noargs(self, **options):
        warnings.warn("The syncdb command will be removed in Django 1.9", RemovedInDjango19Warning)
        call_command("migrate", **options)
