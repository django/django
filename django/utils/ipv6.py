import ipaddress

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def clean_ipv6_address(
    ip_str, unpack_ipv4=False, error_message=_("This is not a valid IPv6 address.")
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
        addr = ipaddress.IPv6Address(int(ipaddress.IPv6Address(ip_str)))
    except ValueError:
        raise ValidationError(
            error_message, code="invalid", params={"protocol": _("IPv6")}
        )

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
        ipaddress.IPv6Address(ip_str)
    except ValueError:
        return False
    return True
