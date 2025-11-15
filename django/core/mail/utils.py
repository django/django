"""
Email message and email sending related helper functions.
"""

import socket


# Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
# seconds, which slows down the restart of the server.
class CachedDnsName:
    def __str__(self):
        return self.get_fqdn()

    def get_fqdn(self):
        if not hasattr(self, '_fqdn'):
            self._fqdn = self._encode_domain(socket.getfqdn())
        return self._fqdn

    def _encode_domain(self, domain):
        """Convert domain to ASCII-compatible encoding (punycode)."""
        try:
            domain.encode('ascii')
        except UnicodeEncodeError:
            domain = domain.encode('idna').decode('ascii')
        return domain


DNS_NAME = CachedDnsName()
