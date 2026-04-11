"""Provides types used internally."""

from ipaddress import IPv4Address, IPv6Address

IPAddress = str | IPv6Address | IPv4Address
