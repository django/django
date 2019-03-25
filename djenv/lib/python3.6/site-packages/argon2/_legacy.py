"""
Legacy mid-level functions.
"""

from __future__ import absolute_import, division, print_function

import os

from ._password_hasher import (
    DEFAULT_HASH_LENGTH,
    DEFAULT_MEMORY_COST,
    DEFAULT_PARALLELISM,
    DEFAULT_RANDOM_SALT_LENGTH,
    DEFAULT_TIME_COST,
)
from .low_level import Type, hash_secret, hash_secret_raw, verify_secret


def hash_password(
    password,
    salt=None,
    time_cost=DEFAULT_TIME_COST,
    memory_cost=DEFAULT_MEMORY_COST,
    parallelism=DEFAULT_PARALLELISM,
    hash_len=DEFAULT_HASH_LENGTH,
    type=Type.I,
):
    """
    Legacy alias for :func:`hash_secret` with default parameters.

    .. deprecated:: 16.0.0
        Use :class:`argon2.PasswordHasher` for passwords.
    """
    if salt is None:
        salt = os.urandom(DEFAULT_RANDOM_SALT_LENGTH)
    return hash_secret(
        password, salt, time_cost, memory_cost, parallelism, hash_len, type
    )


def hash_password_raw(
    password,
    salt=None,
    time_cost=DEFAULT_TIME_COST,
    memory_cost=DEFAULT_MEMORY_COST,
    parallelism=DEFAULT_PARALLELISM,
    hash_len=DEFAULT_HASH_LENGTH,
    type=Type.I,
):
    """
    Legacy alias for :func:`hash_secret_raw` with default parameters.

    .. deprecated:: 16.0.0
        Use :class:`argon2.PasswordHasher` for passwords.
    """
    if salt is None:
        salt = os.urandom(DEFAULT_RANDOM_SALT_LENGTH)
    return hash_secret_raw(
        password, salt, time_cost, memory_cost, parallelism, hash_len, type
    )


def verify_password(hash, password, type=Type.I):
    """
    Legacy alias for :func:`verify_secret` with default parameters.

    .. deprecated:: 16.0.0
        Use :class:`argon2.PasswordHasher` for passwords.
    """
    return verify_secret(hash, password, type)
