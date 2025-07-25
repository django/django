import re
import sys
from collections import Counter
from os.path import abspath, dirname, splitext
from unittest import mock

from sphinxlint import rst
from sphinxlint.checkers import (
    _is_long_interpreted_text,
    _is_very_long_string_literal,
    _starts_with_anonymous_hyperlink,
    _starts_with_directive_or_hyperlink,
)
from sphinxlint.checkers import checker as sphinxlint_checker
from sphinxlint.sphinxlint import check_text
from sphinxlint.utils import PER_FILE_CACHES, hide_non_rst_blocks, po2rst


def django_check_file(filename, checkers, options=None):
    try:
        for checker in checkers:
            if ".rst" in checker.suffixes:
                checker.suffixes = (".txt",)
        ext = splitext(filename)[1]
        if not any(ext in checker.suffixes for checker in checkers):
            return Counter()
        try:
            with open(filename, encoding="utf-8") as f:
                text = f.read()
            if filename.endswith(".po"):
                text = po2rst(text)
        except OSError as err:
            return [f"{filename}: cannot open: {err}"]
        except UnicodeDecodeError as err:
            return [f"{filename}: cannot decode as UTF-8: {err}"]
        return check_text(filename, text, checkers, options)
    finally:
        for memoized_function in PER_FILE_CACHES:
            memoized_function.cache_clear()


_TOCTREE_DIRECTIVE_RE = re.compile(r"^ *.. toctree::")
_PARSED_LITERAL_DIRECTIVE_RE = re.compile(r"^ *.. parsed-literal::")
_IS_METHOD_RE = re.compile(r"^ *([\w.]+)\([\w,* ]+\)")


def is_multiline_block_to_exclude(line):
    if _TOCTREE_DIRECTIVE_RE.match(line):
        return True
    if _PARSED_LITERAL_DIRECTIVE_RE.match(line):
        return True
    return False


@sphinxlint_checker(".rst", ".po", enabled=False, rst_only=True)
def check_line_too_long_django(file, lines, options=None):
    """A modified version of Spinx-lint's line-too-long check."""
    # Ignore additional blocks from line length checks.
    with mock.patch(
        "sphinxlint.utils.is_multiline_non_rst_block", is_multiline_block_to_exclude
    ):
        lines = hide_non_rst_blocks(lines)

    table_rows = []
    for lno, line in enumerate(lines):
        # Beware, in `line` we have the trailing newline.
        if len(line) - 1 > options.max_line_length:

            # Sphinxlint default exceptions.
            if line.lstrip()[0] in "+|":
                continue  # ignore wide tables
            if _is_long_interpreted_text(line):
                continue  # ignore long interpreted text
            if _starts_with_directive_or_hyperlink(line):
                continue  # ignore directives and hyperlink targets
            if _starts_with_anonymous_hyperlink(line):
                continue  # ignore anonymous hyperlink targets
            if _is_very_long_string_literal(line):
                continue  # ignore a very long literal string

            # Additional exceptions
            try:
                # Ignore headings
                if len(set(lines[lno + 1].strip())) == 1 and len(line) == len(
                    lines[lno + 1]
                ):
                    continue
            except IndexError:
                # End of file
                continue
            if len(set(line.strip())) == 1 and len(line) == len(lines[lno - 1]):
                continue  # Ignore heading underline
            if lno in table_rows:
                continue  # Ignore lines in tables
            if len(set(line.strip())) == 2 and " " in line:
                # Ignore simple tables
                borders = [lno_ for lno_, line_ in enumerate(lines) if line == line_]
                table_rows.extend([n for n in range(min(borders), max(borders))])
                continue
            if rst.SEEMS_HYPERLINK_RE.search(line):
                continue  # Ignore long links not at the start of a line
            if match := _IS_METHOD_RE.match(line):
                # Ignore second definition of function signature.
                previous_line = lines[lno - 1]
                if previous_line.startswith(".. method:: ") and (
                    previous_line.find(match[1]) != -1
                ):
                    continue
            yield lno + 1, f"Line too long ({len(line) - 1}/{options.max_line_length})"


import sphinxlint  # noqa: E402

sphinxlint.check_file = django_check_file

from sphinxlint.cli import main  # noqa: E402

if __name__ == "__main__":
    directory = dirname(abspath(__file__))
    print(f"Running sphinxlint for: {directory}")

    sys.exit(
        main(
            [
                directory,
                "--jobs",
                "0",
                "--ignore",
                "_build",
                "--ignore",
                "_theme",
                "--ignore",
                "_ext",
                "--enable",
                "all",
                "--disable",
                "line-too-long",  # Disable sphinx-lint version
            ]
        )
    )
