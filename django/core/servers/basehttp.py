"""
HTTP server that implements the Python WSGI protocol (PEP 333, rev 1.21).

Based on wsgiref.simple_server which is part of the standard library since 2.5.

This is a simple server for use in testing or debugging Django apps. It hasn't
been reviewed for security issues. DON'T USE IT FOR PRODUCTION USE!
"""

from __future__ import unicode_literals

import socket
import sys
from wsgiref import simple_server
from wsgiref.util import FileWrapper  # NOQA: for backwards compatibility

from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import ISO_8859_1, UTF_8
from django.core.management.color import color_style
from django.core.wsgi import get_wsgi_application
from django.utils import six
from django.utils.encoding import uri_to_iri
from django.utils.module_loading import import_string
from django.utils.six.moves import socketserver

__all__ = ('WSGIServer', 'WSGIRequestHandler')


def get_internal_wsgi_application():
    """
    Loads and returns the WSGI application as configured by the user in
    ``settings.WSGI_APPLICATION``. With the default ``startproject`` layout,
    this will be the ``application`` object in ``projectname/wsgi.py``.

    This function, and the ``WSGI_APPLICATION`` setting itself, are only useful
    for Django's internal servers (runserver, runfcgi); external WSGI servers
    should just be configured to point to the correct application object
    directly.

    If settings.WSGI_APPLICATION is not set (is ``None``), we just return
    whatever ``django.core.wsgi.get_wsgi_application`` returns.

    """
    from django.conf import settings
    app_path = getattr(settings, 'WSGI_APPLICATION')
    if app_path is None:
        return get_wsgi_application()

    try:
        return import_string(app_path)
    except ImportError as e:
        msg = (
            "WSGI application '%(app_path)s' could not be loaded; "
            "Error importing module: '%(exception)s'" % ({
                'app_path': app_path,
                'exception': e,
            })
        )
        six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                    sys.exc_info()[2])


def is_broken_pipe_error():
    exc_type, exc_value = sys.exc_info()[:2]
    return issubclass(exc_type, socket.error) and exc_value.args[0] == 32


class WSGIServer(simple_server.WSGIServer, object):
    """BaseHTTPServer that implements the Python WSGI protocol"""

    request_queue_size = 10

    def __init__(self, *args, **kwargs):
        if kwargs.pop('ipv6', False):
            self.address_family = socket.AF_INET6
        super(WSGIServer, self).__init__(*args, **kwargs)

    def server_bind(self):
        """Override server_bind to store the server name."""
        super(WSGIServer, self).server_bind()
        self.setup_environ()

    def handle_error(self, request, client_address):
        if is_broken_pipe_error():
            sys.stderr.write("- Broken pipe from %s\n" % (client_address,))
        else:
            super(WSGIServer, self).handle_error(request, client_address)


# Inheriting from object required on Python 2.
class ServerHandler(simple_server.ServerHandler, object):
    def handle_error(self):
        # Ignore broken pipe errors, otherwise pass on
        if not is_broken_pipe_error():
            super(ServerHandler, self).handle_error()


class WSGIRequestHandler(simple_server.WSGIRequestHandler, object):

    def __init__(self, *args, **kwargs):
        self.style = color_style()
        super(WSGIRequestHandler, self).__init__(*args, **kwargs)

    def address_string(self):
        # Short-circuit parent method to not call socket.getfqdn
        return self.client_address[0]

    def log_message(self, format, *args):

        msg = "[%s] " % self.log_date_time_string()
        try:
            msg += "%s\n" % (format % args)
        except UnicodeDecodeError:
            # e.g. accessing the server via SSL on Python 2
            msg += "\n"

        # Utilize terminal colors, if available
        if args[1][0] == '2':
            # Put 2XX first, since it should be the common case
            msg = self.style.HTTP_SUCCESS(msg)
        elif args[1][0] == '1':
            msg = self.style.HTTP_INFO(msg)
        elif args[1] == '304':
            msg = self.style.HTTP_NOT_MODIFIED(msg)
        elif args[1][0] == '3':
            msg = self.style.HTTP_REDIRECT(msg)
        elif args[1] == '404':
            msg = self.style.HTTP_NOT_FOUND(msg)
        elif args[1][0] == '4':
            # 0x16 = Handshake, 0x03 = SSL 3.0 or TLS 1.x
            if args[0].startswith(str('\x16\x03')):
                msg = ("You're accessing the development server over HTTPS, "
                    "but it only supports HTTP.\n")
            msg = self.style.HTTP_BAD_REQUEST(msg)
        else:
            # Any 5XX, or any other response
            msg = self.style.HTTP_SERVER_ERROR(msg)

        sys.stderr.write(msg)

    def get_environ(self):
        # Strip all headers with underscores in the name before constructing
        # the WSGI environ. This prevents header-spoofing based on ambiguity
        # between underscores and dashes both normalized to underscores in WSGI
        # env vars. Nginx and Apache 2.4+ both do this as well.
        for k, v in self.headers.items():
            if '_' in k:
                del self.headers[k]

        env = super(WSGIRequestHandler, self).get_environ()

        path = self.path
        if '?' in path:
            path = path.partition('?')[0]

        path = uri_to_iri(path).encode(UTF_8)
        # Under Python 3, non-ASCII values in the WSGI environ are arbitrarily
        # decoded with ISO-8859-1. We replicate this behavior here.
        # Refs comment in `get_bytes_from_wsgi()`.
        env['PATH_INFO'] = path.decode(ISO_8859_1) if six.PY3 else path

        return env

    def handle(self):
        """Copy of WSGIRequestHandler, but with different ServerHandler"""

        self.raw_requestline = self.rfile.readline(65537)
        if len(self.raw_requestline) > 65536:
            self.requestline = ''
            self.request_version = ''
            self.command = ''
            self.send_error(414)
            return

        if not self.parse_request():  # An error code has been sent, just exit
            return

        handler = ServerHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ()
        )
        handler.request_handler = self      # backpointer for logging
        handler.run(self.server.get_app())


def run(addr, port, wsgi_handler, ipv6=False, threading=False):
    server_address = (addr, port)
    if threading:
        httpd_cls = type(str('WSGIServer'), (socketserver.ThreadingMixIn, WSGIServer), {})
    else:
        httpd_cls = WSGIServer
    httpd = httpd_cls(server_address, WSGIRequestHandler, ipv6=ipv6)
    if threading:
        # ThreadingMixIn.daemon_threads indicates how threads will behave on an
        # abrupt shutdown; like quitting the server by the user or restarting
        # by the auto-reloader. True means the server will not wait for thread
        # termination before it quits. This will make auto-reloader faster
        # and will prevent the need to kill the server manually if a thread
        # isn't terminating correctly.
        httpd.daemon_threads = True
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()
