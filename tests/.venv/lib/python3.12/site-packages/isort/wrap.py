import copy
import re
from collections.abc import Sequence

from .settings import DEFAULT_CONFIG, Config
from .wrap_modes import WrapModes as Modes
from .wrap_modes import formatter_from_string, vertical_hanging_indent


def import_statement(
    import_start: str,
    from_imports: list[str],
    comments: Sequence[str] = (),
    line_separator: str = "\n",
    config: Config = DEFAULT_CONFIG,
    multi_line_output: Modes | None = None,
    explode: bool = False,
) -> str:
    """Returns a multi-line wrapped form of the provided from import statement."""
    if explode:
        formatter = vertical_hanging_indent
        line_length = 1
        include_trailing_comma = True
    else:
        formatter = formatter_from_string((multi_line_output or config.multi_line_output).name)
        line_length = config.wrap_length or config.line_length
        include_trailing_comma = config.include_trailing_comma
    dynamic_indent = " " * (len(import_start) + 1)
    indent = config.indent
    statement = formatter(
        statement=import_start,
        imports=copy.copy(from_imports),
        white_space=dynamic_indent,
        indent=indent,
        line_length=line_length,
        comments=comments,
        line_separator=line_separator,
        comment_prefix=config.comment_prefix,
        include_trailing_comma=include_trailing_comma,
        remove_comments=config.ignore_comments,
    )
    if config.balanced_wrapping:
        lines = statement.split(line_separator)
        line_count = len(lines)
        if len(lines) > 1:
            minimum_length = min(len(line) for line in lines[:-1])
        else:
            minimum_length = 0
        new_import_statement = statement
        while len(lines[-1]) < minimum_length and len(lines) == line_count and line_length > 10:
            statement = new_import_statement
            line_length -= 1
            new_import_statement = formatter(
                statement=import_start,
                imports=copy.copy(from_imports),
                white_space=dynamic_indent,
                indent=indent,
                line_length=line_length,
                comments=comments,
                line_separator=line_separator,
                comment_prefix=config.comment_prefix,
                include_trailing_comma=include_trailing_comma,
                remove_comments=config.ignore_comments,
            )
            lines = new_import_statement.split(line_separator)
    if statement.count(line_separator) == 0:
        return _wrap_line(statement, line_separator, config)
    return statement


def line(content: str, line_separator: str, config: Config = DEFAULT_CONFIG) -> str:
    """Returns a line wrapped to the specified line-length, if possible."""
    wrap_mode = config.multi_line_output
    if len(content) > config.line_length and wrap_mode != Modes.NOQA:  # type: ignore
        line_without_comment = content
        comment = None
        if "#" in content:
            line_without_comment, comment = content.split("#", 1)
        for splitter in ("import ", "cimport ", ".", "as "):
            exp = r"\b" + re.escape(splitter) + r"\b"
            if re.search(exp, line_without_comment) and not line_without_comment.strip().startswith(
                splitter
            ):
                line_parts = re.split(exp, line_without_comment)
                if comment and not (config.use_parentheses and "noqa" in comment):
                    _comma_maybe = (
                        ","
                        if (
                            config.include_trailing_comma
                            and config.use_parentheses
                            and not line_without_comment.rstrip().endswith(",")
                        )
                        else ""
                    )
                    line_parts[-1] = (
                        f"{line_parts[-1].strip()}{_comma_maybe}{config.comment_prefix}{comment}"
                    )
                next_line = []
                while (len(content) + 2) > (
                    config.wrap_length or config.line_length
                ) and line_parts:
                    next_line.append(line_parts.pop())
                    content = splitter.join(line_parts)
                if not content:
                    content = next_line.pop()

                cont_line = _wrap_line(
                    config.indent + splitter.join(next_line).lstrip(),
                    line_separator,
                    config,
                )
                if config.use_parentheses:
                    if splitter == "as ":
                        output = f"{content}{splitter}{cont_line.lstrip()}"
                    else:
                        _comma = "," if config.include_trailing_comma and not comment else ""

                        if wrap_mode in (
                            Modes.VERTICAL_HANGING_INDENT,  # type: ignore
                            Modes.VERTICAL_GRID_GROUPED,  # type: ignore
                        ):
                            _separator = line_separator
                        else:
                            _separator = ""
                        noqa_comment = ""
                        if comment and "noqa" in comment:
                            noqa_comment = f"{config.comment_prefix}{comment}"
                            cont_line = cont_line.rstrip()
                            _comma = "," if config.include_trailing_comma else ""
                        output = (
                            f"{content}{splitter}({noqa_comment}"
                            f"{line_separator}{cont_line}{_comma}{_separator})"
                        )
                        lines = output.split(line_separator)
                        if config.comment_prefix in lines[-1] and lines[-1].endswith(")"):
                            content, comment = lines[-1].split(config.comment_prefix, 1)
                            lines[-1] = content + ")" + config.comment_prefix + comment[:-1]
                        output = line_separator.join(lines)
                    return output
                return f"{content}{splitter}\\{line_separator}{cont_line}"
    elif len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content:  # type: ignore
        return f"{content}{config.comment_prefix} NOQA"

    return content


_wrap_line = line
