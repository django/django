import errno
import http.client
import http.server
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from socketserver import ThreadingMixIn

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands.runserver import naiveip_re
from django.core.servers import basehttp
from django.utils.autoreload import StatReloader, file_changed

MAXIMUM_WAIT_FOR_DJANGO_RELOAD_IN_SECONDS = 10

logger = logging.getLogger(__name__)


def is_downstream_tcp_conn_cancel_error():
    # Similar to django.core.servers.basehttp.is_broken_pipe_error but also handles
    # ConnectionAbortedError which seems to happen on Windows
    exc_type, _, _ = sys.exc_info()
    return issubclass(exc_type, (BrokenPipeError, ConnectionAbortedError))


def get_free_listen_tcp_port(use_ipv6=False):
    s = socket.socket(socket.AF_INET6 if use_ipv6 else socket.AF_INET)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SimpleStatReloader(StatReloader):

    def __init__(self, *args, **kwargs):
        self.report_changes = False
        self.state = {}
        super().__init__(*args, **kwargs)

    def notify_file_changed(self, path):
        results = file_changed.send(sender=self, file_path=path)
        logger.debug('%s notified as changed. Signal results: %s.', path, results)
        if not any(res[1] for res in results):
            self.report_changes = True

    def update_state(self):
        for filepath, mtime in self.snapshot_files():
            old_time = self.state.get(filepath)
            self.state[filepath] = mtime
            if old_time is None:
                logger.debug('File %s first seen with mtime %s', filepath, mtime)
            elif mtime != old_time:
                logger.debug('File %s previous mtime: %s, current mtime: %s', filepath, old_time, mtime)
                self.notify_file_changed(filepath)

    def changes_detected(self):
        self.update_state()
        return_value = self.report_changes
        self.report_changes = False
        return return_value


class TransparentProxyHttpServer(http.server.HTTPServer):

    request_queue_size = basehttp.WSGIServer.request_queue_size

    def __init__(self, upstream_address, child_args, *args, ipv6=False, **kwargs):
        self.upstream_address = upstream_address
        self.child_proc = None
        self.child_args = child_args
        self.restart_child()
        self.reloader = SimpleStatReloader()
        self.scan_and_reload_lock = threading.Lock()
        if ipv6:
            self.address_family = socket.AF_INET6
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            self.kill_child()
            raise

    def handle_error(self, request, client_address):
        # handle_error() is part of the socketserver.BaseServer API
        if not is_downstream_tcp_conn_cancel_error():
            super().handle_error(request, client_address)

    def kill_child(self):
        if self.child_proc is not None:
            returncode = self.child_proc.poll()
            if returncode is None:
                self.child_proc.kill()
                self.child_proc.wait()

    def restart_child(self):
        self.kill_child()
        self.child_proc = subprocess.Popen(self.child_args, close_fds=False)
        return self.child_status()

    def check_for_changes_then_reload(self, path):
        if self.scan_and_reload_lock.acquire(blocking=False):
            try:
                if self.reloader.changes_detected() and self.restart_child():
                    self.reloader.update_state()
            finally:
                self.scan_and_reload_lock.release()
        else:
            with self.scan_and_reload_lock:
                pass

    def child_status(self):
        return self.child_proc and self.child_proc.poll() is None


class TransparentProxyThreadingHttpServer(ThreadingMixIn, TransparentProxyHttpServer):
    daemon_threads = True


class HttpRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        return self.do_verb()

    def do_POST(self):
        return self.do_verb()

    def do_HEAD(self):
        return self.do_verb()

    def get_request_content_len(self, req_headers):
        try:
            content_length = int(req_headers.get('Content-Length', '0'))
        except (TypeError, ValueError):
            content_length = 0
        else:
            if content_length < 0:
                content_length = 0
        return content_length

    def handle_request(self):
        req_content_len = self.get_request_content_len(self.headers)
        self.server.check_for_changes_then_reload(self.path)
        conn = http.client.HTTPConnection(*self.server.upstream_address)
        start_time = time.monotonic()
        while True:
            try:
                conn.connect()
            except ConnectionRefusedError:
                if time.monotonic() - start_time >= MAXIMUM_WAIT_FOR_DJANGO_RELOAD_IN_SECONDS:
                    os._exit(1)
                time.sleep(1)
            else:
                break

        conn.putrequest(self.command, self.path, skip_accept_encoding=True)
        for name, value in self.headers.items():
            if name.lower() == 'host':
                continue
            conn.putheader(name, value)

        while True:
            try:
                conn.endheaders(self.rfile.read(req_content_len) if req_content_len else None)
            except ConnectionRefusedError:
                if time.monotonic() - start_time >= MAXIMUM_WAIT_FOR_DJANGO_RELOAD_IN_SECONDS:
                    os._exit(1)
                time.sleep(1)
            else:
                break

        return conn

    def handle_response(self, conn):
        resp = conn.getresponse()
        resp_headers = resp.msg

        # HTTP/1.1 requires support for persistent connections. Send 'close' if
        # the content length is unknown to prevent clients from reusing the
        # connection.
        must_send_connection_close = 'Content-Length' not in resp_headers
        saw_connection_header = False

        self.send_response(resp.status, resp.reason)

        for name, value in resp_headers.items():
            lower_hdr_name = name.lower()
            if lower_hdr_name in ('date', 'server'):
                continue
            if lower_hdr_name == 'connection' and must_send_connection_close:
                saw_connection_header = True
                value = 'close'
                self.close_connection = True
            self.send_header(name, value)
        if not saw_connection_header:
            self.send_header('Connection', 'close')
            self.close_connection = True
        self.end_headers()

        self.wfile.write(resp.read())

    def do_verb(self):
        conn = self.handle_request()
        self.handle_response(conn)

    def handle(self):
        super().handle()
        try:
            self.connection.shutdown(socket.SHUT_WR)
        except (AttributeError, OSError):
            pass

    def log_message(self, format, *args):
        extra = {
            'request': self.request,
            'server_time': self.log_date_time_string(),
        }
        if args[1][0] == '4':
            # 0x16 = Handshake, 0x03 = SSL 3.0 or TLS 1.x
            if args[0].startswith('\x16\x03'):
                extra['status_code'] = 500
                logger.error(
                    "You're accessing the development server over HTTPS, but "
                    "it only supports HTTP.\n", extra=extra,
                )
                return


def run(server_address, upstream_address, child_args, ipv6=False, threading=False):
    httpd_cls = TransparentProxyThreadingHttpServer if threading else TransparentProxyHttpServer
    httpd = httpd_cls(upstream_address, child_args, server_address, HttpRequestHandler, ipv6=ipv6)
    httpd.serve_forever()


class Command(BaseCommand):
    help = "Starts a lightweight Web server+proxy for development."

    # Validation is called explicitly each time the child upstream server is reloaded.
    requires_system_checks = False

    default_addr = '127.0.0.1'
    default_addr_ipv6 = '::1'
    default_port = '8000'
    protocol = 'http'

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?',
            help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--ipv6', '-6', action='store_true', dest='use_ipv6',
            help='Tells Django to use an IPv6 address.',
        )
        parser.add_argument(
            '--nothreading', action='store_false', dest='use_threading',
            help='Tells Django to NOT use threading.',
        )
        parser.add_argument(
            '--noreload', action='store_false', dest='use_reloader',
            help='Tells Django to NOT use the auto-reloader.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not settings.ALLOWED_HOSTS:
            raise CommandError('You must set settings.ALLOWED_HOSTS if DEBUG is False.')

        self.use_ipv6 = options['use_ipv6']
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self.verbosity = options['verbosity']
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
            self.addr = self.default_addr_ipv6 if self.use_ipv6 else self.default_addr
            self._raw_ipv6 = self.use_ipv6

        child_args = self.upstream_child_args(**options)
        upstream_address = self.upstream_info(child_args)
        self.run(upstream_address, child_args, **options)

    def upstream_info(self, child_args):
        port = get_free_listen_tcp_port(use_ipv6=self.use_ipv6)
        if self.use_ipv6:
            addr = self.default_addr_ipv6
            netloc = '[{}]:{}'.format(addr, port)
        else:
            addr = self.default_addr
            netloc = '{}:{}'.format(addr, port)
        child_args.append(netloc)
        if self.verbosity >= 2:
            self.stdout.write("Upstream server will run at http://" + netloc)
        return addr, port

    def run(self, upstream_address, child_args, **options):

        threading = options['use_threading']
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        now = datetime.now().strftime('%B %d, %Y - %X')
        self.stdout.write(now)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server at %(protocol)s://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "protocol": self.protocol,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })

        try:
            run((self.addr, int(self.port)), upstream_address, child_args, ipv6=self.use_ipv6, threading=threading)
        except OSError as e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned to.",
            }
            try:
                error_text = ERRORS[e.errno]
            except KeyError:
                error_text = e
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            sys.exit(0)

    def upstream_child_args(self, **options):
        import django.__main__

        args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions]
        if sys.argv[0] == django.__main__.__file__:
            # The server was started with `python -m django serverrun`.
            args += ['-m', 'django']
        else:
            args += sys.argv[:1]
        args += ['runserver', '--noreload', '--really_quiet']
        addrport = options.get('addrport')
        if addrport:
            for arg in sys.argv[2:]:
                if arg != addrport:
                    args.append(arg)
        else:
            args += sys.argv[2:]
        return args
