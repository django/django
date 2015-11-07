from django.core.management import BaseCommand, CommandError

from channels import channel_backends, DEFAULT_CHANNEL_BACKEND
from channels.log import setup_logger


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('port', nargs='?',
            help='Optional port number')

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        # Get the backend to use
        channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        if channel_backend.local_only:
            raise CommandError(
                "You have a process-local channel backend configured, and so cannot run separate interface servers.\n"
                "Configure a network-based backend in CHANNEL_BACKENDS to use this command."
            )
        # Run the interface
        port = int(options.get("port", None) or 9000)
        try:
            import asyncio
        except ImportError:
            from channels.interfaces.websocket_twisted import WebsocketTwistedInterface
            self.logger.info("Running Twisted/Autobahn WebSocket interface server")
            self.logger.info(" Channel backend: %s", channel_backend)
            self.logger.info(" Listening on: ws://0.0.0.0:%i" % port)
            WebsocketTwistedInterface(channel_backend=channel_backend, port=port).run()
        else:
            from channels.interfaces.websocket_asyncio import WebsocketAsyncioInterface
            self.logger.info("Running asyncio/Autobahn WebSocket interface server")
            self.logger.info(" Channel backend: %s", channel_backend)
            self.logger.info(" Listening on: ws://0.0.0.0:%i", port)
            WebsocketAsyncioInterface(channel_backend=channel_backend, port=port).run()
