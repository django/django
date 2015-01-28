from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = ("Runs the command-line client for specified database, or the "
        "default database if none is provided.")

    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database onto which to '
            'open a shell. Defaults to the "default" database.')

    def handle(self, **options):
        connection = connections[options.get('database')]
        try:
            connection.client.runshell()
        except OSError:
            # Note that we're assuming OSError means that the client program
            # isn't installed. There's a possibility OSError would be raised
            # for some other reason, in which case this error message would be
            # inaccurate. Still, this message catches the common case.
            raise CommandError('You appear not to have the %r program installed or on your path.' %
                connection.client.executable_name)
