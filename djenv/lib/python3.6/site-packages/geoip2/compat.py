"""Intended for internal use only."""
import sys

import ipaddress

# pylint: skip-file

if sys.version_info[0] == 2:

    def compat_ip_address(address):
        """Intended for internal use only."""
        if isinstance(address, bytes):
            address = address.decode()
        return ipaddress.ip_address(address)
else:

    def compat_ip_address(address):
        """Intended for internal use only."""
        return ipaddress.ip_address(address)
