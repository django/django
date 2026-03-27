"""Module containing our file processor that tokenizes a file for checks."""
from __future__ import annotations

import argparse
import ast
import functools
import logging
import tokenize
from collections.abc import Generator
from typing import Any

from flake8 import defaults
from flake8 import utils
from flake8._compat import FSTRING_END
from flake8._compat import FSTRING_MIDDLE
from flake8._compat import TSTRING_END
from flake8._compat import TSTRING_MIDDLE
from flake8.plugins.finder import LoadedPlugin

LOG = logging.getLogger(__name__)
NEWLINE = frozenset([tokenize.NL, tokenize.NEWLINE])

SKIP_TOKENS = frozenset(
    [tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT]
)

_LogicalMapping = list[tuple[int, tuple[int, int]]]
_Logical = tuple[list[str], list[str], _LogicalMapping]


class FileProcessor:
    """Processes a file and holds state.

    This processes a file by generating tokens, logical and physical lines,
    and AST trees. This also provides a way of passing state about the file
    to checks expecting that state. Any public attribute on this object can
    be requested by a plugin. The known public attributes are:

    - :attr:`blank_before`
    - :attr:`blank_lines`
    - :attr:`checker_state`
    - :attr:`indent_char`
    - :attr:`indent_level`
    - :attr:`line_number`
    - :attr:`logical_line`
    - :attr:`max_line_length`
    - :attr:`max_doc_length`
    - :attr:`multiline`
    - :attr:`noqa`
    - :attr:`previous_indent_level`
    - :attr:`previous_logical`
    - :attr:`previous_unindented_logical_line`
    - :attr:`tokens`
    - :attr:`file_tokens`
    - :attr:`total_lines`
    - :attr:`verbose`
    """

    #: always ``False``, included for compatibility
    noqa = False

    def __init__(
        self,
        filename: str,
        options: argparse.Namespace,
        lines: list[str] | None = None,
    ) -> None:
        """Initialize our file processor.

        :param filename: Name of the file to process
        """
        self.options = options
        self.filename = filename
        self.lines = lines if lines is not None else self.read_lines()
        self.strip_utf_bom()

        # Defaults for public attributes
        #: Number of preceding blank lines
        self.blank_before = 0
        #: Number of blank lines
        self.blank_lines = 0
        #: Checker states for each plugin?
        self._checker_states: dict[str, dict[Any, Any]] = {}
        #: Current checker state
        self.checker_state: dict[Any, Any] = {}
        #: User provided option for hang closing
        self.hang_closing = options.hang_closing
        #: Character used for indentation
        self.indent_char: str | None = None
        #: Current level of indentation
        self.indent_level = 0
        #: Number of spaces used for indentation
        self.indent_size = options.indent_size
        #: Line number in the file
        self.line_number = 0
        #: Current logical line
        self.logical_line = ""
        #: Maximum line length as configured by the user
        self.max_line_length = options.max_line_length
        #: Maximum docstring / comment line length as configured by the user
        self.max_doc_length = options.max_doc_length
        #: Whether the current physical line is multiline
        self.multiline = False
        #: Previous level of indentation
        self.previous_indent_level = 0
        #: Previous logical line
        self.previous_logical = ""
        #: Previous unindented (i.e. top-level) logical line
        self.previous_unindented_logical_line = ""
        #: Current set of tokens
        self.tokens: list[tokenize.TokenInfo] = []
        #: Total number of lines in the file
        self.total_lines = len(self.lines)
        #: Verbosity level of Flake8
        self.verbose = options.verbose
        #: Statistics dictionary
        self.statistics = {"logical lines": 0}
        self._fstring_start = self._tstring_start = -1

    @functools.cached_property
    def file_tokens(self) -> list[tokenize.TokenInfo]:
        """Return the complete set of tokens for a file."""
        line_iter = iter(self.lines)
        return list(tokenize.generate_tokens(lambda: next(line_iter)))

    def fstring_start(self, lineno: int) -> None:  # pragma: >=3.12 cover
        """Signal the beginning of an fstring."""
        self._fstring_start = lineno

    def tstring_start(self, lineno: int) -> None:  # pragma: >=3.14 cover
        """Signal the beginning of an tstring."""
        self._tstring_start = lineno

    def multiline_string(self, token: tokenize.TokenInfo) -> Generator[str]:
        """Iterate through the lines of a multiline string."""
        if token.type == FSTRING_END:  # pragma: >=3.12 cover
            start = self._fstring_start
        elif token.type == TSTRING_END:  # pragma: >=3.14 cover
            start = self._tstring_start
        else:
            start = token.start[0]

        self.multiline = True
        self.line_number = start
        # intentionally don't include the last line, that line will be
        # terminated later by a future end-of-line
        for _ in range(start, token.end[0]):
            yield self.lines[self.line_number - 1]
            self.line_number += 1
        self.multiline = False

    def reset_blank_before(self) -> None:
        """Reset the blank_before attribute to zero."""
        self.blank_before = 0

    def delete_first_token(self) -> None:
        """Delete the first token in the list of tokens."""
        del self.tokens[0]

    def visited_new_blank_line(self) -> None:
        """Note that we visited a new blank line."""
        self.blank_lines += 1

    def update_state(self, mapping: _LogicalMapping) -> None:
        """Update the indent level based on the logical line mapping."""
        (start_row, start_col) = mapping[0][1]
        start_line = self.lines[start_row - 1]
        self.indent_level = expand_indent(start_line[:start_col])
        if self.blank_before < self.blank_lines:
            self.blank_before = self.blank_lines

    def update_checker_state_for(self, plugin: LoadedPlugin) -> None:
        """Update the checker_state attribute for the plugin."""
        if "checker_state" in plugin.parameters:
            self.checker_state = self._checker_states.setdefault(
                plugin.entry_name, {}
            )

    def next_logical_line(self) -> None:
        """Record the previous logical line.

        This also resets the tokens list and the blank_lines count.
        """
        if self.logical_line:
            self.previous_indent_level = self.indent_level
            self.previous_logical = self.logical_line
            if not self.indent_level:
                self.previous_unindented_logical_line = self.logical_line
        self.blank_lines = 0
        self.tokens = []

    def build_logical_line_tokens(self) -> _Logical:  # noqa: C901
        """Build the mapping, comments, and logical line lists."""
        logical = []
        comments = []
        mapping: _LogicalMapping = []
        length = 0
        previous_row = previous_column = None
        for token_type, text, start, end, line in self.tokens:
            if token_type in SKIP_TOKENS:
                continue
            if not mapping:
                mapping = [(0, start)]
            if token_type == tokenize.COMMENT:
                comments.append(text)
                continue
            if token_type == tokenize.STRING:
                text = mutate_string(text)
            elif token_type in {
                FSTRING_MIDDLE,
                TSTRING_MIDDLE,
            }:  # pragma: >=3.12 cover  # noqa: E501
                # A curly brace in an FSTRING_MIDDLE token must be an escaped
                # curly brace. Both 'text' and 'end' will account for the
                # escaped version of the token (i.e. a single brace) rather
                # than the raw double brace version, so we must counteract this
                brace_offset = text.count("{") + text.count("}")
                text = "x" * (len(text) + brace_offset)
                end = (end[0], end[1] + brace_offset)
            if previous_row is not None and previous_column is not None:
                (start_row, start_column) = start
                if previous_row != start_row:
                    row_index = previous_row - 1
                    column_index = previous_column - 1
                    previous_text = self.lines[row_index][column_index]
                    if previous_text == "," or (
                        previous_text not in "{[(" and text not in "}])"
                    ):
                        text = f" {text}"
                elif previous_column != start_column:
                    text = line[previous_column:start_column] + text
            logical.append(text)
            length += len(text)
            mapping.append((length, end))
            (previous_row, previous_column) = end
        return comments, logical, mapping

    def build_ast(self) -> ast.AST:
        """Build an abstract syntax tree from the list of lines."""
        return ast.parse("".join(self.lines))

    def build_logical_line(self) -> tuple[str, str, _LogicalMapping]:
        """Build a logical line from the current tokens list."""
        comments, logical, mapping_list = self.build_logical_line_tokens()
        joined_comments = "".join(comments)
        self.logical_line = "".join(logical)
        self.statistics["logical lines"] += 1
        return joined_comments, self.logical_line, mapping_list

    def keyword_arguments_for(
        self,
        parameters: dict[str, bool],
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate the keyword arguments for a list of parameters."""
        ret = {}
        for param, required in parameters.items():
            if param in arguments:
                continue
            try:
                ret[param] = getattr(self, param)
            except AttributeError:
                if required:
                    raise
                else:
                    LOG.warning(
                        'Plugin requested optional parameter "%s" '
                        "but this is not an available parameter.",
                        param,
                    )
        return ret

    def generate_tokens(self) -> Generator[tokenize.TokenInfo]:
        """Tokenize the file and yield the tokens."""
        for token in tokenize.generate_tokens(self.next_line):
            if token[2][0] > self.total_lines:
                break
            self.tokens.append(token)
            yield token

    def _noqa_line_range(self, min_line: int, max_line: int) -> dict[int, str]:
        line_range = range(min_line, max_line + 1)
        joined = "".join(self.lines[min_line - 1 : max_line])
        return dict.fromkeys(line_range, joined)

    @functools.cached_property
    def _noqa_line_mapping(self) -> dict[int, str]:
        """Map from line number to the line we'll search for `noqa` in."""
        try:
            file_tokens = self.file_tokens
        except (tokenize.TokenError, SyntaxError):
            # if we failed to parse the file tokens, we'll always fail in
            # the future, so set this so the code does not try again
            return {}
        else:
            ret = {}

            min_line = len(self.lines) + 2
            max_line = -1
            for tp, _, (s_line, _), (e_line, _), _ in file_tokens:
                if tp == tokenize.ENDMARKER or tp == tokenize.DEDENT:
                    continue

                min_line = min(min_line, s_line)
                max_line = max(max_line, e_line)

                if tp in (tokenize.NL, tokenize.NEWLINE):
                    ret.update(self._noqa_line_range(min_line, max_line))

                    min_line = len(self.lines) + 2
                    max_line = -1

            return ret

    def noqa_line_for(self, line_number: int) -> str | None:
        """Retrieve the line which will be used to determine noqa."""
        # NOTE(sigmavirus24): Some plugins choose to report errors for empty
        # files on Line 1. In those cases, we shouldn't bother trying to
        # retrieve a physical line (since none exist).
        return self._noqa_line_mapping.get(line_number)

    def next_line(self) -> str:
        """Get the next line from the list."""
        if self.line_number >= self.total_lines:
            return ""
        line = self.lines[self.line_number]
        self.line_number += 1
        if self.indent_char is None and line[:1] in defaults.WHITESPACE:
            self.indent_char = line[0]
        return line

    def read_lines(self) -> list[str]:
        """Read the lines for this file checker."""
        if self.filename == "-":
            self.filename = self.options.stdin_display_name or "stdin"
            lines = self.read_lines_from_stdin()
        else:
            lines = self.read_lines_from_filename()
        return lines

    def read_lines_from_filename(self) -> list[str]:
        """Read the lines for a file."""
        try:
            with tokenize.open(self.filename) as fd:
                return fd.readlines()
        except (SyntaxError, UnicodeError):
            # If we can't detect the codec with tokenize.detect_encoding, or
            # the detected encoding is incorrect, just fallback to latin-1.
            with open(self.filename, encoding="latin-1") as fd:
                return fd.readlines()

    def read_lines_from_stdin(self) -> list[str]:
        """Read the lines from standard in."""
        return utils.stdin_get_lines()

    def should_ignore_file(self) -> bool:
        """Check if ``flake8: noqa`` is in the file to be ignored.

        :returns:
            True if a line matches :attr:`defaults.NOQA_FILE`,
            otherwise False
        """
        if not self.options.disable_noqa and any(
            defaults.NOQA_FILE.match(line) for line in self.lines
        ):
            return True
        elif any(defaults.NOQA_FILE.search(line) for line in self.lines):
            LOG.warning(
                "Detected `flake8: noqa` on line with code. To ignore an "
                "error on a line use `noqa` instead."
            )
            return False
        else:
            return False

    def strip_utf_bom(self) -> None:
        """Strip the UTF bom from the lines of the file."""
        if not self.lines:
            # If we have nothing to analyze quit early
            return

        # If the first byte of the file is a UTF-8 BOM, strip it
        if self.lines[0][:1] == "\uFEFF":
            self.lines[0] = self.lines[0][1:]
        elif self.lines[0][:3] == "\xEF\xBB\xBF":
            self.lines[0] = self.lines[0][3:]


def is_eol_token(token: tokenize.TokenInfo) -> bool:
    """Check if the token is an end-of-line token."""
    return token[0] in NEWLINE or token[4][token[3][1] :].lstrip() == "\\\n"


def is_multiline_string(token: tokenize.TokenInfo) -> bool:
    """Check if this is a multiline string."""
    return token.type in {FSTRING_END, TSTRING_END} or (
        token.type == tokenize.STRING and "\n" in token.string
    )


def token_is_newline(token: tokenize.TokenInfo) -> bool:
    """Check if the token type is a newline token type."""
    return token[0] in NEWLINE


def count_parentheses(current_parentheses_count: int, token_text: str) -> int:
    """Count the number of parentheses."""
    if token_text in "([{":  # nosec
        return current_parentheses_count + 1
    elif token_text in "}])":  # nosec
        return current_parentheses_count - 1
    return current_parentheses_count


def expand_indent(line: str) -> int:
    r"""Return the amount of indentation.

    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\t')
    8
    >>> expand_indent('       \t')
    8
    >>> expand_indent('        \t')
    16
    """
    return len(line.expandtabs(8))


# NOTE(sigmavirus24): This was taken wholesale from
# https://github.com/PyCQA/pycodestyle. The in-line comments were edited to be
# more descriptive.
def mutate_string(text: str) -> str:
    """Replace contents with 'xxx' to prevent syntax matching.

    >>> mutate_string('"abc"')
    '"xxx"'
    >>> mutate_string("'''abc'''")
    "'''xxx'''"
    >>> mutate_string("r'abc'")
    "r'xxx'"
    """
    # NOTE(sigmavirus24): If there are string modifiers (e.g., b, u, r)
    # use the last "character" to determine if we're using single or double
    # quotes and then find the first instance of it
    start = text.index(text[-1]) + 1
    end = len(text) - 1
    # Check for triple-quoted strings
    if text[-3:] in ('"""', "'''"):
        start += 2
        end -= 2
    return text[:start] + "x" * (end - start) + text[end:]
