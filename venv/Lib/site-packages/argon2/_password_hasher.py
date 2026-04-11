# SPDX-License-Identifier: MIT

from __future__ import annotations

import os

from typing import ClassVar, Literal

from ._utils import (
    Parameters,
    _check_types,
    extract_parameters,
    validate_params_for_platform,
)
from .exceptions import InvalidHashError
from .low_level import Type, hash_secret, verify_secret
from .profiles import get_default_parameters


default_params = get_default_parameters()

DEFAULT_RANDOM_SALT_LENGTH = default_params.salt_len
DEFAULT_HASH_LENGTH = default_params.hash_len
DEFAULT_TIME_COST = default_params.time_cost
DEFAULT_MEMORY_COST = default_params.memory_cost
DEFAULT_PARALLELISM = default_params.parallelism


def _ensure_bytes(s: bytes | str, encoding: str) -> bytes:
    """
    Ensure *s* is a bytes string.  Encode using *encoding* if it isn't.
    """
    if isinstance(s, bytes):
        return s
    return s.encode(encoding)


class PasswordHasher:
    r"""
    High level class to hash passwords with sensible defaults.

    Uses Argon2\ **id** by default and uses a random salt_ for hashing. But it
    can verify any type of Argon2 as long as the hash is correctly encoded.

    The reason for this being a class is both for convenience to carry
    parameters and to verify the parameters only *once*.  Any unnecessary
    slowdown when hashing is a tangible advantage for a brute-force attacker.

    Args:
        time_cost:
            Defines the amount of computation realized and therefore the
            execution time, given in number of iterations.

        memory_cost: Defines the memory usage, given in kibibytes_.

        parallelism:
            Defines the number of parallel threads (*changes* the resulting
            hash value).

        hash_len: Length of the hash in bytes.

        salt_len: Length of random salt to be generated for each password.

        encoding:
            The Argon2 C library expects bytes.  So if :meth:`hash` or
            :meth:`verify` are passed a ``str``, it will be encoded using this
            encoding.

        type:
            Argon2 type to use.  Only change for interoperability with legacy
            systems.

    .. versionadded:: 16.0.0
    .. versionchanged:: 18.2.0
       Switch from Argon2i to Argon2id based on the recommendation by the
       current RFC draft. See also :doc:`parameters`.
    .. versionchanged:: 18.2.0
       Changed default *memory_cost* to 100 MiB and default *parallelism* to 8.
    .. versionchanged:: 18.2.0 ``verify`` now will determine the type of hash.
    .. versionchanged:: 18.3.0 The Argon2 type is configurable now.
    .. versionadded:: 21.2.0 :meth:`from_parameters`
    .. versionchanged:: 21.2.0
       Changed defaults to :data:`argon2.profiles.RFC_9106_LOW_MEMORY`.

    .. _salt: https://en.wikipedia.org/wiki/Salt_(cryptography)
    .. _kibibytes: https://en.wikipedia.org/wiki/Binary_prefix#kibi
    """

    __slots__ = ["_parameters", "encoding"]

    _parameters: Parameters
    encoding: str

    def __init__(
        self,
        time_cost: int = DEFAULT_TIME_COST,
        memory_cost: int = DEFAULT_MEMORY_COST,
        parallelism: int = DEFAULT_PARALLELISM,
        hash_len: int = DEFAULT_HASH_LENGTH,
        salt_len: int = DEFAULT_RANDOM_SALT_LENGTH,
        encoding: str = "utf-8",
        type: Type = Type.ID,
    ):
        e = _check_types(
            time_cost=(time_cost, int),
            memory_cost=(memory_cost, int),
            parallelism=(parallelism, int),
            hash_len=(hash_len, int),
            salt_len=(salt_len, int),
            encoding=(encoding, str),
            type=(type, Type),
        )
        if e:
            raise TypeError(e)

        params = Parameters(
            type=type,
            version=19,
            salt_len=salt_len,
            hash_len=hash_len,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

        validate_params_for_platform(params)

        # Cache a Parameters object for check_needs_rehash.
        self._parameters = params
        self.encoding = encoding

    @classmethod
    def from_parameters(cls, params: Parameters) -> PasswordHasher:
        """
        Construct a `PasswordHasher` from *params*.

        Returns:
            A `PasswordHasher` instance with the parameters from *params*.

        .. versionadded:: 21.2.0
        """

        return cls(
            time_cost=params.time_cost,
            memory_cost=params.memory_cost,
            parallelism=params.parallelism,
            hash_len=params.hash_len,
            salt_len=params.salt_len,
            type=params.type,
        )

    @property
    def time_cost(self) -> int:
        return self._parameters.time_cost

    @property
    def memory_cost(self) -> int:
        return self._parameters.memory_cost

    @property
    def parallelism(self) -> int:
        return self._parameters.parallelism

    @property
    def hash_len(self) -> int:
        return self._parameters.hash_len

    @property
    def salt_len(self) -> int:
        return self._parameters.salt_len

    @property
    def type(self) -> Type:
        return self._parameters.type

    def hash(self, password: str | bytes, *, salt: bytes | None = None) -> str:
        """
        Hash *password* and return an encoded hash.

        Args:
            password: Password to hash.

            salt:
                If None, a random salt is securely created.

                .. danger::

                    You should **not** pass a salt unless you really know what
                    you are doing.

        Raises:
            argon2.exceptions.HashingError: If hashing fails.

        Returns:
            Hashed *password*.

        .. versionadded:: 23.1.0 *salt* parameter
        """
        return hash_secret(
            secret=_ensure_bytes(password, self.encoding),
            salt=salt or os.urandom(self.salt_len),
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=self.hash_len,
            type=self.type,
        ).decode("ascii")

    _header_to_type: ClassVar[dict[bytes, Type]] = {
        b"$argon2i$": Type.I,
        b"$argon2d$": Type.D,
        b"$argon2id": Type.ID,
    }

    def verify(
        self, hash: str | bytes, password: str | bytes
    ) -> Literal[True]:
        """
        Verify that *password* matches *hash*.

        .. warning::

            It is assumed that the caller is in full control of the hash.  No
            other parsing than the determination of the hash type is done by
            *argon2-cffi*.

        Args:
            hash: An encoded hash as returned from :meth:`PasswordHasher.hash`.

            password: The password to verify.

        Raises:
            argon2.exceptions.VerifyMismatchError:
                If verification fails because *hash* is not valid for
                *password*.

            argon2.exceptions.VerificationError:
                If verification fails for other reasons.

            argon2.exceptions.InvalidHashError:
                If *hash* is so clearly invalid, that it couldn't be passed to
                Argon2.

        Returns:
            ``True`` on success, otherwise an exception is raised.

        .. versionchanged:: 16.1.0
            Raise :exc:`~argon2.exceptions.VerifyMismatchError` on mismatches
            instead of its more generic superclass.
        .. versionadded:: 18.2.0 Hash type agility.
        """
        hash = _ensure_bytes(hash, "ascii")
        try:
            hash_type = self._header_to_type[hash[:9]]
        except LookupError:
            raise InvalidHashError from None

        return verify_secret(
            hash, _ensure_bytes(password, self.encoding), hash_type
        )

    def check_needs_rehash(self, hash: str | bytes) -> bool:
        """
        Check whether *hash* was created using the instance's parameters.

        Whenever your Argon2 parameters -- or *argon2-cffi*'s defaults! --
        change, you should rehash your passwords at the next opportunity.  The
        common approach is to do that whenever a user logs in, since that
        should be the only time when you have access to the cleartext
        password.

        Therefore it's best practice to check -- and if necessary rehash --
        passwords after each successful authentication.

        Args:
            hash: An encoded Argon2 password hash.

        Returns:
            Whether *hash* was created using the instance's parameters.

        .. versionadded:: 18.2.0
        .. versionchanged:: 24.1.0 Accepts bytes for *hash*.
        """
        if isinstance(hash, bytes):
            hash = hash.decode("ascii")

        return self._parameters != extract_parameters(hash)
