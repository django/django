"""
IPv4 utility
"""


def clean_ipv4_address(ip_str):
    """
    Cleans an IPv4 address string.
    Args:
        ip_str: A valid IPv4 address.

    Returns:
        A normalized IPv4 address, or the same value
    """
    octets = ip_str.split(".")

    for index in range(len(octets)):
        # Remove leading zeroes
        octets[index] = octets[index].lstrip('0')
        if not octets[index]:
            octets[index] = '0'
    result = ".".join(octets)
    return result
