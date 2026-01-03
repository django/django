"""Defines all wrap modes that can be used when outputting formatted imports"""

import enum
from collections.abc import Callable
from inspect import signature
from typing import Any

import isort.comments

_wrap_modes: dict[str, Callable[..., str]] = {}


def from_string(value: str) -> "WrapModes":
    return getattr(WrapModes, str(value), None) or WrapModes(int(value))


def formatter_from_string(name: str) -> Callable[..., str]:
    return _wrap_modes.get(name.upper(), grid)


def _wrap_mode_interface(
    statement: str,
    imports: list[str],
    white_space: str,
    indent: str,
    line_length: int,
    comments: list[str],
    line_separator: str,
    comment_prefix: str,
    include_trailing_comma: bool,
    remove_comments: bool,
) -> str:
    """Defines the common interface used by all wrap mode functions"""
    return ""


def _wrap_mode(function: Callable[..., str]) -> Callable[..., str]:
    """Registers an individual wrap mode. Function name and order are significant and used for
    creating enum.
    """
    _wrap_modes[function.__name__.upper()] = function
    function.__signature__ = signature(_wrap_mode_interface)  # type: ignore
    function.__annotations__ = _wrap_mode_interface.__annotations__
    return function


@_wrap_mode
def grid(**interface: Any) -> str:
    if not interface["imports"]:
        return ""

    interface["statement"] += "(" + interface["imports"].pop(0)
    while interface["imports"]:
        next_import = interface["imports"].pop(0)
        next_statement = isort.comments.add_to_line(
            interface["comments"],
            interface["statement"] + ", " + next_import,
            removed=interface["remove_comments"],
            comment_prefix=interface["comment_prefix"],
        )
        if (
            len(next_statement.split(interface["line_separator"])[-1]) + 1
            > interface["line_length"]
        ):
            lines = [f"{interface['white_space']}{next_import.split(' ')[0]}"]
            for part in next_import.split(" ")[1:]:
                new_line = f"{lines[-1]} {part}"
                if len(new_line) + 1 > interface["line_length"]:
                    lines.append(f"{interface['white_space']}{part}")
                else:
                    lines[-1] = new_line
            next_import = interface["line_separator"].join(lines)
            interface["statement"] = (
                isort.comments.add_to_line(
                    interface["comments"],
                    f"{interface['statement']},",
                    removed=interface["remove_comments"],
                    comment_prefix=interface["comment_prefix"],
                )
                + f"{interface['line_separator']}{next_import}"
            )
            interface["comments"] = []
        else:
            interface["statement"] += ", " + next_import
    return f"{interface['statement']}{',' if interface['include_trailing_comma'] else ''})"


@_wrap_mode
def vertical(**interface: Any) -> str:
    if not interface["imports"]:
        return ""

    first_import = (
        isort.comments.add_to_line(
            interface["comments"],
            interface["imports"].pop(0) + ",",
            removed=interface["remove_comments"],
            comment_prefix=interface["comment_prefix"],
        )
        + interface["line_separator"]
        + interface["white_space"]
    )

    _imports = ("," + interface["line_separator"] + interface["white_space"]).join(
        interface["imports"]
    )
    _comma_maybe = "," if interface["include_trailing_comma"] else ""
    return f"{interface['statement']}({first_import}{_imports}{_comma_maybe})"


def _hanging_indent_end_line(line: str) -> str:
    if not line.endswith(" "):
        line += " "
    return line + "\\"


@_wrap_mode
def hanging_indent(**interface: Any) -> str:
    if not interface["imports"]:
        return ""

    line_length_limit = interface["line_length"] - 3

    next_import = interface["imports"].pop(0)
    next_statement = interface["statement"] + next_import
    # Check for first import
    if len(next_statement) > line_length_limit:
        next_statement = (
            _hanging_indent_end_line(interface["statement"])
            + interface["line_separator"]
            + interface["indent"]
            + next_import
        )

    interface["statement"] = next_statement
    while interface["imports"]:
        next_import = interface["imports"].pop(0)
        next_statement = interface["statement"] + ", " + next_import
        if len(next_statement.split(interface["line_separator"])[-1]) > line_length_limit:
            next_statement = (
                _hanging_indent_end_line(interface["statement"] + ",")
                + f"{interface['line_separator']}{interface['indent']}{next_import}"
            )
        interface["statement"] = next_statement

    if interface["comments"]:
        statement_with_comments = isort.comments.add_to_line(
            interface["comments"],
            interface["statement"],
            removed=interface["remove_comments"],
            comment_prefix=interface["comment_prefix"],
        )
        if len(statement_with_comments.split(interface["line_separator"])[-1]) <= (
            line_length_limit + 2
        ):
            return statement_with_comments
        return (
            _hanging_indent_end_line(interface["statement"])
            + str(interface["line_separator"])
            + isort.comments.add_to_line(
                interface["comments"],
                interface["indent"],
                removed=interface["remove_comments"],
                comment_prefix=interface["comment_prefix"].lstrip(),
            )
        )
    return str(interface["statement"])


@_wrap_mode
def vertical_hanging_indent(**interface: Any) -> str:
    _line_with_comments = isort.comments.add_to_line(
        interface["comments"],
        "",
        removed=interface["remove_comments"],
        comment_prefix=interface["comment_prefix"],
    )
    _imports = ("," + interface["line_separator"] + interface["indent"]).join(interface["imports"])
    _comma_maybe = "," if interface["include_trailing_comma"] else ""
    return (
        f"{interface['statement']}({_line_with_comments}{interface['line_separator']}"
        f"{interface['indent']}{_imports}{_comma_maybe}{interface['line_separator']})"
    )


def _vertical_grid_common(need_trailing_char: bool, **interface: Any) -> str:
    if not interface["imports"]:
        return ""

    interface["statement"] += (
        isort.comments.add_to_line(
            interface["comments"],
            "(",
            removed=interface["remove_comments"],
            comment_prefix=interface["comment_prefix"],
        )
        + interface["line_separator"]
        + interface["indent"]
        + interface["imports"].pop(0)
    )
    while interface["imports"]:
        next_import = interface["imports"].pop(0)
        next_statement = f"{interface['statement']}, {next_import}"
        current_line_length = len(next_statement.split(interface["line_separator"])[-1])
        if interface["imports"] or interface["include_trailing_comma"]:
            # We need to account for a comma after this import.
            current_line_length += 1
        if not interface["imports"] and need_trailing_char:
            # We need to account for a closing ) we're going to add.
            current_line_length += 1
        if current_line_length > interface["line_length"]:
            next_statement = (
                f"{interface['statement']},{interface['line_separator']}"
                f"{interface['indent']}{next_import}"
            )
        interface["statement"] = next_statement
    if interface["include_trailing_comma"]:
        interface["statement"] += ","
    return str(interface["statement"])


@_wrap_mode
def vertical_grid(**interface: Any) -> str:
    return _vertical_grid_common(need_trailing_char=True, **interface) + ")"


@_wrap_mode
def vertical_grid_grouped(**interface: Any) -> str:
    return (
        _vertical_grid_common(need_trailing_char=False, **interface)
        + str(interface["line_separator"])
        + ")"
    )


@_wrap_mode
def vertical_grid_grouped_no_comma(**interface: Any) -> str:
    # This is a deprecated alias for vertical_grid_grouped above. This function
    # needs to exist for backwards compatibility but should never get called.
    raise NotImplementedError


@_wrap_mode
def noqa(**interface: Any) -> str:
    _imports = ", ".join(interface["imports"])
    retval = f"{interface['statement']}{_imports}"
    comment_str = " ".join(interface["comments"])
    if interface["comments"]:
        if (
            len(retval) + len(interface["comment_prefix"]) + 1 + len(comment_str)
            <= interface["line_length"]
        ):
            return f"{retval}{interface['comment_prefix']} {comment_str}"
        if "NOQA" in interface["comments"]:
            return f"{retval}{interface['comment_prefix']} {comment_str}"
        return f"{retval}{interface['comment_prefix']} NOQA {comment_str}"

    if len(retval) <= interface["line_length"]:
        return retval
    return f"{retval}{interface['comment_prefix']} NOQA"


@_wrap_mode
def vertical_hanging_indent_bracket(**interface: Any) -> str:
    if not interface["imports"]:
        return ""
    statement = vertical_hanging_indent(**interface)
    return f"{statement[:-1]}{interface['indent']})"


@_wrap_mode
def vertical_prefix_from_module_import(**interface: Any) -> str:
    if not interface["imports"]:
        return ""

    prefix_statement = interface["statement"]
    output_statement = prefix_statement + interface["imports"].pop(0)
    comments = interface["comments"]

    statement = output_statement
    statement_with_comments = ""
    for next_import in interface["imports"]:
        statement = statement + ", " + next_import
        statement_with_comments = isort.comments.add_to_line(
            comments,
            statement,
            removed=interface["remove_comments"],
            comment_prefix=interface["comment_prefix"],
        )
        if (
            len(statement_with_comments.split(interface["line_separator"])[-1]) + 1
            > interface["line_length"]
        ):
            statement = (
                isort.comments.add_to_line(
                    comments,
                    output_statement,
                    removed=interface["remove_comments"],
                    comment_prefix=interface["comment_prefix"],
                )
                + f"{interface['line_separator']}{prefix_statement}{next_import}"
            )
            comments = []
        output_statement = statement

    if comments and statement_with_comments:
        output_statement = statement_with_comments
    return str(output_statement)


@_wrap_mode
def hanging_indent_with_parentheses(**interface: Any) -> str:
    if not interface["imports"]:
        return ""

    line_length_limit = interface["line_length"] - 1

    interface["statement"] += "("
    next_import = interface["imports"].pop(0)
    next_statement = interface["statement"] + next_import
    # Check for first import
    if len(next_statement) > line_length_limit:
        next_statement = (
            isort.comments.add_to_line(
                interface["comments"],
                interface["statement"],
                removed=interface["remove_comments"],
                comment_prefix=interface["comment_prefix"],
            )
            + f"{interface['line_separator']}{interface['indent']}{next_import}"
        )
        interface["comments"] = []
    interface["statement"] = next_statement
    while interface["imports"]:
        next_import = interface["imports"].pop(0)
        if (
            interface["line_separator"] not in interface["statement"]
            and "#" in interface["statement"]
        ):  # pragma: no cover # TODO: fix, this is because of test run inconsistency.
            line, comments = interface["statement"].split("#", 1)
            next_statement = (
                f"{line.rstrip()}, {next_import}{interface['comment_prefix']}{comments}"
            )
        else:
            next_statement = isort.comments.add_to_line(
                interface["comments"],
                interface["statement"] + ", " + next_import,
                removed=interface["remove_comments"],
                comment_prefix=interface["comment_prefix"],
            )
        current_line = next_statement.split(interface["line_separator"])[-1]
        if len(current_line) > line_length_limit:
            next_statement = (
                isort.comments.add_to_line(
                    interface["comments"],
                    interface["statement"] + ",",
                    removed=interface["remove_comments"],
                    comment_prefix=interface["comment_prefix"],
                )
                + f"{interface['line_separator']}{interface['indent']}{next_import}"
            )
            interface["comments"] = []
        interface["statement"] = next_statement
    return f"{interface['statement']}{',' if interface['include_trailing_comma'] else ''})"


@_wrap_mode
def backslash_grid(**interface: Any) -> str:
    interface["indent"] = interface["white_space"][:-1]
    return hanging_indent(**interface)


WrapModes = enum.Enum(  # type: ignore
    "WrapModes", {wrap_mode: index for index, wrap_mode in enumerate(_wrap_modes.keys())}
)
