"""Translates Mypy's output into GitHub's error/warning annotation syntax.

See: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions

This first is run with Mypy's output piped in, to collect messages in
mypy_annotate.dat. After all platforms run, we run this again, which prints the
messages in GitHub's format but with cross-platform failures deduplicated.
"""
from __future__ import annotations

import argparse
import pickle
import re
import sys

import attrs

# Example: 'package/filename.py:42:1:46:3: error: Type error here [code]'
report_re = re.compile(
    r"""
    ([^:]+):  # Filename (anything but ":")
    ([0-9]+):  # Line number (start)
    (?:([0-9]+):  # Optional column number
      (?:([0-9]+):([0-9]+):)?  # then also optionally, 2 more numbers for end columns
    )?
    \s*(error|warn|note):  # Kind, prefixed with space
    (.+)  # Message
    """,
    re.VERBOSE,
)

mypy_to_github = {
    "error": "error",
    "warn": "warning",
    "note": "notice",
}


@attrs.frozen(kw_only=True)
class Result:
    """Accumulated results, used as a dict key to deduplicate."""

    filename: str
    start_line: int
    kind: str
    message: str
    start_col: int | None = None
    end_line: int | None = None
    end_col: int | None = None


def process_line(line: str) -> Result | None:
    if match := report_re.fullmatch(line.rstrip()):
        filename, st_line, st_col, end_line, end_col, kind, message = match.groups()
        return Result(
            filename=filename,
            start_line=int(st_line),
            start_col=int(st_col) if st_col is not None else None,
            end_line=int(end_line) if end_line is not None else None,
            end_col=int(end_col) if end_col is not None else None,
            kind=mypy_to_github[kind],
            message=message,
        )
    else:
        return None


def export(results: dict[Result, list[str]]) -> None:
    """Display the collected results."""
    for res, platforms in results.items():
        print(f"::{res.kind} file={res.filename},line={res.start_line},", end="")
        if res.start_col is not None:
            print(f"col={res.start_col},", end="")
            if res.end_col is not None and res.end_line is not None:
                print(f"endLine={res.end_line},endColumn={res.end_col},", end="")
                message = f"({res.start_line}:{res.start_col} - {res.end_line}:{res.end_col}):{res.message}"
            else:
                message = f"({res.start_line}:{res.start_col}):{res.message}"
        else:
            message = f"{res.start_line}:{res.message}"
        print(f"title=Mypy-{'+'.join(platforms)}::{res.filename}:{message}")


def main(argv: list[str]) -> None:
    """Look for error messages, and convert the format."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dumpfile", help="File to write pickled messages to.", required=True
    )
    parser.add_argument(
        "--platform",
        help="OS name, if set Mypy should be piped to stdin.",
        default=None,
    )
    cmd_line = parser.parse_args(argv)

    results: dict[Result, list[str]]
    try:
        with open(cmd_line.dumpfile, "rb") as f:
            results = pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError):
        # If we fail to load, assume it's an old result.
        results = {}

    if cmd_line.platform is None:
        # Write out the results.
        export(results)
    else:
        platform: str = cmd_line.platform
        for line in sys.stdin:
            parsed = process_line(line)
            if parsed is not None:
                try:
                    results[parsed].append(platform)
                except KeyError:
                    results[parsed] = [platform]
            sys.stdout.write(line)
        with open(cmd_line.dumpfile, "wb") as f:
            pickle.dump(results, f)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
