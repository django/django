import django
import threading
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.management import CommandError
from channels import channel_backends, DEFAULT_CHANNEL_BACKEND
from channels.worker import Worker
from channels.utils import auto_import_consumers
from channels.adapters import UrlConsumer
from channels.interfaces.wsgi import WSGIInterface


class Command(RunserverCommand):

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        return WSGIInterface(self.channel_backend)

    def run(self, *args, **options):
        # Force disable reloader for now
        options['use_reloader'] = False
        # Check a handler is registered for http reqs
        self.channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        auto_import_consumers()
        if not self.channel_backend.registry.consumer_for_channel("django.wsgi.request"):
            # Register the default one
            self.channel_backend.registry.add_consumer(UrlConsumer(), ["django.wsgi.request"])
        # Launch a worker thread
        worker = WorkerThread(self.channel_backend)
        worker.daemon = True
        worker.start()
        # Run the rest
        return super(Command, self).run(*args, **options)


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def __init__(self, channel_backend):
        super(WorkerThread, self).__init__()
        self.channel_backend = channel_backend

    def run(self):
        Worker(channel_backend=self.channel_backend).run()
