import datetime
import sys
import threading

from daphne.server import Server, build_endpoint_description_strings
from django.apps import apps
from django.conf import settings
from django.core.management.commands.runserver import Command as RunserverCommand
from django.utils import six
from django.utils.encoding import get_system_encoding

from channels import DEFAULT_CHANNEL_LAYER, channel_layers
from channels.handler import ViewConsumer
from channels.log import setup_logger
from channels.staticfiles import StaticFilesConsumer
from channels.worker import Worker


class Command(RunserverCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--noworker', action='store_false', dest='run_worker', default=True,
            help='Tells Django not to run a worker thread; you\'ll need to run one separately.')
        parser.add_argument('--noasgi', action='store_false', dest='use_asgi', default=True,
            help='Run the old WSGI-based runserver rather than the ASGI-based one')
        parser.add_argument('--http_timeout', action='store', dest='http_timeout', type=int, default=60,
            help='Specify the daphne http_timeout interval in seconds (default: 60)')
        parser.add_argument('--websocket_handshake_timeout', action='store', dest='websocket_handshake_timeout',
            type=int, default=5,
            help='Specify the daphne websocket_handshake_timeout interval in seconds (default: 5)')

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        self.logger = setup_logger('django.channels', self.verbosity)
        self.http_timeout = options.get("http_timeout", 60)
        self.websocket_handshake_timeout = options.get("websocket_handshake_timeout", 5)
        super(Command, self).handle(*args, **options)

    def inner_run(self, *args, **options):
        # Maybe they want the wsgi one?
        if not options.get("use_asgi", True) or DEFAULT_CHANNEL_LAYER not in channel_layers:
            return RunserverCommand.inner_run(self, *args, **options)
        # Check a handler is registered for http reqs; if not, add default one
        self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        self.channel_layer.router.check_default(
            http_consumer=self.get_consumer(*args, **options),
        )
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
            "Channel layer %(layer)s\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
            "layer": self.channel_layer,
        })

        # Launch workers as subthreads
        if options.get("run_worker", True):
            worker_count = 4 if options.get("use_threading", True) else 1
            for _ in range(worker_count):
                worker = WorkerThread(self.channel_layer, self.logger)
                worker.daemon = True
                worker.start()
        # Launch server in 'main' thread. Signals are disabled as it's still
        # actually a subthread under the autoreloader.
        self.logger.debug("Daphne running, listening on %s:%s", self.addr, self.port)

        # build the endpoint description string from host/port options
        endpoints = build_endpoint_description_strings(host=self.addr, port=self.port)
        try:
            Server(
                channel_layer=self.channel_layer,
                endpoints=endpoints,
                signal_handlers=not options['use_reloader'],
                action_logger=self.log_action,
                http_timeout=self.http_timeout,
                ws_protocols=getattr(settings, 'CHANNELS_WS_PROTOCOLS', None),
                root_path=getattr(settings, 'FORCE_SCRIPT_NAME', '') or '',
                websocket_handshake_timeout=self.websocket_handshake_timeout,
            ).run()
            self.logger.debug("Daphne exited")
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
            msg += "HTTP %(method)s %(path)s %(status)s [%(time_taken).2f, %(client)s]\n" % details
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
        elif protocol == "websocket" and action == "connecting":
            msg += "WebSocket HANDSHAKING %(path)s [%(client)s]\n" % details
        elif protocol == "websocket" and action == "rejected":
            msg += "WebSocket REJECT %(path)s [%(client)s]\n" % details

        sys.stderr.write(msg)

    def get_consumer(self, *args, **options):
        """
        Returns the static files serving handler wrapping the default handler,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        staticfiles_installed = apps.is_installed("django.contrib.staticfiles")
        use_static_handler = options.get('use_static_handler', staticfiles_installed)
        insecure_serving = options.get('insecure_serving', False)
        if use_static_handler and (settings.DEBUG or insecure_serving):
            return StaticFilesConsumer()
        else:
            return ViewConsumer()


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
        worker = Worker(channel_layer=self.channel_layer, signal_handlers=False)
        worker.ready()
        worker.run()
        self.logger.debug("Worker thread exited")
