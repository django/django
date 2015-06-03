import django
import threading
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.handlers.wsgi import WSGIHandler
from channel import Channel, coreg
from channel.request import encode_request
from channel.response import decode_response
from channel.worker import Worker
from channel.utils import auto_import_consumers


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
            raise RuntimeError("No consumer registered for WSGI requests")
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
        response_channel = Channel.new_name("django.wsgi.response")
        Channel("django.wsgi.request").send(
            request = encode_request(request),
            response_channel = response_channel,
        )
        channel, message = Channel.receive_many([response_channel])
        return decode_response(message)


class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def run(self):
        Worker(
            consumer_registry = coreg,
            channel_class = Channel,
        ).run()
