import ipaddress

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_IPV6_ADDRESS_LENGTH = 39


def _ipv6_address_from_str(ip_str, max_length=MAX_IPV6_ADDRESS_LENGTH):
    if len(ip_str) > max_length:
        raise ValueError(
            f"Unable to convert {ip_str} to an IPv6 address (value too long)."
        )
    return ipaddress.IPv6Address(int(ipaddress.IPv6Address(ip_str)))


def clean_ipv6_address(
    ip_str,
    unpack_ipv4=False,
    error_message=_("This is not a valid IPv6 address."),
    max_length=MAX_IPV6_ADDRESS_LENGTH,
):
    """
    Clean an IPv6 address string.

    Raise ValidationError if the address is invalid.

    Replace the longest continuous zero-sequence with "::", remove leading
    zeroes, and make sure all hextets are lowercase.

    Args:
        ip_str: A valid IPv6 address.
        unpack_ipv4: if an IPv4-mapped address is found,
        return the plain IPv4 address (default=False).
        error_message: An error message used in the ValidationError.

    Return a compressed IPv6 address or the same value.
    """
    try:
        addr = _ipv6_address_from_str(ip_str, max_length)
    except ValueError:
        raise ValidationError(error_message, code="invalid")

    if unpack_ipv4 and addr.ipv4_mapped:
        return str(addr.ipv4_mapped)
    elif addr.ipv4_mapped:
        return "::ffff:%s" % str(addr.ipv4_mapped)

    return str(addr)


def is_valid_ipv6_address(ip_str):
    """
    Return whether or not the `ip_str` string is a valid IPv6 address.
    """
    try:
        _ipv6_address_from_str(ip_str)
    except ValueError:
        return False
    return True
