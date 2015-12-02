import time
from django.core.management import BaseCommand, CommandError
from channels import channel_backends, DEFAULT_CHANNEL_BACKEND


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('port', nargs='?',
            help='Optional port number')

    def handle(self, *args, **options):
        # Get the backend to use
        channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        if channel_backend.local_only:
            raise CommandError(
                "You have a process-local channel backend configured, and so cannot run separate interface servers.\n"
                "Configure a network-based backend in CHANNEL_BACKENDS to use this command."
            )
        # Run the interface
        port = int(options.get("port", None) or 8000)
        from channels.interfaces.http_twisted import HttpTwistedInterface
        self.stdout.write("Running twisted/Autobahn HTTP & WebSocket interface server")
        self.stdout.write(" Channel backend: %s" % channel_backend)
        self.stdout.write(" Listening on: 0.0.0.0:%i" % port)
        HttpTwistedInterface(channel_backend=channel_backend, port=port).run()
