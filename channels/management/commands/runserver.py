import datetime
import logging
import sys

from django.apps import apps
from django.conf import settings
from django.core.management import CommandError
from django.core.management.commands.runserver import Command as RunserverCommand

from channels import __version__
from channels.routing import get_default_application
from daphne.endpoints import build_endpoint_description_strings
from daphne.server import Server

from ...staticfiles import StaticFilesWrapper

logger = logging.getLogger("django.channels.server")


class Command(RunserverCommand):
    protocol = "http"
    server_cls = Server

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--noasgi",
            action="store_false",
            dest="use_asgi",
            default=True,
            help="Run the old WSGI-based runserver rather than the ASGI-based one",
        )
        parser.add_argument(
            "--http_timeout",
            action="store",
            dest="http_timeout",
            type=int,
            default=None,
            help="Specify the daphne http_timeout interval in seconds (default: no timeout)",
        )
        parser.add_argument(
            "--websocket_handshake_timeout",
            action="store",
            dest="websocket_handshake_timeout",
            type=int,
            default=5,
            help="Specify the daphne websocket_handshake_timeout interval in seconds (default: 5)",
        )

    def handle(self, *args, **options):
        self.http_timeout = options.get("http_timeout", None)
        self.websocket_handshake_timeout = options.get("websocket_handshake_timeout", 5)
        # Check Channels is installed right
        if options["use_asgi"] and not hasattr(settings, "ASGI_APPLICATION"):
            raise CommandError(
                "You have not set ASGI_APPLICATION, which is needed to run the server."
            )
        # Dispatch upward
        super().handle(*args, **options)

    def inner_run(self, *args, **options):
        # Maybe they want the wsgi one?
        if not options.get("use_asgi", True):
            if hasattr(RunserverCommand, "server_cls"):
                self.server_cls = RunserverCommand.server_cls
            return RunserverCommand.inner_run(self, *args, **options)
        # Run checks
        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        self.check_migrations()
        # Print helpful text
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        now = datetime.datetime.now().strftime("%B %d, %Y - %X")
        self.stdout.write(now)
        self.stdout.write(
            (
                "Django version %(version)s, using settings %(settings)r\n"
                "Starting ASGI/Channels version %(channels_version)s development server"
                " at %(protocol)s://%(addr)s:%(port)s/\n"
                "Quit the server with %(quit_command)s.\n"
            )
            % {
                "version": self.get_version(),
                "channels_version": __version__,
                "settings": settings.SETTINGS_MODULE,
                "protocol": self.protocol,
                "addr": "[%s]" % self.addr if self._raw_ipv6 else self.addr,
                "port": self.port,
                "quit_command": quit_command,
            }
        )

        # Launch server in 'main' thread. Signals are disabled as it's still
        # actually a subthread under the autoreloader.
        logger.debug("Daphne running, listening on %s:%s", self.addr, self.port)

        # build the endpoint description string from host/port options
        endpoints = build_endpoint_description_strings(host=self.addr, port=self.port)
        try:
            self.server_cls(
                application=self.get_application(options),
                endpoints=endpoints,
                signal_handlers=not options["use_reloader"],
                action_logger=self.log_action,
                http_timeout=self.http_timeout,
                root_path=getattr(settings, "FORCE_SCRIPT_NAME", "") or "",
                websocket_handshake_timeout=self.websocket_handshake_timeout,
            ).run()
            logger.debug("Daphne exited")
        except KeyboardInterrupt:
            shutdown_message = options.get("shutdown_message", "")
            if shutdown_message:
                self.stdout.write(shutdown_message)
            return

    def get_application(self, options):
        """
        Returns the static files serving application wrapping the default application,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        staticfiles_installed = apps.is_installed("django.contrib.staticfiles")
        use_static_handler = options.get("use_static_handler", staticfiles_installed)
        insecure_serving = options.get("insecure_serving", False)
        if use_static_handler and (settings.DEBUG or insecure_serving):
            return StaticFilesWrapper(get_default_application())
        else:
            return get_default_application()

    def log_action(self, protocol, action, details):
        """
        Logs various different kinds of requests to the console.
        """
        # HTTP requests
        if protocol == "http" and action == "complete":
            msg = "HTTP %(method)s %(path)s %(status)s [%(time_taken).2f, %(client)s]"

            # Utilize terminal colors, if available
            if 200 <= details["status"] < 300:
                # Put 2XX first, since it should be the common case
                logger.info(self.style.HTTP_SUCCESS(msg), details)
            elif 100 <= details["status"] < 200:
                logger.info(self.style.HTTP_INFO(msg), details)
            elif details["status"] == 304:
                logger.info(self.style.HTTP_NOT_MODIFIED(msg), details)
            elif 300 <= details["status"] < 400:
                logger.info(self.style.HTTP_REDIRECT(msg), details)
            elif details["status"] == 404:
                logger.warn(self.style.HTTP_NOT_FOUND(msg), details)
            elif 400 <= details["status"] < 500:
                logger.warn(self.style.HTTP_BAD_REQUEST(msg), details)
            else:
                # Any 5XX, or any other response
                logger.error(self.style.HTTP_SERVER_ERROR(msg), details)

        # Websocket requests
        elif protocol == "websocket" and action == "connected":
            logger.info("WebSocket CONNECT %(path)s [%(client)s]", details)
        elif protocol == "websocket" and action == "disconnected":
            logger.info("WebSocket DISCONNECT %(path)s [%(client)s]", details)
        elif protocol == "websocket" and action == "connecting":
            logger.info("WebSocket HANDSHAKING %(path)s [%(client)s]", details)
        elif protocol == "websocket" and action == "rejected":
            logger.info("WebSocket REJECT %(path)s [%(client)s]", details)
