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
        if "http" not in self.application_mapping:
            self.application_mapping["http"] = AsgiHandler

    def __call__(self, scope):
        if scope["type"] in self.application_mapping:
            return self.application_mapping[scope["type"]](scope)
        else:
            raise ValueError("No application configured for scope type %r" % scope["type"])
