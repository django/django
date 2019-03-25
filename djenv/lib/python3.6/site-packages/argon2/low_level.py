# -*- coding: utf-8 -*-
"""
Low-level functions if you want to build your own higher level abstractions.

.. warning::
    This is a "Hazardous Materials" module.  You should **ONLY** use it if
    you're 100% absolutely sure that you know what you’re doing because this
    module is full of land mines, dragons, and dinosaurs with laser guns.
"""

from __future__ import absolute_import, division, print_function

from enum import Enum

from six import PY3

from ._ffi import ffi, lib
from .exceptions import HashingError, VerificationError, VerifyMismatchError


__all__ = [
    "ARGON2_VERSION",
    "Type",
    "ffi",
    "hash_secret",
    "hash_secret_raw",
    "verify_secret",
]

ARGON2_VERSION = lib.ARGON2_VERSION_NUMBER
"""
The latest version of the Argon2 algorithm that is supported (and used by
default).

.. versionadded:: 16.1.0
"""


class Type(Enum):
    """
    Enum of Argon2 variants.

    Please see :doc:`parameters` on how to pick one.
    """

    D = lib.Argon2_d
    r"""
    Argon2\ **d** is faster and uses data-depending memory access, which makes
    it less suitable for hashing secrets and more suitable for cryptocurrencies
    and applications with no threats from side-channel timing attacks.
    """
    I = lib.Argon2_i
    r"""
    Argon2\ **i** uses data-independent memory access.  Argon2i is slower as
    it makes more passes over the memory to protect from tradeoff attacks.
    """
    ID = lib.Argon2_id
    r"""
    Argon2\ **id** is a hybrid of Argon2i and Argon2d, using a combination of
    data-depending and data-independent memory accesses, which gives some of
    Argon2i's resistance to side-channel cache timing attacks and much of
    Argon2d's resistance to GPU cracking attacks.

    That makes it the preferred type for password hashing and password-based
    key derivation.

    .. versionadded:: 16.3.0
    """


def hash_secret(
    secret,
    salt,
    time_cost,
    memory_cost,
    parallelism,
    hash_len,
    type,
    version=ARGON2_VERSION,
):
    """
    Hash *secret* and return an **encoded** hash.

    An encoded hash can be directly passed into :func:`verify_secret` as it
    contains all parameters and the salt.

    :param bytes secret: Secret to hash.
    :param bytes salt: A salt_.  Should be random and different for each
        secret.
    :param Type type: Which Argon2 variant to use.
    :param int version: Which Argon2 version to use.

    For an explanation of the Argon2 parameters see :class:`PasswordHasher`.

    :rtype: bytes

    :raises argon2.exceptions.HashingError: If hashing fails.

    .. versionadded:: 16.0.0

    .. _salt: https://en.wikipedia.org/wiki/Salt_(cryptography)
    .. _kibibytes: https://en.wikipedia.org/wiki/Binary_prefix#kibi
    """
    size = (
        lib.argon2_encodedlen(
            time_cost,
            memory_cost,
            parallelism,
            len(salt),
            hash_len,
            type.value,
        )
        + 1
    )
    buf = ffi.new("char[]", size)
    rv = lib.argon2_hash(
        time_cost,
        memory_cost,
        parallelism,
        ffi.new("uint8_t[]", secret),
        len(secret),
        ffi.new("uint8_t[]", salt),
        len(salt),
        ffi.NULL,
        hash_len,
        buf,
        size,
        type.value,
        version,
    )
    if rv != lib.ARGON2_OK:
        raise HashingError(error_to_str(rv))

    return ffi.string(buf)


def hash_secret_raw(
    secret,
    salt,
    time_cost,
    memory_cost,
    parallelism,
    hash_len,
    type,
    version=ARGON2_VERSION,
):
    """
    Hash *password* and return a **raw** hash.

    This function takes the same parameters as :func:`hash_secret`.

    .. versionadded:: 16.0.0
    """
    buf = ffi.new("uint8_t[]", hash_len)

    rv = lib.argon2_hash(
        time_cost,
        memory_cost,
        parallelism,
        ffi.new("uint8_t[]", secret),
        len(secret),
        ffi.new("uint8_t[]", salt),
        len(salt),
        buf,
        hash_len,
        ffi.NULL,
        0,
        type.value,
        version,
    )
    if rv != lib.ARGON2_OK:
        raise HashingError(error_to_str(rv))

    return bytes(ffi.buffer(buf, hash_len))


def verify_secret(hash, secret, type):
    """
    Verify whether *secret* is correct for *hash* of *type*.

    :param bytes hash: An encoded Argon2 hash as returned by
        :func:`hash_secret`.
    :param bytes secret: The secret to verify whether it matches the one
        in *hash*.
    :param Type type: Type for *hash*.

    :raises argon2.exceptions.VerifyMismatchError: If verification fails
        because *hash* is not valid for *secret* of *type*.
    :raises argon2.exceptions.VerificationError: If verification fails for
        other reasons.

    :return: ``True`` on success, raise
        :exc:`~argon2.exceptions.VerificationError` otherwise.
    :rtype: bool

    .. versionadded:: 16.0.0
    .. versionchanged:: 16.1.0
        Raise :exc:`~argon2.exceptions.VerifyMismatchError` on mismatches
        instead of its more generic superclass.
    """
    rv = lib.argon2_verify(
        ffi.new("char[]", hash),
        ffi.new("uint8_t[]", secret),
        len(secret),
        type.value,
    )
    if rv == lib.ARGON2_OK:
        return True
    elif rv == lib.ARGON2_VERIFY_MISMATCH:
        raise VerifyMismatchError(error_to_str(rv))
    else:
        raise VerificationError(error_to_str(rv))


def core(context, type):
    """
    Direct binding to the ``argon2_ctx`` function.

    .. warning::
        This is a strictly advanced function working on raw C data structures.
        Both Argon2's and ``argon2_cffi``'s higher-level bindings do a lot of
        sanity checks and housekeeping work that *you* are now responsible for
        (e.g. clearing buffers). The structure of the *context* object can,
        has, and will change with *any* release!

        Use at your own peril; ``argon2_cffi`` does *not* use this binding
        itself.

    :param context: A CFFI Argon2 context object (i.e. an ``struct
        Argon2_Context``/``argon2_context``).
    :param int type: Which Argon2 variant to use.  You can use the ``value``
        field of :class:`Type`'s fields.

    :rtype: int
    :return: An Argon2 error code.  Can be transformed into a string using
        :func:`error_to_str`.

    .. versionadded:: 16.0.0
    """
    return lib.argon2_ctx(context, type)


def error_to_str(error):
    """
    Convert an Argon2 error code into a native string.

    :param int error: An Argon2 error code as returned by :func:`core`.

    :rtype: str

    .. versionadded:: 16.0.0
    """
    msg = ffi.string(lib.argon2_error_message(error))
    if PY3:
        msg = msg.decode("ascii")
    return msg
