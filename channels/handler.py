from __future__ import unicode_literals

import cgi
import codecs
import logging
import sys
import time
import traceback
from io import BytesIO

from django import http
from django.conf import settings
from django.core import signals
from django.core.handlers import base
from django.core.urlresolvers import set_script_prefix
from django.http import FileResponse, HttpResponse, HttpResponseServerError
from django.utils import six
from django.utils.functional import cached_property

from channels.exceptions import RequestAborted, RequestTimeout, ResponseLater as ResponseLaterOuter

logger = logging.getLogger('django.request')


class AsgiRequest(http.HttpRequest):
    """
    Custom request subclass that decodes from an ASGI-standard request
    dict, and wraps request body handling.
    """

    ResponseLater = ResponseLaterOuter

    # Number of seconds until a Request gives up on trying to read a request
    # body and aborts.
    body_receive_timeout = 60

    def __init__(self, message):
        self.message = message
        self.reply_channel = self.message.reply_channel
        self._content_length = 0
        self._post_parse_error = False
        self._read_started = False
        self.resolver_match = None
        # Path info
        self.path = self.message['path']
        self.script_name = self.message.get('root_path', '')
        if self.script_name and self.path.startswith(self.script_name):
            # TODO: Better is-prefix checking, slash handling?
            self.path_info = self.path[len(self.script_name):]
        else:
            self.path_info = self.path
        # HTTP basics
        self.method = self.message['method'].upper()
        self.META = {
            "REQUEST_METHOD": self.method,
            "QUERY_STRING": self.message.get('query_string', ''),
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": self.path_info,
            # Old code will need these for a while
            "wsgi.multithread": True,
            "wsgi.multiprocess": True,
        }
        if self.message.get('client', None):
            self.META['REMOTE_ADDR'] = self.message['client'][0]
            self.META['REMOTE_HOST'] = self.META['REMOTE_ADDR']
            self.META['REMOTE_PORT'] = self.message['client'][1]
        if self.message.get('server', None):
            self.META['SERVER_NAME'] = self.message['server'][0]
            self.META['SERVER_PORT'] = six.text_type(self.message['server'][1])
        else:
            self.META['SERVER_NAME'] = "unknown"
            self.META['SERVER_PORT'] = "0"
        # Handle old style-headers for a transition period
        if "headers" in self.message and isinstance(self.message['headers'], dict):
            self.message['headers'] = [
                (x.encode("latin1"), y) for x, y in
                self.message['headers'].items()
            ]
        # Headers go into META
        for name, value in self.message.get('headers', []):
            name = name.decode("latin1")
            if name == "content-length":
                corrected_name = "CONTENT_LENGTH"
            elif name == "content-type":
                corrected_name = "CONTENT_TYPE"
            else:
                corrected_name = 'HTTP_%s' % name.upper().replace("-", "_")
            # HTTPbis say only ASCII chars are allowed in headers, but we latin1 just in case
            value = value.decode("latin1")
            if corrected_name in self.META:
                value = self.META[corrected_name] + "," + value
            self.META[corrected_name] = value
        # Pull out request encoding if we find it
        if "CONTENT_TYPE" in self.META:
            self.content_type, self.content_params = cgi.parse_header(self.META["CONTENT_TYPE"])
            if 'charset' in self.content_params:
                try:
                    codecs.lookup(self.content_params['charset'])
                except LookupError:
                    pass
                else:
                    self.encoding = self.content_params['charset']
        else:
            self.content_type, self.content_params = "", {}
        # Pull out content length info
        if self.META.get('CONTENT_LENGTH', None):
            try:
                self._content_length = int(self.META['CONTENT_LENGTH'])
            except (ValueError, TypeError):
                pass
        # Body handling
        self._body = message.get("body", b"")
        if message.get("body_channel", None):
            body_handle_start = time.time()
            while True:
                # Get the next chunk from the request body channel
                chunk = None
                while chunk is None:
                    # If they take too long, raise request timeout and the handler
                    # will turn it into a response
                    if time.time() - body_handle_start > self.body_receive_timeout:
                        raise RequestTimeout()
                    _, chunk = message.channel_layer.receive_many(
                        [message['body_channel']],
                        block=True,
                    )
                # If chunk contains close, abort.
                if chunk.get("closed", False):
                    raise RequestAborted()
                # Add content to body
                self._body += chunk.get("content", "")
                # Exit loop if this was the last
                if not chunk.get("more_content", False):
                    break
        assert isinstance(self._body, six.binary_type), "Body is not bytes"
        # Add a stream-a-like for the body
        self._stream = BytesIO(self._body)
        # Other bits
        self.resolver_match = None

    @cached_property
    def GET(self):
        return http.QueryDict(self.message.get('query_string', ''))

    def _get_post(self):
        if not hasattr(self, '_post'):
            self._read_started = False
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_files(self):
        if not hasattr(self, '_files'):
            self._read_started = False
            self._load_post_and_files()
        return self._files

    POST = property(_get_post, _set_post)
    FILES = property(_get_files)

    @cached_property
    def COOKIES(self):
        return http.parse_cookie(self.META.get('HTTP_COOKIE', ''))


class AsgiHandler(base.BaseHandler):
    """
    Handler for ASGI requests for the view system only (it will have got here
    after traversing the dispatch-by-channel-name system, which decides it's
    a HTTP request)
    """

    request_class = AsgiRequest

    # Size to chunk response bodies into for multiple response messages
    chunk_size = 512 * 1024

    def __init__(self, *args, **kwargs):
        super(AsgiHandler, self).__init__(*args, **kwargs)
        self.load_middleware()

    def __call__(self, message):
        # Set script prefix from message root_path, turning None into empty string
        set_script_prefix(message.get('root_path', '') or '')
        signals.request_started.send(sender=self.__class__, message=message)
        # Run request through view system
        try:
            request = self.request_class(message)
        except UnicodeDecodeError:
            logger.warning(
                'Bad Request (UnicodeDecodeError)',
                exc_info=sys.exc_info(),
                extra={
                    'status_code': 400,
                }
            )
            response = http.HttpResponseBadRequest()
        except RequestTimeout:
            # Parsing the rquest failed, so the response is a Request Timeout error
            response = HttpResponse("408 Request Timeout (upload too slow)", status_code=408)
        except RequestAborted:
            # Client closed connection on us mid request. Abort!
            return
        else:
            try:
                response = self.get_response(request)
                # Fix chunk size on file responses
                if isinstance(response, FileResponse):
                    response.block_size = 1024 * 512
            except AsgiRequest.ResponseLater:
                # The view has promised something else
                # will send a response at a later time
                return
        # Transform response into messages, which we yield back to caller
        for message in self.encode_response(response):
            # TODO: file_to_stream
            yield message
        # Close the response now we're done with it
        response.close()

    def process_exception_by_middleware(self, exception, request):
        """
        Catches ResponseLater and re-raises it, else tries to delegate
        to middleware exception handling.
        """
        if isinstance(exception, AsgiRequest.ResponseLater):
            raise
        else:
            return super(AsgiHandler, self).process_exception_by_middleware(exception, request)

    def handle_uncaught_exception(self, request, resolver, exc_info):
        """
        Propagates ResponseLater up into the higher handler method,
        processes everything else
        """
        # ResponseLater needs to be bubbled up the stack
        if issubclass(exc_info[0], AsgiRequest.ResponseLater):
            raise
        # There's no WSGI server to catch the exception further up if this fails,
        # so translate it into a plain text response.
        try:
            return super(AsgiHandler, self).handle_uncaught_exception(request, resolver, exc_info)
        except:
            return HttpResponseServerError(
                traceback.format_exc() if settings.DEBUG else "Internal Server Error",
                content_type="text/plain",
            )

    @classmethod
    def encode_response(cls, response):
        """
        Encodes a Django HTTP response into ASGI http.response message(s).
        """
        # Collect cookies into headers.
        # Note that we have to preserve header case as there are some non-RFC
        # compliant clients that want things like Content-Type correct. Ugh.
        response_headers = []
        for header, value in response.items():
            if isinstance(header, six.text_type):
                header = header.encode("ascii")
            if isinstance(value, six.text_type):
                value = value.encode("latin1")
            response_headers.append(
                (
                    six.binary_type(header),
                    six.binary_type(value),
                )
            )
        for c in response.cookies.values():
            response_headers.append(
                (
                    b'Set-Cookie',
                    c.output(header='').encode("ascii"),
                )
            )
        # Make initial response message
        message = {
            "status": response.status_code,
            "headers": response_headers,
        }
        # Streaming responses need to be pinned to their iterator
        if response.streaming:
            # Access `__iter__` and not `streaming_content` directly in case
            # it has been overridden in a subclass.
            for part in response:
                for chunk, more in cls.chunk_bytes(part):
                    message['content'] = chunk
                    # We ignore "more" as there may be more parts; instead,
                    # we use an empty final closing message with False.
                    message['more_content'] = True
                    yield message
                    message = {}
            # Final closing message
            message["more_content"] = False
            yield message
        # Other responses just need chunking
        else:
            # Yield chunks of response
            for chunk, last in cls.chunk_bytes(response.content):
                message['content'] = chunk
                message['more_content'] = not last
                yield message
                message = {}

    @classmethod
    def chunk_bytes(cls, data):
        """
        Chunks some data into chunks based on the current ASGI channel layer's
        message size and reasonable defaults.

        Yields (chunk, last_chunk) tuples.
        """
        position = 0
        if not data:
            yield data, True
            return
        while position < len(data):
            yield (
                data[position:position + cls.chunk_size],
                (position + cls.chunk_size) >= len(data),
            )
            position += cls.chunk_size


class ViewConsumer(object):
    """
    Dispatches channel HTTP requests into django's URL/View system.
    """

    handler_class = AsgiHandler

    def __init__(self):
        self.handler = self.handler_class()

    def __call__(self, message):
        for reply_message in self.handler(message):
            while True:
                # If we get ChannelFull we just wait and keep trying until
                # it goes through.
                # TODO: Add optional death timeout? Don't want to lock up
                # a whole worker if the client just vanishes and leaves the response
                # channel full.
                try:
                    # Note: Use immediately to prevent streaming responses trying
                    # cache all data.
                    message.reply_channel.send(reply_message, immediately=True)
                except message.channel_layer.ChannelFull:
                    time.sleep(0.05)
                else:
                    break
