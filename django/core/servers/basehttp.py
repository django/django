"""
HTTP server that implements the Python WSGI protocol (PEP 333, rev 1.21).

Based on wsgiref.simple_server which is part of the standard library since 2.5.

This is a simple server for use in testing or debugging Django apps. It hasn't
been reviewed for security issues. DON'T USE IT FOR PRODUCTION USE!
"""

import os
import socket
import sys
import traceback
import urllib
import urlparse
from SocketServer import ThreadingMixIn
from wsgiref import simple_server
from wsgiref.util import FileWrapper   # for backwards compatibility

import django
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style
from django.core.wsgi import get_wsgi_application
from django.utils.importlib import import_module

__all__ = ['WSGIServer', 'WSGIRequestHandler']


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
    module_name, attr = app_path.rsplit('.', 1)
    try:
        mod = import_module(module_name)
    except ImportError, e:
        raise ImproperlyConfigured(
            "WSGI application '%s' could not be loaded; "
            "could not import module '%s': %s" % (app_path, module_name, e))
    try:
        app = getattr(mod, attr)
    except AttributeError, e:
        raise ImproperlyConfigured(
            "WSGI application '%s' could not be loaded; "
            "can't find '%s' in module '%s': %s"
            % (app_path, attr, module_name, e))

    return app


class WSGIServerException(Exception):
    pass


class ServerHandler(simple_server.ServerHandler, object):
    error_status = "500 INTERNAL SERVER ERROR"

    def write(self, data):
        """'write()' callable as specified by PEP 333"""

        assert isinstance(data, str), "write() argument must be string"

        if not self.status:
            raise AssertionError("write() before start_response()")

        elif not self.headers_sent:
            # Before the first output, send the stored headers
            self.bytes_sent = len(data)    # make sure we know content-length
            self.send_headers()
        else:
            self.bytes_sent += len(data)

        # XXX check Content-Length and truncate if too many bytes written?

        # If data is too large, socket will choke, so write chunks no larger
        # than 32MB at a time.
        length = len(data)
        if length > 33554432:
            offset = 0
            while offset < length:
                chunk_size = min(33554432, length)
                self._write(data[offset:offset+chunk_size])
                self._flush()
                offset += chunk_size
        else:
            self._write(data)
            self._flush()

    def error_output(self, environ, start_response):
        super(ServerHandler, self).error_output(environ, start_response)
        return ['\n'.join(traceback.format_exception(*sys.exc_info()))]


class WSGIServer(simple_server.WSGIServer, object):
    """BaseHTTPServer that implements the Python WSGI protocol"""

    def __init__(self, *args, **kwargs):
        if kwargs.pop('ipv6', False):
            self.address_family = socket.AF_INET6
        super(WSGIServer, self).__init__(*args, **kwargs)

    def server_bind(self):
        """Override server_bind to store the server name."""
        try:
            super(WSGIServer, self).server_bind()
        except Exception, e:
            raise WSGIServerException(e)
        self.setup_environ()


class WSGIRequestHandler(simple_server.WSGIRequestHandler, object):

    def __init__(self, *args, **kwargs):
        from django.conf import settings
        self.admin_static_prefix = urlparse.urljoin(settings.STATIC_URL, 'admin/')
        # We set self.path to avoid crashes in log_message() on unsupported
        # requests (like "OPTIONS").
        self.path = ''
        self.style = color_style()
        super(WSGIRequestHandler, self).__init__(*args, **kwargs)

    def get_environ(self):
        env = self.server.base_environ.copy()
        env['SERVER_PROTOCOL'] = self.request_version
        env['REQUEST_METHOD'] = self.command
        if '?' in self.path:
            path,query = self.path.split('?',1)
        else:
            path,query = self.path,''

        env['PATH_INFO'] = urllib.unquote(path)
        env['QUERY_STRING'] = query
        env['REMOTE_ADDR'] = self.client_address[0]

        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader

        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length

        for h in self.headers.headers:
            k,v = h.split(':',1)
            k=k.replace('-','_').upper(); v=v.strip()
            if k in env:
                continue                    # skip content length, type,etc.
            if 'HTTP_'+k in env:
                env['HTTP_'+k] += ','+v     # comma-separate multiple headers
            else:
                env['HTTP_'+k] = v
        return env

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
        httpd_cls = type('WSGIServer', (ThreadingMixIn, WSGIServer), {})
    else:
        httpd_cls = WSGIServer
    httpd = httpd_cls(server_address, WSGIRequestHandler, ipv6=ipv6)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()
