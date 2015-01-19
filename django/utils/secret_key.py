"""
Secret key related utility functions.
"""
from __future__ import unicode_literals
from django.utils.crypto import get_random_string

import os


def generate_secret_key():
    """
    Returns a secure randomly generated secret key.

    """
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(50, chars)


def create_secret_key_file(path):
    """
    Writes a secret key out to a file.
    """
    # Open file for write only
    # Fail if file already exists
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a
    # symlink that we follow and insecurely open a file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd = os.open(path, flags, mode=0o600)

    try:
        with os.fdopen(fd, 'w') as file:
            file.write(generate_secret_key())
    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise
