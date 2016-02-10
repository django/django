import datetime
import sys
import threading

from django.conf import settings
from django.core.management.commands.runserver import \
    Command as RunserverCommand
from django.utils import six
from django.utils.encoding import get_system_encoding

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
        # Run checks
        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        self.check_migrations()
        # Print helpful text
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'
        now = datetime.datetime.now().strftime('%B %d, %Y - %X')
        if six.PY2:
            now = now.decode(get_system_encoding())
        self.stdout.write(now)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting Channels development server at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })

        # Launch worker as subthread
        worker = WorkerThread(self.channel_layer, self.logger)
        worker.daemon = True
        worker.start()
        # Launch server in 'main' thread. Signals are disabled as it's still
        # actually a subthread under the autoreloader.
        self.logger.debug("Daphne running, listening on %s:%s", self.addr, self.port)
        try:
            from daphne.server import Server
            Server(
                channel_layer=self.channel_layer,
                host=self.addr,
                port=int(self.port),
                signal_handlers=False,
                action_logger=self.log_action,
            ).run()
        except KeyboardInterrupt:
            shutdown_message = options.get('shutdown_message', '')
            if shutdown_message:
                self.stdout.write(shutdown_message)
            return

    def log_action(self, protocol, action, details):
        """
        Logs various different kinds of requests to the console.
        """
        # All start with timestamp
        msg = "[%s] " % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        # HTTP requests
        if protocol == "http" and action == "complete":
            msg += "HTTP %(method)s %(path)s %(status)s [%(client)s]\n" % details
            # Utilize terminal colors, if available
            if 200 <= details['status'] < 300:
                # Put 2XX first, since it should be the common case
                msg = self.style.HTTP_SUCCESS(msg)
            elif 100 <= details['status'] < 200:
                msg = self.style.HTTP_INFO(msg)
            elif details['status'] == 304:
                msg = self.style.HTTP_NOT_MODIFIED(msg)
            elif 300 <= details['status'] < 400:
                msg = self.style.HTTP_REDIRECT(msg)
            elif details['status'] == 404:
                msg = self.style.HTTP_NOT_FOUND(msg)
            elif 400 <= details['status'] < 500:
                msg = self.style.HTTP_BAD_REQUEST(msg)
            else:
                # Any 5XX, or any other response
                msg = self.style.HTTP_SERVER_ERROR(msg)
        # Websocket requests
        elif protocol == "websocket" and action == "connected":
            msg += "WebSocket CONNECT %(path)s [%(client)s]\n" % details
        elif protocol == "websocket" and action == "disconnected":
            msg += "WebSocket DISCONNECT %(path)s [%(client)s]\n" % details


        sys.stderr.write(msg)

class WorkerThread(threading.Thread):
    """
    Class that runs a worker
    """

    def __init__(self, channel_layer, logger):
        super(WorkerThread, self).__init__()
        self.channel_layer = channel_layer
        self.logger = logger

    def run(self):
        self.logger.debug("Worker thread running")
        worker = Worker(channel_layer=self.channel_layer)
        worker.run()
