from django.core.management.base import NoArgsCommand, CommandError

class Command(NoArgsCommand):
    help = "Runs the command-line client for the current DATABASE_ENGINE."

    requires_model_validation = False

    def handle_noargs(self, **options):
        from django.db import connection
        try:
            connection.client.runshell()
        except OSError:
            # Note that we're assuming OSError means that the client program
            # isn't installed. There's a possibility OSError would be raised
            # for some other reason, in which case this error message would be
            # inaccurate. Still, this message catches the common case.
            raise CommandError('You appear not to have the %r program installed or on your path.' % \
                connection.client.executable_name)
