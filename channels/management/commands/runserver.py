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

    def inner_run(self, *args, **options):
        # Check a handler is registered for http reqs; if not, add default one
        self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        if not self.channel_layer.registry.consumer_for_channel("http.request"):
            self.channel_layer.registry.add_consumer(ViewConsumer(), ["http.request"])
        # Report starting up
        # Launch worker as subthread (including autoreload logic)
        worker = WorkerThread(self.channel_layer, self.logger)
        worker.daemon = True
        worker.start()
        # Launch server in main thread (Twisted doesn't like being in a
        # subthread, and it doesn't need to autoreload as there's no user code)
        self.logger.info("Daphne running, listening on %s:%s", self.addr, self.port)
        from daphne.server import Server
        Server(
            channel_layer=self.channel_layer,
            host=self.addr,
            port=int(self.port),
            signal_handlers=False,
        ).run()


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def __init__(self, channel_layer, logger):
        super(WorkerThread, self).__init__()
        self.channel_layer = channel_layer
        self.logger = logger

    def run(self):
        self.logger.info("Worker thread running")
        worker = Worker(channel_layer=self.channel_layer)
        worker.run()
