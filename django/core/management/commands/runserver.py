from __future__ import unicode_literals

import errno
import logging
import os
import re
import socket
import sys
import threading
from datetime import datetime

from django.channels import DEFAULT_CHANNEL_LAYER, channel_layers
from django.channels.worker import Worker
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.asgi import ViewConsumer
from django.core.management.base import BaseCommand, CommandError
from django.core.servers.basehttp import get_internal_wsgi_application, run
from django.utils import autoreload, six
from django.utils.encoding import force_text, get_system_encoding


naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)


class Command(BaseCommand):
    help = "Starts a lightweight Web server for development."

    # Validation is called explicitly each time the server is reloaded.
    requires_system_checks = False
    leave_locale_alone = True

    default_port = '8000'

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?',
            help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
            help='Tells Django to use an IPv6 address.',
        )
        parser.add_argument(
            '--nothreading', action='store_false', dest='use_threading', default=True,
            help='Tells Django to NOT use threading.',
        )
        parser.add_argument(
            '--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.',
        )
        parser.add_argument(
            '--noworker', action='store_false', dest='run_worker', default=True,
            help='Tells Django not to run a worker thread; you\'ll need to run one separately.'
        )
        parser.add_argument(
            '--noasgi', action='store_false', dest='use_asgi', default=True,
            help='Run the old WSGI-based runserver rather than the ASGI-based one'
        )

    def execute(self, *args, **options):
        if options['no_color']:
            # We rely on the environment because it's currently the only
            # way to reach WSGIRequestHandler. This seems an acceptable
            # compromise considering `runserver` runs indefinitely.
            os.environ[str("DJANGO_COLORS")] = str("nocolor")
        super(Command, self).execute(*args, **options)

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        return get_internal_wsgi_application()

    def handle(self, *args, **options):
        from django.conf import settings

        if not settings.DEBUG and not settings.ALLOWED_HOSTS:
            raise CommandError('You must set settings.ALLOWED_HOSTS if DEBUG is False.')

        self.verbosity = options.get("verbosity", 1)

        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self._raw_ipv6 = False
        if not options['addrport']:
            self.addr = ''
            self.port = self.default_port
        else:
            m = re.match(naiveip_re, options['addrport'])
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % options['addrport'])
            self.addr, _ipv4, _ipv6, _fqdn, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." % self.port)
            if self.addr:
                if _ipv6:
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                    self._raw_ipv6 = True
                elif self.use_ipv6 and not _fqdn:
                    raise CommandError('"%s" is not a valid IPv6 address.' % self.addr)
        if not self.addr:
            self.addr = '::1' if self.use_ipv6 else '127.0.0.1'
            self._raw_ipv6 = self.use_ipv6
        self.run(**options)

    def run(self, **options):
        """
        Runs the server, using the autoreloader if needed
        """
        use_reloader = options['use_reloader']

        if use_reloader:
            autoreload.main(self.inner_run, None, options)
        else:
            self.inner_run(None, **options)

    def inner_run(self, *args, **options):
        # If an exception was silenced in ManagementUtility.execute in order
        # to be raised in the child process, raise it now.
        autoreload.raise_last_exception()

        # Work out if we should use ASGI or WSGI mode
        use_asgi = options.get("use_asgi", True)
        if DEFAULT_CHANNEL_LAYER not in channel_layers:
            use_asgi = False

        # Check a handler is registered for http reqs; if not, add default one
        if use_asgi:
            self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
            self.channel_layer.router.check_default(
                http_consumer=self.get_consumer(),
            )

        # 'shutdown_message' is a stealth option.
        self.shutdown_message = options.get('shutdown_message', '')
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        # Need to check migrations here, so can't use the
        # requires_migrations_check attribute.
        self.check_migrations()
        now = datetime.now().strftime('%B %d, %Y - %X')
        if six.PY2:
            now = now.decode(get_system_encoding())
        self.stdout.write(now)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server at http://%(addr)s:%(port)s/\n"
            "%(channel_message)s\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
            "channel_message": ("Channel layer %s\n" % self.channel_layer) if use_asgi else "",
        })
        if use_asgi:
            self.inner_run_asgi(*args, **options)
        else:
            self.inner_run_wsgi(*args, **options)

    def inner_run_wsgi(self, *args, **options):
        """
        Runs the runserver in WSGI mode
        """
        try:
            handler = self.get_handler(*args, **options)
            run(self.addr, int(self.port), handler,
                ipv6=self.use_ipv6, threading=options.get('use_threading'))
        except socket.error as e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned to.",
            }
            try:
                error_text = ERRORS[e.errno]
            except KeyError:
                error_text = force_text(e)
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if self.shutdown_message:
                self.stdout.write(self.shutdown_message)
            sys.exit(0)

    def inner_run_asgi(self, *args, **options):
        """
        Runs the runserver in ASGI mode, using Daphne
        """
        # Set up logger for sub-stuff
        self.logger = logging.getLogger("django.channels")
        handler = logging.StreamHandler()
        self.logger.addHandler(handler)
        self.logger.propagate = False
        if self.verbosity > 1:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        # Launch workers as subthreads
        if options.get("run_worker", True):
            for _ in range(4):
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
                signal_handlers=not options['use_reloader'],
                action_logger=self.log_action,
                http_timeout=60,  # Shorter timeout than normal as it's dev
            ).run()
            self.logger.debug("Daphne exited")
        except KeyboardInterrupt:
            if self.shutdown_message:
                self.stdout.write(self.shutdown_message)
            return

    def check_migrations(self):
        """
        Checks to see if the set of migrations on disk matches the
        migrations in the database. Prints a warning if they don't match.
        """
        try:
            executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        except ImproperlyConfigured:
            # No databases are configured (or the dummy one)
            return
        except MigrationSchemaMissing:
            self.stdout.write(self.style.NOTICE(
                "\nNot checking migrations as it is not possible to access/create the django_migrations table."
            ))
            return

        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            self.stdout.write(self.style.NOTICE(
                "\nYou have unapplied migrations; your app may not work properly until they are applied."
            ))
            self.stdout.write(self.style.NOTICE("Run 'python manage.py migrate' to apply them.\n"))

    def log_action(self, protocol, action, details):
        """
        Logs various different kinds of requests to the console.
        """
        # All start with timestamp
        msg = "[%s] " % datetime.now().strftime("%Y/%m/%d %H:%M:%S")
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
        sys.stderr.write(msg)

    def get_consumer(self, *args, **options):
        """
        Returns the consumer to use for HTTP requests
        """
        return ViewConsumer()


class WorkerThread(threading.Thread):
    """
    Class that runs an ASGI worker
    """

    def __init__(self, channel_layer, logger):
        super(WorkerThread, self).__init__()
        self.channel_layer = channel_layer
        self.logger = logger

    def run(self):
        self.logger.debug("Worker thread running")
        worker = Worker(channel_layer=self.channel_layer, signal_handlers=False)
        worker.run()
        self.logger.debug("Worker thread exited")
