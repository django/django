"""
HTTP server that implements the Python WSGI protocol (PEP 333, rev 1.21).

Based on wsgiref.simple_server which is part of the standard library since 2.5.

This is a simple server for use in testing or debugging Django apps. It hasn't
been reviewed for security issues. DON'T USE IT FOR PRODUCTION USE!
"""

from __future__ import unicode_literals

from io import BytesIO
import socket
import sys
import traceback
try:
    from urllib.parse import urljoin
except ImportError:     # Python 2
    from urlparse import urljoin
from django.utils.six.moves import socketserver
from wsgiref import simple_server
from wsgiref.util import FileWrapper   # for backwards compatibility

from django.core.management.color import color_style
from django.core.wsgi import get_wsgi_application
from django.utils.module_loading import import_by_path
from django.utils import six

__all__ = ('WSGIServer', 'WSGIRequestHandler', 'MAX_SOCKET_CHUNK_SIZE')


# If data is too large, socket will choke, so write chunks no larger than 32MB
# at a time. The rationale behind the 32MB can be found on Django's Trac:
# https://code.djangoproject.com/ticket/5596#comment:4
MAX_SOCKET_CHUNK_SIZE = 32 * 1024 * 1024  # 32 MB


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

    return import_by_path(
        app_path,
        error_prefix="WSGI application '%s' could not be loaded; " % app_path
    )


class WSGIServerException(Exception):
    pass


class ServerHandler(simple_server.ServerHandler, object):
    error_status = str("500 INTERNAL SERVER ERROR")

    def write(self, data):
        """'write()' callable as specified by PEP 3333"""

        assert isinstance(data, bytes), "write() argument must be bytestring"

        if not self.status:
            raise AssertionError("write() before start_response()")

        elif not self.headers_sent:
            # Before the first output, send the stored headers
            self.bytes_sent = len(data)    # make sure we know content-length
            self.send_headers()
        else:
            self.bytes_sent += len(data)

        # XXX check Content-Length and truncate if too many bytes written?
        data = BytesIO(data)
        for chunk in iter(lambda: data.read(MAX_SOCKET_CHUNK_SIZE), b''):
            self._write(chunk)
            self._flush()

    def error_output(self, environ, start_response):
        super(ServerHandler, self).error_output(environ, start_response)
        return ['\n'.join(traceback.format_exception(*sys.exc_info()))]

    # Backport of http://hg.python.org/cpython/rev/d5af1b235dab. See #16241.
    # This can be removed when support for Python <= 2.7.3 is deprecated.
    def finish_response(self):
        try:
            if not self.result_is_file() or not self.sendfile():
                for data in self.result:
                    self.write(data)
                self.finish_content()
        finally:
            self.close()


class WSGIServer(simple_server.WSGIServer, object):
    """BaseHTTPServer that implements the Python WSGI protocol"""

    request_queue_size = 10

    def __init__(self, *args, **kwargs):
        if kwargs.pop('ipv6', False):
            self.address_family = socket.AF_INET6
        super(WSGIServer, self).__init__(*args, **kwargs)

    def server_bind(self):
        """Override server_bind to store the server name."""
        try:
            super(WSGIServer, self).server_bind()
        except Exception as e:
            six.reraise(WSGIServerException, WSGIServerException(e), sys.exc_info()[2])
        self.setup_environ()


class WSGIRequestHandler(simple_server.WSGIRequestHandler, object):

    def __init__(self, *args, **kwargs):
        from django.conf import settings
        self.admin_static_prefix = urljoin(settings.STATIC_URL, 'admin/')
        # We set self.path to avoid crashes in log_message() on unsupported
        # requests (like "OPTIONS").
        self.path = ''
        self.style = color_style()
        super(WSGIRequestHandler, self).__init__(*args, **kwargs)

    def address_string(self):
        # Short-circuit parent method to not call socket.getfqdn
        return self.client_address[0]

    def log_message(self, format, *args):
        # Don't bother logging requests for admin images or the favicon.
        if (self.path.startswith(self.admin_static_prefix)
                or self.path == '/favicon.ico'):
            return

        msg = "[%s] %s\n" % (self.log_date_time_string(), format % args)

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
            msg = self.style.HTTP_BAD_REQUEST(msg)
        else:
            # Any 5XX, or any other response
            msg = self.style.HTTP_SERVER_ERROR(msg)

        sys.stderr.write(msg)


def run(addr, port, wsgi_handler, ipv6=False, threading=False):
    server_address = (addr, port)
    if threading:
        httpd_cls = type(str('WSGIServer'), (socketserver.ThreadingMixIn, WSGIServer), {})
    else:
        httpd_cls = WSGIServer
    httpd = httpd_cls(server_address, WSGIRequestHandler, ipv6=ipv6)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()
