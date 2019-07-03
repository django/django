"""
Email message and email sending related helper functions.
"""

import socket

from django.utils.encoding import punycode


# Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
# seconds, which slows down the restart of the server.
class CachedDnsName:
    def __str__(self):
        return self.get_fqdn()

    def get_fqdn(self):
        if not hasattr(self, '_fqdn'):
            self._fqdn = punycode(socket.getfqdn())
        return self._fqdn


DNS_NAME = CachedDnsName()
