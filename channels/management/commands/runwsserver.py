import time
from django.core.management import BaseCommand, CommandError
from channels import channel_backends, DEFAULT_CHANNEL_BACKEND
from channels.interfaces.websocket_twisted import WebsocketTwistedInterface
from channels.utils import auto_import_consumers


class Command(BaseCommand):

    def handle(self, *args, **options):
        # Get the backend to use
        channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        auto_import_consumers()
        if channel_backend.local_only:
            raise CommandError(
                "You have a process-local channel backend configured, and so cannot run separate interface servers.\n"
                "Configure a network-based backend in CHANNEL_BACKENDS to use this command."
            )
        # Launch a worker
        self.stdout.write("Running Twisted/Autobahn WebSocket interface against backend %s" % channel_backend)
        # Run the interface
        try:
            WebsocketTwistedInterface(channel_backend=channel_backend).run()
        except KeyboardInterrupt:
            pass
