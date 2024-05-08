# SPDX-License-Identifier: MIT

"""
This module offers access to standardized parameters that you can load using
:meth:`argon2.PasswordHasher.from_parameters()`. See the `source code
<https://github.com/hynek/argon2-cffi/blob/main/src/argon2/profiles.py>`_ for
concrete values and :doc:`parameters` for more information.

.. versionadded:: 21.2.0
"""

from __future__ import annotations

from ._utils import Parameters
from .low_level import Type


# FIRST RECOMMENDED option per RFC 9106.
RFC_9106_HIGH_MEMORY = Parameters(
    type=Type.ID,
    version=19,
    salt_len=16,
    hash_len=32,
    time_cost=1,
    memory_cost=2097152,  # 2 GiB
    parallelism=4,
)

# SECOND RECOMMENDED option per RFC 9106.
RFC_9106_LOW_MEMORY = Parameters(
    type=Type.ID,
    version=19,
    salt_len=16,
    hash_len=32,
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
)

# The pre-RFC defaults in argon2-cffi 18.2.0 - 21.1.0.
PRE_21_2 = Parameters(
    type=Type.ID,
    version=19,
    salt_len=16,
    hash_len=16,
    time_cost=2,
    memory_cost=102400,  # 100 MiB
    parallelism=8,
)

# Only for testing!
CHEAPEST = Parameters(
    type=Type.ID,
    version=19,
    salt_len=8,
    hash_len=4,
    time_cost=1,
    memory_cost=8,
    parallelism=1,
)
