from __future__ import unicode_literals

from channels.http import AsgiHandler


"""
All Routing instances inside this file are also valid ASGI applications - with
new Channels routing, whatever you end up with as the top level object is just
served up as the "ASGI application".
"""


class ProtocolTypeRouter:
    """
    Takes a mapping of protocol type names to other Application instances,
    and dispatches to the right one based on protocol name (or raises an error)
    """

    def __init__(self, application_mapping):
        self.application_mapping = application_mapping

    def __call__(self, conntype):
        if conntype in self.application_mapping:
            return self.application_mapping[conntype](conntype)
        else:
            raise ValueError("No application configured for connection type %r" % conntype)


class DjangoHTTPViews:
    """
    Accepts HTTP connections and shunts them into the Django view system inside
    of a threadpool.
    """

    def __call__(self, conntype):
        # Make sure it's HTTP
        if conntype != "http":
            raise ValueError("The Django HTTP View system cannot handle a connection of type %r" % conntype)
        # Just return AsgiHandler
        return AsgiHandler(conntype)

