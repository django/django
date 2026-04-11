# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import sys
import timeit

from . import (
    DEFAULT_HASH_LENGTH,
    DEFAULT_MEMORY_COST,
    DEFAULT_PARALLELISM,
    DEFAULT_TIME_COST,
    PasswordHasher,
    profiles,
)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Argon2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n", type=int, default=100, help="Number of iterations to measure."
    )
    parser.add_argument(
        "-t", type=int, help="`time_cost`", default=DEFAULT_TIME_COST
    )
    parser.add_argument(
        "-m", type=int, help="`memory_cost`", default=DEFAULT_MEMORY_COST
    )
    parser.add_argument(
        "-p", type=int, help="`parallelism`", default=DEFAULT_PARALLELISM
    )
    parser.add_argument(
        "-l", type=int, help="`hash_length`", default=DEFAULT_HASH_LENGTH
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="A profile from `argon2.profiles. Takes precedence.",
        default=None,
    )

    args = parser.parse_args(argv[1:])

    password = b"secret"
    if args.profile:
        ph = PasswordHasher.from_parameters(
            getattr(profiles, args.profile.upper())
        )
    else:
        ph = PasswordHasher(
            time_cost=args.t,
            memory_cost=args.m,
            parallelism=args.p,
            hash_len=args.l,
        )
    hash = ph.hash(password)

    print(f"Running Argon2id {args.n} times with:")

    for name, value, units in [
        ("hash_len", ph.hash_len, "bytes"),
        ("memory_cost", ph.memory_cost, "KiB"),
        ("parallelism", ph.parallelism, "threads"),
        ("time_cost", ph.time_cost, "iterations"),
    ]:
        print(f"{name}: {value} {units}")

    print("\nMeasuring...")
    duration = timeit.timeit(
        f"ph.verify({hash!r}, {password!r})",
        setup=f"""\
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost={args.t!r},
    memory_cost={args.m!r},
    parallelism={args.p!r},
    hash_len={args.l!r},
)
gc.enable()""",
        number=args.n,
    )
    print(f"\n{duration / args.n * 1000:.1f}ms per password verification")


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv)
