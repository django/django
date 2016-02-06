from __future__ import unicode_literals

import sys
import logging
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

    def __init__(self, message):
        self.message = message
        self.reply_channel = self.message.reply_channel
        self._content_length = 0
        self._post_parse_error = False
        self.resolver_match = None
        # Path info
        self.path = self.message['path']
        self.script_name = self.message.get('root_path', '')
        if self.script_name:
            # TODO: Better is-prefix checking, slash handling?
            self.path_info = self.path[len(self.script_name):]
        else:
            self.path_info = self.path
        # HTTP basics
        self.method = self.message['method'].upper()
        self.META = {
            "REQUEST_METHOD": self.method,
            "QUERY_STRING": self.message.get('query_string', ''),
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
            self.META[corrected_name] = value
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
            response = self.get_response(request)
        # Transform response into messages, which we yield back to caller
        for message in self.encode_response(response):
            # TODO: file_to_stream
            yield message

    def encode_response(self, response):
        """
        Encodes a Django HTTP response into an ASGI http.response message(s).
        """
        # Collect cookies into headers.
        # Note that we have to preserve header case as there are some non-RFC
        # compliant clients that want things like Content-Type correct. Ugh.
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        for c in response.cookies.values():
            response_headers.append((str('Set-Cookie'), str(c.output(header=''))))
        # Make initial response message
        message = {
            "status": response.status_code,
            "status_text": response.reason_phrase,
            "headers": response_headers,
        }
        # Streaming responses need to be pinned to their iterator
        if response.streaming:
            for part in response.streaming_content:
                for chunk in self.chunk_bytes(part):
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
            for chunk, last in self.chunk_bytes(response.content):
                message['content'] = chunk
                message['more_content'] = not last
                yield message
                message = {}

    def chunk_bytes(self, data):
        """
        Chunks some data into chunks based on the current ASGI channel layer's
        message size and reasonable defaults.

        Yields (chunk, last_chunk) tuples.
        """
        position = 0
        while position < len(data):
            yield (
                data[position:position + self.chunk_size],
                (position + self.chunk_size) >= len(data),
            )
            position += self.chunk_size


class ViewConsumer(object):
    """
    Dispatches channel HTTP requests into django's URL/View system.
    """

    def __init__(self):
        self.handler = AsgiHandler()

    def __call__(self, message):
        for reply_message in self.handler(message):
            message.reply_channel.send(reply_message)
