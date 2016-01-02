import threading

from django.core.management.commands.runserver import \
    Command as RunserverCommand

from channels import DEFAULT_CHANNEL_LAYER, channel_layers
from channels.handler import ViewConsumer
from channels.interfaces.wsgi import WSGIInterface
from channels.log import setup_logger
from channels.worker import Worker


class Command(RunserverCommand):

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        super(Command, self).handle(*args, **options)

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        return WSGIInterface(self.channel_layer)

    def run(self, *args, **options):
        # Run the rest
        return super(Command, self).run(*args, **options)

    def inner_run(self, *args, **options):
        # Check a handler is registered for http reqs
        self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        if not self.channel_layer.registry.consumer_for_channel("http.request"):
            # Register the default one
            self.channel_layer.registry.add_consumer(ViewConsumer(), ["http.request"])
        # Note that this is the right one on the console
        self.logger.info("Worker thread running, channels enabled")
        if self.channel_layer.local_only:
            self.logger.info("Local channel backend detected, no remote channels support")
        # Launch a worker thread
        worker = WorkerThread(self.channel_layer)
        worker.daemon = True
        worker.start()
        # Run rest of inner run
        super(Command, self).inner_run(*args, **options)


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def __init__(self, channel_layer):
        super(WorkerThread, self).__init__()
        self.channel_layer = channel_layer

    def run(self):
        Worker(channel_layer=self.channel_layer).run()
