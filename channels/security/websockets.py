from functools import update_wrapper

from django.conf import settings
from django.http.request import validate_host

from ..exceptions import DenyConnection

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class BaseOriginValidator(object):
    """
    Base class-based decorator for origin validation of WebSocket connect
    messages.

    This base class handles parsing of the origin header. When the origin header
    is missing, empty or contains non-ascii characters, it raises a
    DenyConnection exception to reject the connection.

    Subclasses must overwrite the method validate_origin(self, message, origin)
    to return True when a message should be accepted, False otherwise.
    """

    def __init__(self, func):
        update_wrapper(self, func)
        self.func = func

    def __call__(self, message, *args, **kwargs):
        origin = self.get_origin(message)
        if not self.validate_origin(message, origin):
            raise DenyConnection
        return self.func(message, *args, **kwargs)

    def get_header(self, message, name):
        headers = message.content["headers"]
        for header in headers:
            try:
                if header[0] == name:
                    return header[1:]
            except IndexError:
                continue
        raise KeyError('No header named "{}"'.format(name))

    def get_origin(self, message):
        """
        Returns the origin of a WebSocket connect message.

        Raises DenyConnection for messages with missing or non-ascii Origin
        header.
        """
        try:
            header = self.get_header(message, b"origin")[0]
        except (IndexError, KeyError):
            raise DenyConnection
        try:
            origin = header.decode("ascii")
        except UnicodeDecodeError:
            raise DenyConnection
        return origin

    def validate_origin(self, message, origin):
        """
        Validates the origin of a WebSocket connect message.

        Must be overwritten by subclasses.
        """
        raise NotImplemented("You must overwrite this method.")


class AllowedHostsOnlyOriginValidator(BaseOriginValidator):
    """
    Class-based decorator for websocket consumers that checks that
    the origin is allowed according to the ALLOWED_HOSTS settings.
    """

    def validate_origin(self, message, origin):
        allowed_hosts = settings.ALLOWED_HOSTS
        if settings.DEBUG and not allowed_hosts:
            allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]

        origin_hostname = urlparse(origin).hostname
        valid = (origin_hostname and
                 validate_host(origin_hostname, allowed_hosts))
        return valid


allowed_hosts_only = AllowedHostsOnlyOriginValidator
