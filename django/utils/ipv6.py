# This code was mostly based on ipaddr-py
# Copyright 2007 Google Inc. https://github.com/google/ipaddr-py
# Licensed under the Apache License, Version 2.0 (the "License").
import re

from django.core.exceptions import ValidationError
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _


def clean_ipv6_address(ip_str, unpack_ipv4=False,
                       error_message=_("This is not a valid IPv6 address.")):
    """
    Cleans an IPv6 address string.

    Validity is checked by calling is_valid_ipv6_address() - if an
    invalid address is passed, ValidationError is raised.

    Replaces the longest continuous zero-sequence with "::" and
    removes leading zeroes and makes sure all hextets are lowercase.

    Args:
        ip_str: A valid IPv6 address.
        unpack_ipv4: if an IPv4-mapped address is found,
        return the plain IPv4 address (default=False).
        error_message: An error message used in the ValidationError.

    Returns:
        A compressed IPv6 address, or the same value
    """
    best_doublecolon_start = -1
    best_doublecolon_len = 0
    doublecolon_start = -1
    doublecolon_len = 0

    if not is_valid_ipv6_address(ip_str):
        raise ValidationError(error_message, code='invalid')

    # This algorithm can only handle fully exploded
    # IP strings
    ip_str = _explode_shorthand_ip_string(ip_str)

    ip_str = _sanitize_ipv4_mapping(ip_str)

    # If needed, unpack the IPv4 and return straight away
    # - no need in running the rest of the algorithm
    if unpack_ipv4:
        ipv4_unpacked = _unpack_ipv4(ip_str)

        if ipv4_unpacked:
            return ipv4_unpacked

    hextets = ip_str.split(":")

    for index in range(len(hextets)):
        # Remove leading zeroes
        if '.' not in hextets[index]:
            hextets[index] = hextets[index].lstrip('0')
        if not hextets[index]:
            hextets[index] = '0'

        # Determine best hextet to compress
        if hextets[index] == '0':
            doublecolon_len += 1
            if doublecolon_start == -1:
                # Start of a sequence of zeros.
                doublecolon_start = index
            if doublecolon_len > best_doublecolon_len:
                # This is the longest sequence of zeros so far.
                best_doublecolon_len = doublecolon_len
                best_doublecolon_start = doublecolon_start
        else:
            doublecolon_len = 0
            doublecolon_start = -1

    # Compress the most suitable hextet
    if best_doublecolon_len > 1:
        best_doublecolon_end = (best_doublecolon_start +
                                best_doublecolon_len)
        # For zeros at the end of the address.
        if best_doublecolon_end == len(hextets):
            hextets += ['']
        hextets[best_doublecolon_start:best_doublecolon_end] = ['']
        # For zeros at the beginning of the address.
        if best_doublecolon_start == 0:
            hextets = [''] + hextets

    result = ":".join(hextets)

    return result.lower()


def _sanitize_ipv4_mapping(ip_str):
    """
    Sanitize IPv4 mapping in an expanded IPv6 address.

    This converts ::ffff:0a0a:0a0a to ::ffff:10.10.10.10.
    If there is nothing to sanitize, returns an unchanged
    string.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The sanitized output string, if applicable.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        # not an ipv4 mapping
        return ip_str

    hextets = ip_str.split(':')

    if '.' in hextets[-1]:
        # already sanitized
        return ip_str

    ipv4_address = "%d.%d.%d.%d" % (
        int(hextets[6][0:2], 16),
        int(hextets[6][2:4], 16),
        int(hextets[7][0:2], 16),
        int(hextets[7][2:4], 16),
    )

    result = ':'.join(hextets[0:6])
    result += ':' + ipv4_address

    return result


def _unpack_ipv4(ip_str):
    """
    Unpack an IPv4 address that was mapped in a compressed IPv6 address.

    This converts 0000:0000:0000:0000:0000:ffff:10.10.10.10 to 10.10.10.10.
    If there is nothing to sanitize, returns None.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The unpacked IPv4 address, or None if there was nothing to unpack.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        return None

    return ip_str.rsplit(':', 1)[1]


def is_valid_ipv6_address(ip_str):
    """
    Ensure we have a valid IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A boolean, True if this is a valid IPv6 address.
    """
    from django.core.validators import validate_ipv4_address

    symbols_re = re.compile(r'^[0-9a-fA-F:.]+$')
    if not symbols_re.match(ip_str):
        return False

    # We need to have at least one ':'.
    if ':' not in ip_str:
        return False

    # We can only have one '::' shortener.
    if ip_str.count('::') > 1:
        return False

    # '::' should be encompassed by start, digits or end.
    if ':::' in ip_str:
        return False

    # A single colon can neither start nor end an address.
    if ((ip_str.startswith(':') and not ip_str.startswith('::')) or
            (ip_str.endswith(':') and not ip_str.endswith('::'))):
        return False

    # We can never have more than 7 ':' (1::2:3:4:5:6:7:8 is invalid)
    if ip_str.count(':') > 7:
        return False

    # If we have no concatenation, we need to have 8 fields with 7 ':'.
    if '::' not in ip_str and ip_str.count(':') != 7:
        # We might have an IPv4 mapped address.
        if ip_str.count('.') != 3:
            return False

    ip_str = _explode_shorthand_ip_string(ip_str)

    # Now that we have that all squared away, let's check that each of the
    # hextets are between 0x0 and 0xFFFF.
    for hextet in ip_str.split(':'):
        if hextet.count('.') == 3:
            # If we have an IPv4 mapped address, the IPv4 portion has to
            # be at the end of the IPv6 portion.
            if not ip_str.split(':')[-1] == hextet:
                return False
            try:
                validate_ipv4_address(hextet)
            except ValidationError:
                return False
        else:
            try:
                # a value error here means that we got a bad hextet,
                # something like 0xzzzz
                if int(hextet, 16) < 0x0 or int(hextet, 16) > 0xFFFF:
                    return False
            except ValueError:
                return False
    return True


def _explode_shorthand_ip_string(ip_str):
    """
    Expand a shortened IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A string, the expanded IPv6 address.
    """
    if not _is_shorthand_ip(ip_str):
        # We've already got a longhand ip_str.
        return ip_str

    new_ip = []
    hextet = ip_str.split('::')

    # If there is a ::, we need to expand it with zeroes
    # to get to 8 hextets - unless there is a dot in the last hextet,
    # meaning we're doing v4-mapping
    if '.' in ip_str.split(':')[-1]:
        fill_to = 7
    else:
        fill_to = 8

    if len(hextet) > 1:
        sep = len(hextet[0].split(':')) + len(hextet[1].split(':'))
        new_ip = hextet[0].split(':')

        for __ in range(fill_to - sep):
            new_ip.append('0000')
        new_ip += hextet[1].split(':')

    else:
        new_ip = ip_str.split(':')

    # Now need to make sure every hextet is 4 lower case characters.
    # If a hextet is < 4 characters, we've got missing leading 0's.
    ret_ip = []
    for hextet in new_ip:
        ret_ip.append(('0' * (4 - len(hextet)) + hextet).lower())
    return ':'.join(ret_ip)


def _is_shorthand_ip(ip_str):
    """Determine if the address is shortened.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A boolean, True if the address is shortened.
    """
    if ip_str.count('::') == 1:
        return True
    if any(len(x) < 4 for x in ip_str.split(':')):
        return True
    return False
