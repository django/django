import django
import threading
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.handlers.wsgi import WSGIHandler
from django.http import HttpResponse
from channels import Channel, coreg
from channels.worker import Worker
from channels.utils import auto_import_consumers
from channels.adapters import UrlConsumer


class Command(RunserverCommand):

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        django.setup()
        return WSGIInterfaceHandler()

    def run(self, *args, **options):
        # Force disable reloader for now
        options['use_reloader'] = False
        # Check a handler is registered for http reqs
        auto_import_consumers()
        if not coreg.consumer_for_channel("django.wsgi.request"):
            # Register the default one
            coreg.add_consumer(UrlConsumer(), ["django.wsgi.request"])
        # Launch a worker thread
        worker = WorkerThread()
        worker.daemon = True
        worker.start()
        # Run the rest
        return super(Command, self).run(*args, **options)


class WSGIInterfaceHandler(WSGIHandler):
    """
    New WSGI handler that pushes requests to channels.
    """

    def get_response(self, request):
        request.response_channel = Channel.new_name("django.wsgi.response")
        Channel("django.wsgi.request").send(**request.channel_encode())
        channel, message = Channel.receive_many([request.response_channel])
        return HttpResponse.channel_decode(message)


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def run(self):
        Worker(
            consumer_registry = coreg,
            channel_class = Channel,
        ).run()
