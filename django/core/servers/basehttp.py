"""
BaseHTTPServer that implements the Python WSGI protocol (PEP 333, rev 1.21).

Adapted from wsgiref.simple_server: http://svn.eby-sarna.com/wsgiref/

This is a simple server for use in testing or debugging Django apps. It hasn't
been reviewed for security issues. Don't use it for production use.
"""

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from types import ListType, StringType, TupleType
import os, re, sys, time, urllib

__version__ = "0.1"
__all__ = ['WSGIServer','WSGIRequestHandler','demo_app']

server_version = "WSGIServer/" + __version__
sys_version = "Python/" + sys.version.split()[0]
software_version = server_version + ' ' + sys_version

class WSGIServerException(Exception):
    pass

class FileWrapper:
    """Wrapper to convert file-like objects to iterables"""

    def __init__(self, filelike, blksize=8192):
        self.filelike = filelike
        self.blksize = blksize
        if hasattr(filelike,'close'):
            self.close = filelike.close

    def __getitem__(self,key):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError

    def __iter__(self):
        return self

    def next(self):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise StopIteration

# Regular expression that matches `special' characters in parameters, the
# existance of which force quoting of the parameter value.
tspecials = re.compile(r'[ \(\)<>@,;:\\"/\[\]\?=]')

def _formatparam(param, value=None, quote=1):
    """Convenience function to format and return a key=value pair.

    This will quote the value if needed or if quote is true.
    """
    if value is not None and len(value) > 0:
        if quote or tspecials.search(value):
            value = value.replace('\\', '\\\\').replace('"', r'\"')
            return '%s="%s"' % (param, value)
        else:
            return '%s=%s' % (param, value)
    else:
        return param

class Headers:
    """Manage a collection of HTTP response headers"""
    def __init__(self,headers):
        if type(headers) is not ListType:
            raise TypeError("Headers must be a list of name/value tuples")
        self._headers = headers

    def __len__(self):
        """Return the total number of headers, including duplicates."""
        return len(self._headers)

    def __setitem__(self, name, val):
        """Set the value of a header."""
        del self[name]
        self._headers.append((name, val))

    def __delitem__(self,name):
        """Delete all occurrences of a header, if present.

        Does *not* raise an exception if the header is missing.
        """
        name = name.lower()
        self._headers[:] = [kv for kv in self._headers if kv[0].lower()<>name]

    def __getitem__(self,name):
        """Get the first header value for 'name'

        Return None if the header is missing instead of raising an exception.

        Note that if the header appeared multiple times, the first exactly which
        occurrance gets returned is undefined.  Use getall() to get all
        the values matching a header field name.
        """
        return self.get(name)

    def has_key(self, name):
        """Return true if the message contains the header."""
        return self.get(name) is not None

    __contains__ = has_key

    def get_all(self, name):
        """Return a list of all the values for the named field.

        These will be sorted in the order they appeared in the original header
        list or were added to this instance, and may contain duplicates.  Any
        fields deleted and re-inserted are always appended to the header list.
        If no fields exist with the given name, returns an empty list.
        """
        name = name.lower()
        return [kv[1] for kv in self._headers if kv[0].lower()==name]


    def get(self,name,default=None):
        """Get the first header value for 'name', or return 'default'"""
        name = name.lower()
        for k,v in self._headers:
            if k.lower()==name:
                return v
        return default

    def keys(self):
        """Return a list of all the header field names.

        These will be sorted in the order they appeared in the original header
        list, or were added to this instance, and may contain duplicates.
        Any fields deleted and re-inserted are always appended to the header
        list.
        """
        return [k for k, v in self._headers]

    def values(self):
        """Return a list of all header values.

        These will be sorted in the order they appeared in the original header
        list, or were added to this instance, and may contain duplicates.
        Any fields deleted and re-inserted are always appended to the header
        list.
        """
        return [v for k, v in self._headers]

    def items(self):
        """Get all the header fields and values.

        These will be sorted in the order they were in the original header
        list, or were added to this instance, and may contain duplicates.
        Any fields deleted and re-inserted are always appended to the header
        list.
        """
        return self._headers[:]

    def __repr__(self):
        return "Headers(%s)" % `self._headers`

    def __str__(self):
        """str() returns the formatted headers, complete with end line,
        suitable for direct HTTP transmission."""
        return '\r\n'.join(["%s: %s" % kv for kv in self._headers]+['',''])

    def setdefault(self,name,value):
        """Return first matching header value for 'name', or 'value'

        If there is no header named 'name', add a new header with name 'name'
        and value 'value'."""
        result = self.get(name)
        if result is None:
            self._headers.append((name,value))
            return value
        else:
            return result

    def add_header(self, _name, _value, **_params):
        """Extended header setting.

        _name is the header field to add.  keyword arguments can be used to set
        additional parameters for the header field, with underscores converted
        to dashes.  Normally the parameter will be added as key="value" unless
        value is None, in which case only the key will be added.

        Example:

        h.add_header('content-disposition', 'attachment', filename='bud.gif')

        Note that unlike the corresponding 'email.Message' method, this does
        *not* handle '(charset, language, value)' tuples: all values must be
        strings or None.
        """
        parts = []
        if _value is not None:
            parts.append(_value)
        for k, v in _params.items():
            if v is None:
                parts.append(k.replace('_', '-'))
            else:
                parts.append(_formatparam(k.replace('_', '-'), v))
        self._headers.append((_name, "; ".join(parts)))

def guess_scheme(environ):
    """Return a guess for whether 'wsgi.url_scheme' should be 'http' or 'https'
    """
    if environ.get("HTTPS") in ('yes','on','1'):
        return 'https'
    else:
        return 'http'

_hoppish = {
    'connection':1, 'keep-alive':1, 'proxy-authenticate':1,
    'proxy-authorization':1, 'te':1, 'trailers':1, 'transfer-encoding':1,
    'upgrade':1
}.has_key

def is_hop_by_hop(header_name):
    """Return true if 'header_name' is an HTTP/1.1 "Hop-by-Hop" header"""
    return _hoppish(header_name.lower())

class ServerHandler:
    """Manage the invocation of a WSGI application"""

    # Configuration parameters; can override per-subclass or per-instance
    wsgi_version = (1,0)
    wsgi_multithread = True
    wsgi_multiprocess = True
    wsgi_run_once = False

    origin_server = True    # We are transmitting direct to client
    http_version  = "1.0"   # Version that should be used for response
    server_software = software_version

    # os_environ is used to supply configuration from the OS environment:
    # by default it's a copy of 'os.environ' as of import time, but you can
    # override this in e.g. your __init__ method.
    os_environ = dict(os.environ.items())

    # Collaborator classes
    wsgi_file_wrapper = FileWrapper     # set to None to disable
    headers_class = Headers             # must be a Headers-like class

    # Error handling (also per-subclass or per-instance)
    traceback_limit = None  # Print entire traceback to self.get_stderr()
    error_status = "500 Dude, this is whack!"
    error_headers = [('Content-Type','text/plain')]

    # State variables (don't mess with these)
    status = result = None
    headers_sent = False
    headers = None
    bytes_sent = 0

    def __init__(self, stdin, stdout, stderr, environ, multithread=True,
        multiprocess=False):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.base_env = environ
        self.wsgi_multithread = multithread
        self.wsgi_multiprocess = multiprocess

    def run(self, application):
        """Invoke the application"""
        # Note to self: don't move the close()!  Asynchronous servers shouldn't
        # call close() from finish_response(), so if you close() anywhere but
        # the double-error branch here, you'll break asynchronous servers by
        # prematurely closing.  Async servers must return from 'run()' without
        # closing if there might still be output to iterate over.
        try:
            self.setup_environ()
            self.result = application(self.environ, self.start_response)
            self.finish_response()
        except:
            try:
                self.handle_error()
            except:
                # If we get an error handling an error, just give up already!
                self.close()
                raise   # ...and let the actual server figure it out.

    def setup_environ(self):
        """Set up the environment for one request"""

        env = self.environ = self.os_environ.copy()
        self.add_cgi_vars()

        env['wsgi.input']        = self.get_stdin()
        env['wsgi.errors']       = self.get_stderr()
        env['wsgi.version']      = self.wsgi_version
        env['wsgi.run_once']     = self.wsgi_run_once
        env['wsgi.url_scheme']   = self.get_scheme()
        env['wsgi.multithread']  = self.wsgi_multithread
        env['wsgi.multiprocess'] = self.wsgi_multiprocess

        if self.wsgi_file_wrapper is not None:
            env['wsgi.file_wrapper'] = self.wsgi_file_wrapper

        if self.origin_server and self.server_software:
            env.setdefault('SERVER_SOFTWARE',self.server_software)

    def finish_response(self):
        """Send any iterable data, then close self and the iterable

        Subclasses intended for use in asynchronous servers will
        want to redefine this method, such that it sets up callbacks
        in the event loop to iterate over the data, and to call
        'self.close()' once the response is finished.
        """
        if not self.result_is_file() and not self.sendfile():
            for data in self.result:
                self.write(data)
            self.finish_content()
        self.close()

    def get_scheme(self):
        """Return the URL scheme being used"""
        return guess_scheme(self.environ)

    def set_content_length(self):
        """Compute Content-Length or switch to chunked encoding if possible"""
        try:
            blocks = len(self.result)
        except (TypeError,AttributeError,NotImplementedError):
            pass
        else:
            if blocks==1:
                self.headers['Content-Length'] = str(self.bytes_sent)
                return
        # XXX Try for chunked encoding if origin server and client is 1.1

    def cleanup_headers(self):
        """Make any necessary header changes or defaults

        Subclasses can extend this to add other defaults.
        """
        if not self.headers.has_key('Content-Length'):
            self.set_content_length()

    def start_response(self, status, headers,exc_info=None):
        """'start_response()' callable as specified by PEP 333"""

        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None        # avoid dangling circular ref
        elif self.headers is not None:
            raise AssertionError("Headers already set!")

        assert type(status) is StringType,"Status must be a string"
        assert len(status)>=4,"Status must be at least 4 characters"
        assert int(status[:3]),"Status message must begin w/3-digit code"
        assert status[3]==" ", "Status message must have a space after code"
        if __debug__:
            for name,val in headers:
                assert type(name) is StringType,"Header names must be strings"
                assert type(val) is StringType,"Header values must be strings"
                assert not is_hop_by_hop(name),"Hop-by-hop headers not allowed"
        self.status = status
        self.headers = self.headers_class(headers)
        return self.write

    def send_preamble(self):
        """Transmit version/status/date/server, via self._write()"""
        if self.origin_server:
            if self.client_is_modern():
                self._write('HTTP/%s %s\r\n' % (self.http_version,self.status))
                if not self.headers.has_key('Date'):
                    self._write(
                        'Date: %s\r\n' % time.asctime(time.gmtime(time.time()))
                    )
                if self.server_software and not self.headers.has_key('Server'):
                    self._write('Server: %s\r\n' % self.server_software)
        else:
            self._write('Status: %s\r\n' % self.status)

    def write(self, data):
        """'write()' callable as specified by PEP 333"""

        assert type(data) is StringType,"write() argument must be string"

        if not self.status:
             raise AssertionError("write() before start_response()")

        elif not self.headers_sent:
            # Before the first output, send the stored headers
            self.bytes_sent = len(data)    # make sure we know content-length
            self.send_headers()
        else:
            self.bytes_sent += len(data)

        # XXX check Content-Length and truncate if too many bytes written?
        self._write(data)
        self._flush()

    def sendfile(self):
        """Platform-specific file transmission

        Override this method in subclasses to support platform-specific
        file transmission.  It is only called if the application's
        return iterable ('self.result') is an instance of
        'self.wsgi_file_wrapper'.

        This method should return a true value if it was able to actually
        transmit the wrapped file-like object using a platform-specific
        approach.  It should return a false value if normal iteration
        should be used instead.  An exception can be raised to indicate
        that transmission was attempted, but failed.

        NOTE: this method should call 'self.send_headers()' if
        'self.headers_sent' is false and it is going to attempt direct
        transmission of the file1.
        """
        return False   # No platform-specific transmission by default

    def finish_content(self):
        """Ensure headers and content have both been sent"""
        if not self.headers_sent:
            self.headers['Content-Length'] = "0"
            self.send_headers()
        else:
            pass # XXX check if content-length was too short?

    def close(self):
        try:
            self.request_handler.log_request(self.status.split(' ',1)[0], self.bytes_sent)
        finally:
            try:
                if hasattr(self.result,'close'):
                    self.result.close()
            finally:
                self.result = self.headers = self.status = self.environ = None
                self.bytes_sent = 0; self.headers_sent = False

    def send_headers(self):
        """Transmit headers to the client, via self._write()"""
        self.cleanup_headers()
        self.headers_sent = True
        if not self.origin_server or self.client_is_modern():
            self.send_preamble()
            self._write(str(self.headers))

    def result_is_file(self):
        """True if 'self.result' is an instance of 'self.wsgi_file_wrapper'"""
        wrapper = self.wsgi_file_wrapper
        return wrapper is not None and isinstance(self.result,wrapper)

    def client_is_modern(self):
        """True if client can accept status and headers"""
        return self.environ['SERVER_PROTOCOL'].upper() != 'HTTP/0.9'

    def log_exception(self,exc_info):
        """Log the 'exc_info' tuple in the server log

        Subclasses may override to retarget the output or change its format.
        """
        try:
            from traceback import print_exception
            stderr = self.get_stderr()
            print_exception(
                exc_info[0], exc_info[1], exc_info[2],
                self.traceback_limit, stderr
            )
            stderr.flush()
        finally:
            exc_info = None

    def handle_error(self):
        """Log current error, and send error output to client if possible"""
        self.log_exception(sys.exc_info())
        if not self.headers_sent:
            self.result = self.error_output(self.environ, self.start_response)
            self.finish_response()
        # XXX else: attempt advanced recovery techniques for HTML or text?

    def error_output(self, environ, start_response):
        import traceback
        start_response(self.error_status, self.error_headers[:], sys.exc_info())
        return ['\n'.join(traceback.format_exception(*sys.exc_info()))]

    # Pure abstract methods; *must* be overridden in subclasses

    def _write(self,data):
        self.stdout.write(data)
        self._write = self.stdout.write

    def _flush(self):
        self.stdout.flush()
        self._flush = self.stdout.flush

    def get_stdin(self):
        return self.stdin

    def get_stderr(self):
        return self.stderr

    def add_cgi_vars(self):
        self.environ.update(self.base_env)

class WSGIServer(HTTPServer):
    """BaseHTTPServer that implements the Python WSGI protocol"""
    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        try:
            HTTPServer.server_bind(self)
        except Exception, e:
            raise WSGIServerException, e
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application

class WSGIRequestHandler(BaseHTTPRequestHandler):
    server_version = "WSGIServer/" + __version__

    def __init__(self, *args, **kwargs):
        from django.conf.settings import ADMIN_MEDIA_PREFIX
        self.admin_media_prefix = ADMIN_MEDIA_PREFIX
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

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

        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
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

    def get_stderr(self):
        return sys.stderr

    def handle(self):
        """Handle a single HTTP request"""
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return
        handler = ServerHandler(self.rfile, self.wfile, self.get_stderr(), self.get_environ())
        handler.request_handler = self      # backpointer for logging
        handler.run(self.server.get_app())

    def log_message(self, format, *args):
        # Don't bother logging requests for admin images or the favicon.
        if self.path.startswith(self.admin_media_prefix) or self.path == '/favicon.ico':
            return
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

def run(port, wsgi_handler):
    server_address = ('', port)
    httpd = WSGIServer(server_address, WSGIRequestHandler)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()
