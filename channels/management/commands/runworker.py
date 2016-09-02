from __future__ import unicode_literals

from django.conf import settings
from django.core.management import BaseCommand, CommandError

from channels import DEFAULT_CHANNEL_LAYER, channel_layers
from channels.log import setup_logger
from channels.staticfiles import StaticFilesConsumer
from channels.worker import Worker, WorkerGroup
from channels.signals import worker_process_ready


class Command(BaseCommand):

    leave_locale_alone = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--layer', action='store', dest='layer', default=DEFAULT_CHANNEL_LAYER,
            help='Channel layer alias to use, if not the default.',
        )
        parser.add_argument(
            '--only-channels', action='append', dest='only_channels',
            help='Limits this worker to only listening on the provided channels (supports globbing).',
        )
        parser.add_argument(
            '--exclude-channels', action='append', dest='exclude_channels',
            help='Prevents this worker from listening on the provided channels (supports globbing).',
        )
        parser.add_argument(
            '--threads', action='store', dest='threads',
            default=1, type=int,
            help='Number of threads to execute.'
        )

    def handle(self, *args, **options):
        # Get the backend to use
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        self.channel_layer = channel_layers[options.get("layer", DEFAULT_CHANNEL_LAYER)]
        self.n_threads = options.get('threads', 1)
        # Check that handler isn't inmemory
        if self.channel_layer.local_only():
            raise CommandError(
                "You cannot span multiple processes with the in-memory layer. " +
                "Change your settings to use a cross-process channel layer."
            )
        # Check a handler is registered for http reqs
        # Serve static files if Django in debug mode
        if settings.DEBUG:
            self.channel_layer.router.check_default(http_consumer=StaticFilesConsumer())
        else:
            self.channel_layer.router.check_default()
        # Optionally provide an output callback
        callback = None
        if self.verbosity > 1:
            callback = self.consumer_called
        self.callback = callback
        self.options = options
        # Choose an appropriate worker.
        worker_kwargs = {}
        if self.n_threads == 1:
            self.logger.info("Using single-threaded worker.")
            worker_cls = Worker
        else:
            self.logger.info("Using multi-threaded worker, {} thread(s).".format(self.n_threads))
            worker_cls = WorkerGroup
            worker_kwargs['n_threads'] = self.n_threads
        # Run the worker
        self.logger.info("Running worker against channel layer %s", self.channel_layer)
        try:
            worker = worker_cls(
                channel_layer=self.channel_layer,
                callback=self.callback,
                only_channels=self.options.get("only_channels", None),
                exclude_channels=self.options.get("exclude_channels", None),
                **worker_kwargs
            )
            worker_process_ready.send(sender=worker)
            worker.ready()
            worker.run()
        except KeyboardInterrupt:
            pass

    def consumer_called(self, channel, message):
        self.logger.debug("%s", channel)
