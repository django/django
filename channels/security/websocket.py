from urllib.parse import urlparse

from django.conf import settings
from django.http.request import validate_host

from ..generic.websocket import AsyncWebsocketConsumer


class OriginValidator:
    """
    Validates that the incoming connection has an Origin header that
    is in an allowed list.
    """

    def __init__(self, application, allowed_origins):
        self.application = application
        self.allowed_origins = allowed_origins

    def __call__(self, scope):
        # Make sure the scope is of type websocket
        if scope["type"] != "websocket":
            raise ValueError("You cannot use OriginValidator on a non-WebSocket connection")
        # Extract the Origin header
        origin_host = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"origin":
                print("got origin header, val %r" % header_value)
                try:
                    origin_host = urlparse(header_value.decode("ascii")).hostname
                    print("nuhost: %r" % origin_host)
                except UnicodeDecodeError:
                    pass
            else:
                print("non origin header: %r" % header_name)
        # Check to see if the origin header is valid
        print("origin header: %s" % origin_host)
        if self.valid_origin(origin_host):
            # Pass control to the application
            return self.application(scope)
        else:
            # Deny the connection
            return WebsocketDenier(scope)

    def valid_origin(self, origin):
        # None is not allowed
        if origin is None:
            return False
        # Check against our list
        return validate_host(origin, self.allowed_origins)


def AllowedHostsOriginValidator(application):
    """
    Factory function which returns an OriginValidator configured to use
    settings.ALLOWED_HOSTS.
    """
    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]
    return OriginValidator(application, allowed_hosts)


class WebsocketDenier(AsyncWebsocketConsumer):
    """
    Simple application which denies all requests to it.
    """

    async def connect(self):
        await self.close()
