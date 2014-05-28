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


def create_secret_key_file(path=None):
    """
    Writes a secret key out to a file.
    """
    key = generate_secret_key()
    if path is None:
        path = '.secret_key'

    with open(path, "w") as file:
        file.write(key)
    os.chmod(path, 0600)

    return key


def read_or_create_secret_key_file(path=None):
    """
    Attempts to read the secret key from a file.

    If it fails to open the file None will be returned.
    """
    if path is None:
        path = '.secret_key'

    try:
        with open(path, "r") as file:
            return file.read()
    except IOError:
        return create_secret_key_file(path)
