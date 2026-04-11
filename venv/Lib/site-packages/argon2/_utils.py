# SPDX-License-Identifier: MIT

from __future__ import annotations

import platform
import sys

from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidHashError, UnsupportedParametersError
from .low_level import Type


NoneType = type(None)


def _check_types(**kw: Any) -> str | None:
    """
    Check each ``name: (value, types)`` in *kw*.

    Returns a human-readable string of all violations or `None``.
    """
    errors = []
    for name, (value, types) in kw.items():
        if not isinstance(value, types):
            if isinstance(types, tuple):
                types = ", or ".join(t.__name__ for t in types)
            else:
                types = types.__name__
            errors.append(
                f"'{name}' must be a {types} (got {type(value).__name__})"
            )

    if errors != []:
        return ", ".join(errors) + "."

    return None


def _is_wasm() -> bool:
    return sys.platform == "emscripten" or platform.machine() in [
        "wasm32",
        "wasm64",
    ]


def _decoded_str_len(length: int) -> int:
    """
    Compute how long an encoded string of length *l* becomes.
    """
    rem = length % 4

    if rem == 3:
        last_group_len = 2
    elif rem == 2:
        last_group_len = 1
    else:
        last_group_len = 0

    return length // 4 * 3 + last_group_len


@dataclass
class Parameters:
    """
    Argon2 hash parameters.

    See :doc:`parameters` on how to pick them.

    Attributes:
        type: Hash type.

        version: Argon2 version.

        salt_len: Length of the salt in bytes.

        hash_len: Length of the hash in bytes.

        time_cost: Time cost in iterations.

        memory_cost: Memory cost in kibibytes.

        parallelism: Number of parallel threads.

    .. versionadded:: 18.2.0
    """

    type: Type
    version: int
    salt_len: int
    hash_len: int
    time_cost: int
    memory_cost: int
    parallelism: int

    __slots__ = (
        "hash_len",
        "memory_cost",
        "parallelism",
        "salt_len",
        "time_cost",
        "type",
        "version",
    )


_NAME_TO_TYPE = {"argon2id": Type.ID, "argon2i": Type.I, "argon2d": Type.D}
_REQUIRED_KEYS = sorted(("v", "m", "t", "p"))


def extract_parameters(hash: str) -> Parameters:
    """
    Extract parameters from an encoded *hash*.

    Args:
        hash: An encoded Argon2 hash string.

    Returns:
        The parameters used to create the hash.

    .. versionadded:: 18.2.0
    """
    parts = hash.split("$")

    # Backwards compatibility for Argon v1.2 hashes
    if len(parts) == 5:
        parts.insert(2, "v=18")

    if len(parts) != 6:
        raise InvalidHashError

    if parts[0]:
        raise InvalidHashError

    try:
        type = _NAME_TO_TYPE[parts[1]]

        kvs = {
            k: int(v)
            for k, v in (
                s.split("=") for s in [parts[2], *parts[3].split(",")]
            )
        }
    except Exception:  # noqa: BLE001
        raise InvalidHashError from None

    if sorted(kvs.keys()) != _REQUIRED_KEYS:
        raise InvalidHashError

    return Parameters(
        type=type,
        salt_len=_decoded_str_len(len(parts[4])),
        hash_len=_decoded_str_len(len(parts[5])),
        version=kvs["v"],
        time_cost=kvs["t"],
        memory_cost=kvs["m"],
        parallelism=kvs["p"],
    )


def validate_params_for_platform(params: Parameters) -> None:
    """
    Validate *params* against current platform.

    Args:
        params: Parameters to be validated

    Returns:
       None
    """
    if _is_wasm() and params.parallelism != 1:
        msg = "In WebAssembly environments `parallelism` must be 1."
        raise UnsupportedParametersError(msg)
