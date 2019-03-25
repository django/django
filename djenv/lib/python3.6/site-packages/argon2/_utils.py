# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from six import iteritems

from .exceptions import InvalidHash
from .low_level import Type


NoneType = type(None)


def _check_types(**kw):
    """
    Check each ``name: (value, types)`` in *kw*.

    Returns a human-readable string of all violations or `None``.
    """
    errors = []
    for name, (value, types) in iteritems(kw):
        if not isinstance(value, types):
            if isinstance(types, tuple):
                types = ", or ".join(t.__name__ for t in types)
            else:
                types = types.__name__
            errors.append(
                "'{name}' must be a {type} (got {actual})".format(
                    name=name, type=types, actual=type(value).__name__
                )
            )

    if errors != []:
        return ", ".join(errors) + "."


def _encoded_str_len(l):
    """
    Compute how long a byte string of length *l* becomes if encoded to hex.
    """
    return (l << 2) / 3 + 2


def _decoded_str_len(l):
    """
    Compute how long an encoded string of length *l* becomes.
    """
    rem = l % 4

    if rem == 3:
        last_group_len = 2
    elif rem == 2:
        last_group_len = 1
    else:
        last_group_len = 0

    return l // 4 * 3 + last_group_len


class Parameters(object):
    """
    Argon2 hash parameters.

    See :doc:`parameters` on how to pick them.

    :ivar Type type: Hash type.
    :ivar int version: Argon2 version.
    :ivar int salt_len: Length of the salt in bytes.
    :ivar int hash_len: Length of the hash in bytes.
    :ivar int time_cost: Time cost in iterations.
    :ivar int memory_cost: Memory cost in kibibytes.
    :ivar int parallelism: Number of parallel threads.

    .. versionadded:: 18.2.0
    """

    __slots__ = [
        "type",
        "version",
        "salt_len",
        "hash_len",
        "time_cost",
        "memory_cost",
        "parallelism",
    ]

    def __init__(
        self,
        type,
        version,
        salt_len,
        hash_len,
        time_cost,
        memory_cost,
        parallelism,
    ):
        self.type = type
        self.version = version
        self.salt_len = salt_len
        self.hash_len = hash_len
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.parallelism = parallelism

    def __repr__(self):
        return (
            "<Parameters(type=%r, version=%d, hash_len=%d, salt_len=%d, "
            "time_cost=%d, memory_cost=%d, parallelelism=%d)>"
            % (
                self.type,
                self.version,
                self.hash_len,
                self.salt_len,
                self.time_cost,
                self.memory_cost,
                self.parallelism,
            )
        )

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return NotImplemented

        return (
            self.type,
            self.version,
            self.salt_len,
            self.hash_len,
            self.time_cost,
            self.memory_cost,
            self.parallelism,
        ) == (
            other.type,
            other.version,
            other.salt_len,
            other.hash_len,
            other.time_cost,
            other.memory_cost,
            other.parallelism,
        )

    def __ne__(self, other):
        if self.__class__ != other.__class__:
            return NotImplemented

        return not self.__eq__(other)


_NAME_TO_TYPE = {"argon2id": Type.ID, "argon2i": Type.I, "argon2d": Type.D}
_REQUIRED_KEYS = sorted(("v", "m", "t", "p"))


def extract_parameters(hash):
    """
    Extract parameters from an encoded *hash*.

    :param str params: An encoded Argon2 hash string.

    :rtype: Parameters

    .. versionadded:: 18.2.0
    """
    parts = hash.split("$")

    # Backwards compatibility for Argon v1.2 hashes
    if len(parts) == 5:
        parts.insert(2, "v=18")

    if len(parts) != 6:
        raise InvalidHash

    if parts[0] != "":
        raise InvalidHash

    try:
        type = _NAME_TO_TYPE[parts[1]]

        kvs = {
            k: int(v)
            for k, v in (
                s.split("=") for s in [parts[2]] + parts[3].split(",")
            )
        }
    except Exception:
        raise InvalidHash

    if sorted(kvs.keys()) != _REQUIRED_KEYS:
        raise InvalidHash

    return Parameters(
        type=type,
        salt_len=_decoded_str_len(len(parts[4])),
        hash_len=_decoded_str_len(len(parts[5])),
        version=kvs["v"],
        time_cost=kvs["t"],
        memory_cost=kvs["m"],
        parallelism=kvs["p"],
    )
