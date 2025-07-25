import re
import sys
from collections import Counter
from os.path import abspath, dirname, splitext
from unittest import mock

from sphinxlint.checkers import (
    _is_long_interpreted_text,
    _is_very_long_string_literal,
    _starts_with_anonymous_hyperlink,
    _starts_with_directive_or_hyperlink,
)
from sphinxlint.checkers import checker as sphinxlint_checker
from sphinxlint.sphinxlint import check_text
from sphinxlint.utils import PER_FILE_CACHES, hide_non_rst_blocks


def django_check_file(filename, checkers, options=None):
    try:
        for checker in checkers:
            # Django docs use ".txt" for docs file extension.
            if ".rst" in checker.suffixes:
                checker.suffixes = (".txt",)
        ext = splitext(filename)[1]
        if not any(ext in checker.suffixes for checker in checkers):
            return Counter()
        try:
            with open(filename, encoding="utf-8") as f:
                text = f.read()
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
_IS_METHOD_RE = re.compile(r"^ *([\w.]+)\([\w ,*]*\)\s*$")
# https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
# Use two trailing underscores when embedding the URL. Technically, a single
# underscore works as well, but that would create a named reference instead of
# an anonymous one. Named references typically do not have a benefit when the
# URL is embedded. Moreover, they have the disadvantage that you must make sure
# that you do not use the same “Link text” for another link in your document.
_HYPERLINK_DANGLING_RE = re.compile(r"^\s*<https?://[^>]+>`__?[\.,;]?$")


@sphinxlint_checker(".rst", enabled=False, rst_only=True)
def check_line_too_long_django(file, lines, options=None):
    """A modified version of Sphinx-lint's line-too-long check.

    Original:
    https://github.com/sphinx-contrib/sphinx-lint/blob/main/sphinxlint/checkers.py
    """

    def is_multiline_block_to_exclude(line):
        return _TOCTREE_DIRECTIVE_RE.match(line) or _PARSED_LITERAL_DIRECTIVE_RE.match(
            line
        )

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
            if _HYPERLINK_DANGLING_RE.match(line):
                continue  # Ignore dangling long links inside a ``_ ref.
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
    params = sys.argv[1:] if len(sys.argv) > 1 else []

    print(f"Running sphinxlint for: {directory} {params=}")

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
                "--max-line-length",
                "79",
                *params,
            ]
        )
    )
