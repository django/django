"""Provides types used internally"""

from ipaddress import IPv4Address, IPv6Address
from typing import Union

IPAddress = Union[str, IPv6Address, IPv4Address]
