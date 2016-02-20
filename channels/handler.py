from __future__ import unicode_literals

import cgi
import codecs
import logging
import sys
from io import BytesIO
from threading import Lock

from django import http
from django.core import signals
from django.core.handlers import base
from django.core.urlresolvers import set_script_prefix
from django.utils import six
from django.utils.functional import cached_property

logger = logging.getLogger('django.request')


class AsgiRequest(http.HttpRequest):
    """
    Custom request subclass that decodes from an ASGI-standard request
    dict, and wraps request body handling.
    """

    class ResponseLater(Exception):
        """
        Exception that will cause any handler to skip around response
        transmission and presume something else will do it later.
        """
        def __init__(self):
            Exception.__init__(self, "Response later")

    def __init__(self, message):
        self.message = message
        self.reply_channel = self.message.reply_channel
        self._content_length = 0
        self._post_parse_error = False
        self.resolver_match = None
        # Path info
        self.path = self.message['path'].decode("ascii")
        self.script_name = self.message.get('root_path', b'')
        if self.script_name:
            # TODO: Better is-prefix checking, slash handling?
            self.path_info = self.path[len(self.script_name):]
        else:
            self.path_info = self.path
        # HTTP basics
        self.method = self.message['method'].upper()
        self.META = {
            "REQUEST_METHOD": self.method,
            "QUERY_STRING": self.message.get('query_string', b'').decode("ascii"),
            "SCRIPT_NAME": self.script_name.decode("ascii"),
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
            self.META['SERVER_PORT'] = self.message['server'][1]
        # Headers go into META
        for name, value in self.message.get('headers', {}).items():
            if name == "content-length":
                corrected_name = "CONTENT_LENGTH"
            elif name == "content-type":
                corrected_name = "CONTENT_TYPE"
            else:
                corrected_name = 'HTTP_%s' % name.upper().replace("-", "_")
            # HTTPbis say only ASCII chars are allowed in headers
            self.META[corrected_name] = value.decode("ascii")
        # Pull out request encoding if we find it
        if "CONTENT_TYPE" in self.META:
            _, content_params = cgi.parse_header(self.META["CONTENT_TYPE"])
            if 'charset' in content_params:
                try:
                    codecs.lookup(content_params['charset'])
                except LookupError:
                    pass
                else:
                    self.encoding = content_params['charset']
        # Pull out content length info
        if self.META.get('CONTENT_LENGTH', None):
            try:
                self._content_length = int(self.META['CONTENT_LENGTH'])
            except (ValueError, TypeError):
                pass
        # Body handling
        self._body = message.get("body", b"")
        if message.get("body_channel", None):
            while True:
                # Get the next chunk from the request body channel
                chunk = None
                while chunk is None:
                    _, chunk = message.channel_layer.receive_many(
                        [message['body_channel']],
                        block=True,
                    )
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
        return http.QueryDict(
            self.message.get('query_string', ''),
            encoding=self._encoding,
        )

    def _get_post(self):
        if not hasattr(self, '_post'):
            self._read_started = False
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_files(self):
        if not hasattr(self, '_files'):
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

    initLock = Lock()
    request_class = AsgiRequest

    # Size to chunk response bodies into for multiple response messages
    chunk_size = 512 * 1024

    def __call__(self, message):
        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            with self.initLock:
                # Check that middleware is still uninitialized.
                if self._request_middleware is None:
                    self.load_middleware()
        # Set script prefix from message root_path
        set_script_prefix(message.get('root_path', ''))
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
        else:
            try:
                response = self.get_response(request)
            except AsgiRequest.ResponseLater:
                # The view has promised something else
                # will send a response at a later time
                return
        # Transform response into messages, which we yield back to caller
        for message in self.encode_response(response):
            # TODO: file_to_stream
            yield message

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
        if issubclass(exc_info[0], AsgiRequest.ResponseLater):
            raise
        return super(AsgiHandler, self).handle_uncaught_exception(request, resolver, exc_info)

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
            if isinstance(header, six.binary_type):
                header = header.decode("latin1")
            if isinstance(value, six.text_type):
                value = value.encode("latin1")
            response_headers.append(
                (
                    six.text_type(header),
                    six.binary_type(value),
                )
            )
        for c in response.cookies.values():
            response_headers.append(
                (
                    'Set-Cookie',
                    c.output(header='').encode("ascii"),
                )
            )
        # Make initial response message
        message = {
            "status": response.status_code,
            "status_text": response.reason_phrase.encode("ascii"),
            "headers": response_headers,
        }
        # Streaming responses need to be pinned to their iterator
        if response.streaming:
            for part in response.streaming_content:
                for chunk in cls.chunk_bytes(part):
                    message['content'] = chunk
                    message['more_content'] = True
                    yield message
                    message = {}
            # Final closing message
            yield {
                "more_content": False,
            }
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
            message.reply_channel.send(reply_message)
