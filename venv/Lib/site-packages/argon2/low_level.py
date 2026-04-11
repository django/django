# SPDX-License-Identifier: MIT

"""
Low-level functions if you want to build your own higher level abstractions.

.. warning::
    This is a "Hazardous Materials" module.  You should **ONLY** use it if
    you're 100% absolutely sure that you know what you're doing because this
    module is full of land mines, dragons, and dinosaurs with laser guns.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from _argon2_cffi_bindings import ffi, lib

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
    I = lib.Argon2_i  # noqa: E741
    ID = lib.Argon2_id


def hash_secret(
    secret: bytes,
    salt: bytes,
    time_cost: int,
    memory_cost: int,
    parallelism: int,
    hash_len: int,
    type: Type,
    version: int = ARGON2_VERSION,
) -> bytes:
    """
    Hash *secret* and return an **encoded** hash.

    An encoded hash can be directly passed into :func:`verify_secret` as it
    contains all parameters and the salt.

    Args:
        secret: Secret to hash.

        salt: A salt_. Should be random and different for each secret.

        type: Which Argon2 variant to use.

        version: Which Argon2 version to use.

    For an explanation of the Argon2 parameters see
    :class:`argon2.PasswordHasher`.

    Returns:
        An encoded Argon2 hash.

    Raises:
        argon2.exceptions.HashingError: If hashing fails.

    .. versionadded:: 16.0.0

    .. _salt: https://en.wikipedia.org/wiki/Salt_(cryptography)
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

    return ffi.string(buf)  # type: ignore[no-any-return]


def hash_secret_raw(
    secret: bytes,
    salt: bytes,
    time_cost: int,
    memory_cost: int,
    parallelism: int,
    hash_len: int,
    type: Type,
    version: int = ARGON2_VERSION,
) -> bytes:
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


def verify_secret(hash: bytes, secret: bytes, type: Type) -> Literal[True]:
    """
    Verify whether *secret* is correct for *hash* of *type*.

    Args:
        hash:
            An encoded Argon2 hash as returned by :func:`hash_secret`.

        secret:
            The secret to verify whether it matches the one in *hash*.

        type: Type for *hash*.

    Raises:
        argon2.exceptions.VerifyMismatchError:
            If verification fails because *hash* is not valid for *secret* of
            *type*.

        argon2.exceptions.VerificationError:
            If verification fails for other reasons.

    Returns:
        ``True`` on success, raise :exc:`~argon2.exceptions.VerificationError`
        otherwise.

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

    if rv == lib.ARGON2_VERIFY_MISMATCH:
        raise VerifyMismatchError(error_to_str(rv))

    raise VerificationError(error_to_str(rv))


def core(context: Any, type: int) -> int:
    """
    Direct binding to the ``argon2_ctx`` function.

    .. warning::
        This is a strictly advanced function working on raw C data structures.
        Both Argon2's and *argon2-cffi*'s higher-level bindings do a lot of
        sanity checks and housekeeping work that *you* are now responsible for
        (e.g. clearing buffers). The structure of the *context* object can,
        has, and will change with *any* release!

        Use at your own peril; *argon2-cffi* does *not* use this binding
        itself.

    Args:
        context:
            A CFFI Argon2 context object (i.e. an ``struct Argon2_Context`` /
            ``argon2_context``).

        type:
            Which Argon2 variant to use.  You can use the ``value`` field of
            :class:`Type`'s fields.

    Returns:
        An Argon2 error code.  Can be transformed into a string using
        :func:`error_to_str`.

    .. versionadded:: 16.0.0
    """
    return lib.argon2_ctx(context, type)  # type: ignore[no-any-return]


def error_to_str(error: int) -> str:
    """
    Convert an Argon2 error code into a native string.

    Args:
        error: An Argon2 error code as returned by :func:`core`.

    Returns:
        A human-readable string describing the error.

    .. versionadded:: 16.0.0
    """
    return ffi.string(lib.argon2_error_message(error)).decode("ascii")  # type: ignore[no-any-return]
