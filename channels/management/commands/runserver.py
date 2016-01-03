import threading

from django.core.management.commands.runserver import \
    Command as RunserverCommand

from channels import DEFAULT_CHANNEL_LAYER, channel_layers
from channels.handler import ViewConsumer
from channels.log import setup_logger
from channels.worker import Worker


class Command(RunserverCommand):

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        super(Command, self).handle(*args, **options)

    def run(self, *args, **options):
        # Don't autoreload for now
        self.inner_run(None, **options)

    def inner_run(self, *args, **options):
        # Check a handler is registered for http reqs; if not, add default one
        self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        if not self.channel_layer.registry.consumer_for_channel("http.request"):
            self.channel_layer.registry.add_consumer(ViewConsumer(), ["http.request"])
        # Note that this is the channel-enabled one on the console
        self.logger.info("Worker thread running, channels enabled")
        # Launch a worker thread
        worker = WorkerThread(self.channel_layer)
        worker.daemon = True
        worker.start()
        # Launch server in main thread
        from daphne.server import Server
        Server(
            channel_layer=self.channel_layer,
            host=self.addr,
            port=int(self.port),
        ).run()


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def __init__(self, channel_layer):
        super(WorkerThread, self).__init__()
        self.channel_layer = channel_layer

    def run(self):
        Worker(channel_layer=self.channel_layer).run()
