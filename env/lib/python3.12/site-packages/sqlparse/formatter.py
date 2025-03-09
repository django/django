#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""SQL formatter"""

from sqlparse import filters
from sqlparse.exceptions import SQLParseError


def validate_options(options):  # noqa: C901
    """Validates options."""
    kwcase = options.get("keyword_case")
    if kwcase not in [None, "upper", "lower", "capitalize"]:
        raise SQLParseError("Invalid value for keyword_case: " "{!r}".format(kwcase))

    idcase = options.get("identifier_case")
    if idcase not in [None, "upper", "lower", "capitalize"]:
        raise SQLParseError("Invalid value for identifier_case: " "{!r}".format(idcase))

    ofrmt = options.get("output_format")
    if ofrmt not in [None, "sql", "python", "php"]:
        raise SQLParseError("Unknown output format: " "{!r}".format(ofrmt))

    strip_comments = options.get("strip_comments", False)
    if strip_comments not in [True, False]:
        raise SQLParseError(
            "Invalid value for strip_comments: " "{!r}".format(strip_comments)
        )

    space_around_operators = options.get("use_space_around_operators", False)
    if space_around_operators not in [True, False]:
        raise SQLParseError(
            "Invalid value for use_space_around_operators: "
            "{!r}".format(space_around_operators)
        )

    strip_ws = options.get("strip_whitespace", False)
    if strip_ws not in [True, False]:
        raise SQLParseError(
            "Invalid value for strip_whitespace: " "{!r}".format(strip_ws)
        )

    truncate_strings = options.get("truncate_strings")
    if truncate_strings is not None:
        try:
            truncate_strings = int(truncate_strings)
        except (ValueError, TypeError):
            raise SQLParseError(
                "Invalid value for truncate_strings: " "{!r}".format(truncate_strings)
            )
        if truncate_strings <= 1:
            raise SQLParseError(
                "Invalid value for truncate_strings: " "{!r}".format(truncate_strings)
            )
        options["truncate_strings"] = truncate_strings
        options["truncate_char"] = options.get("truncate_char", "[...]")

    indent_columns = options.get("indent_columns", False)
    if indent_columns not in [True, False]:
        raise SQLParseError(
            "Invalid value for indent_columns: " "{!r}".format(indent_columns)
        )
    elif indent_columns:
        options["reindent"] = True  # enforce reindent
    options["indent_columns"] = indent_columns

    reindent = options.get("reindent", False)
    if reindent not in [True, False]:
        raise SQLParseError("Invalid value for reindent: " "{!r}".format(reindent))
    elif reindent:
        options["strip_whitespace"] = True

    reindent_aligned = options.get("reindent_aligned", False)
    if reindent_aligned not in [True, False]:
        raise SQLParseError(
            "Invalid value for reindent_aligned: " "{!r}".format(reindent)
        )
    elif reindent_aligned:
        options["strip_whitespace"] = True

    indent_after_first = options.get("indent_after_first", False)
    if indent_after_first not in [True, False]:
        raise SQLParseError(
            "Invalid value for indent_after_first: " "{!r}".format(indent_after_first)
        )
    options["indent_after_first"] = indent_after_first

    indent_tabs = options.get("indent_tabs", False)
    if indent_tabs not in [True, False]:
        raise SQLParseError(
            "Invalid value for indent_tabs: " "{!r}".format(indent_tabs)
        )
    elif indent_tabs:
        options["indent_char"] = "\t"
    else:
        options["indent_char"] = " "

    indent_width = options.get("indent_width", 2)
    try:
        indent_width = int(indent_width)
    except (TypeError, ValueError):
        raise SQLParseError("indent_width requires an integer")
    if indent_width < 1:
        raise SQLParseError("indent_width requires a positive integer")
    options["indent_width"] = indent_width

    wrap_after = options.get("wrap_after", 0)
    try:
        wrap_after = int(wrap_after)
    except (TypeError, ValueError):
        raise SQLParseError("wrap_after requires an integer")
    if wrap_after < 0:
        raise SQLParseError("wrap_after requires a positive integer")
    options["wrap_after"] = wrap_after

    comma_first = options.get("comma_first", False)
    if comma_first not in [True, False]:
        raise SQLParseError("comma_first requires a boolean value")
    options["comma_first"] = comma_first

    compact = options.get("compact", False)
    if compact not in [True, False]:
        raise SQLParseError("compact requires a boolean value")
    options["compact"] = compact

    right_margin = options.get("right_margin")
    if right_margin is not None:
        try:
            right_margin = int(right_margin)
        except (TypeError, ValueError):
            raise SQLParseError("right_margin requires an integer")
        if right_margin < 10:
            raise SQLParseError("right_margin requires an integer > 10")
    options["right_margin"] = right_margin

    return options


def build_filter_stack(stack, options):
    """Setup and return a filter stack.

    Args:
      stack: :class:`~sqlparse.filters.FilterStack` instance
      options: Dictionary with options validated by validate_options.
    """
    # Token filter
    if options.get("keyword_case"):
        stack.preprocess.append(filters.KeywordCaseFilter(options["keyword_case"]))

    if options.get("identifier_case"):
        stack.preprocess.append(
            filters.IdentifierCaseFilter(options["identifier_case"])
        )

    if options.get("truncate_strings"):
        stack.preprocess.append(
            filters.TruncateStringFilter(
                width=options["truncate_strings"], char=options["truncate_char"]
            )
        )

    if options.get("use_space_around_operators", False):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.SpacesAroundOperatorsFilter())

    # After grouping
    if options.get("strip_comments"):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripCommentsFilter())

    if options.get("strip_whitespace") or options.get("reindent"):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripWhitespaceFilter())

    if options.get("reindent"):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.ReindentFilter(
                char=options["indent_char"],
                width=options["indent_width"],
                indent_after_first=options["indent_after_first"],
                indent_columns=options["indent_columns"],
                wrap_after=options["wrap_after"],
                comma_first=options["comma_first"],
                compact=options["compact"],
            )
        )

    if options.get("reindent_aligned", False):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.AlignedIndentFilter(char=options["indent_char"])
        )

    if options.get("right_margin"):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.RightMarginFilter(width=options["right_margin"])
        )

    # Serializer
    if options.get("output_format"):
        frmt = options["output_format"]
        if frmt.lower() == "php":
            fltr = filters.OutputPHPFilter()
        elif frmt.lower() == "python":
            fltr = filters.OutputPythonFilter()
        else:
            fltr = None
        if fltr is not None:
            stack.postprocess.append(fltr)

    return stack
