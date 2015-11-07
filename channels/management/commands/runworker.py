
from django.core.management import BaseCommand, CommandError

from channels import DEFAULT_CHANNEL_BACKEND, channel_backends
from channels.log import setup_logger
from channels.worker import Worker


class Command(BaseCommand):

    def handle(self, *args, **options):
        # Get the backend to use
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        if channel_backend.local_only:
            raise CommandError(
                "You have a process-local channel backend configured, and so cannot run separate workers.\n"
                "Configure a network-based backend in CHANNEL_BACKENDS to use this command."
            )
        # Launch a worker
        self.logger.info("Running worker against backend %s", channel_backend)
        # Optionally provide an output callback
        callback = None
        if self.verbosity > 1:
            callback = self.consumer_called
        # Run the worker
        try:
            Worker(channel_backend=channel_backend, callback=callback).run()
        except KeyboardInterrupt:
            pass

    def consumer_called(self, channel, message):
        self.logger.debug("%s", channel)
