import warnings
from optparse import make_option

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS
from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.six.moves import input


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

        try:
            apps.get_model('auth', 'Permission')
        except LookupError:
            return

        UserModel = get_user_model()

        if not UserModel._default_manager.exists() and options.get('interactive'):
            msg = ("\nYou have installed Django's auth system, and "
                "don't have any superusers defined.\nWould you like to create one "
                "now? (yes/no): ")
            confirm = input(msg)
            while 1:
                if confirm not in ('yes', 'no'):
                    confirm = input('Please enter either "yes" or "no": ')
                    continue
                if confirm == 'yes':
                    call_command("createsuperuser", interactive=True, database=options['database'])
                break
