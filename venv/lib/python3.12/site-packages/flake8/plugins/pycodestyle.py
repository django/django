"""Generated using ./bin/gen-pycodestyle-plugin."""
# fmt: off
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from pycodestyle import ambiguous_identifier as _ambiguous_identifier
from pycodestyle import bare_except as _bare_except
from pycodestyle import blank_lines as _blank_lines
from pycodestyle import break_after_binary_operator as _break_after_binary_operator  # noqa: E501
from pycodestyle import break_before_binary_operator as _break_before_binary_operator  # noqa: E501
from pycodestyle import comparison_negative as _comparison_negative
from pycodestyle import comparison_to_singleton as _comparison_to_singleton
from pycodestyle import comparison_type as _comparison_type
from pycodestyle import compound_statements as _compound_statements
from pycodestyle import continued_indentation as _continued_indentation
from pycodestyle import explicit_line_join as _explicit_line_join
from pycodestyle import extraneous_whitespace as _extraneous_whitespace
from pycodestyle import imports_on_separate_lines as _imports_on_separate_lines
from pycodestyle import indentation as _indentation
from pycodestyle import maximum_doc_length as _maximum_doc_length
from pycodestyle import maximum_line_length as _maximum_line_length
from pycodestyle import missing_whitespace as _missing_whitespace
from pycodestyle import missing_whitespace_after_keyword as _missing_whitespace_after_keyword  # noqa: E501
from pycodestyle import module_imports_on_top_of_file as _module_imports_on_top_of_file  # noqa: E501
from pycodestyle import python_3000_invalid_escape_sequence as _python_3000_invalid_escape_sequence  # noqa: E501
from pycodestyle import tabs_obsolete as _tabs_obsolete
from pycodestyle import tabs_or_spaces as _tabs_or_spaces
from pycodestyle import trailing_blank_lines as _trailing_blank_lines
from pycodestyle import trailing_whitespace as _trailing_whitespace
from pycodestyle import whitespace_around_comma as _whitespace_around_comma
from pycodestyle import whitespace_around_keywords as _whitespace_around_keywords  # noqa: E501
from pycodestyle import whitespace_around_named_parameter_equals as _whitespace_around_named_parameter_equals  # noqa: E501
from pycodestyle import whitespace_around_operator as _whitespace_around_operator  # noqa: E501
from pycodestyle import whitespace_before_comment as _whitespace_before_comment
from pycodestyle import whitespace_before_parameters as _whitespace_before_parameters  # noqa: E501


def pycodestyle_logical(
    blank_before: Any,
    blank_lines: Any,
    checker_state: Any,
    hang_closing: Any,
    indent_char: Any,
    indent_level: Any,
    indent_size: Any,
    line_number: Any,
    lines: Any,
    logical_line: Any,
    max_doc_length: Any,
    noqa: Any,
    previous_indent_level: Any,
    previous_logical: Any,
    previous_unindented_logical_line: Any,
    tokens: Any,
    verbose: Any,
) -> Generator[tuple[int, str]]:
    """Run pycodestyle logical checks."""
    yield from _ambiguous_identifier(logical_line, tokens)
    yield from _bare_except(logical_line, noqa)
    yield from _blank_lines(logical_line, blank_lines, indent_level, line_number, blank_before, previous_logical, previous_unindented_logical_line, previous_indent_level, lines)  # noqa: E501
    yield from _break_after_binary_operator(logical_line, tokens)
    yield from _break_before_binary_operator(logical_line, tokens)
    yield from _comparison_negative(logical_line)
    yield from _comparison_to_singleton(logical_line, noqa)
    yield from _comparison_type(logical_line, noqa)
    yield from _compound_statements(logical_line)
    yield from _continued_indentation(logical_line, tokens, indent_level, hang_closing, indent_char, indent_size, noqa, verbose)  # noqa: E501
    yield from _explicit_line_join(logical_line, tokens)
    yield from _extraneous_whitespace(logical_line)
    yield from _imports_on_separate_lines(logical_line)
    yield from _indentation(logical_line, previous_logical, indent_char, indent_level, previous_indent_level, indent_size)  # noqa: E501
    yield from _maximum_doc_length(logical_line, max_doc_length, noqa, tokens)
    yield from _missing_whitespace(logical_line, tokens)
    yield from _missing_whitespace_after_keyword(logical_line, tokens)
    yield from _module_imports_on_top_of_file(logical_line, indent_level, checker_state, noqa)  # noqa: E501
    yield from _python_3000_invalid_escape_sequence(logical_line, tokens, noqa)
    yield from _whitespace_around_comma(logical_line)
    yield from _whitespace_around_keywords(logical_line)
    yield from _whitespace_around_named_parameter_equals(logical_line, tokens)
    yield from _whitespace_around_operator(logical_line)
    yield from _whitespace_before_comment(logical_line, tokens)
    yield from _whitespace_before_parameters(logical_line, tokens)


def pycodestyle_physical(
    indent_char: Any,
    line_number: Any,
    lines: Any,
    max_line_length: Any,
    multiline: Any,
    noqa: Any,
    physical_line: Any,
    total_lines: Any,
) -> Generator[tuple[int, str]]:
    """Run pycodestyle physical checks."""
    ret = _maximum_line_length(physical_line, max_line_length, multiline, line_number, noqa)  # noqa: E501
    if ret is not None:
        yield ret
    ret = _tabs_obsolete(physical_line)
    if ret is not None:
        yield ret
    ret = _tabs_or_spaces(physical_line, indent_char)
    if ret is not None:
        yield ret
    ret = _trailing_blank_lines(physical_line, lines, line_number, total_lines)
    if ret is not None:
        yield ret
    ret = _trailing_whitespace(physical_line)
    if ret is not None:
        yield ret
