import copy
import itertools
from collections.abc import Iterable
from functools import partial
from typing import Any

from isort.format import format_simplified

from . import parse, sorting, wrap
from .comments import add_to_line as with_comments
from .identify import STATEMENT_DECLARATIONS
from .settings import DEFAULT_CONFIG, Config


def sorted_imports(
    parsed: parse.ParsedContent,
    config: Config = DEFAULT_CONFIG,
    extension: str = "py",
    import_type: str = "import",
) -> str:
    """Adds the imports back to the file.

    (at the index of the first import) sorted alphabetically and split between groups

    """
    if parsed.import_index == -1:
        return _output_as_string(parsed.lines_without_imports, parsed.line_separator)

    formatted_output: list[str] = parsed.lines_without_imports.copy()
    remove_imports = [format_simplified(removal) for removal in config.remove_imports]

    sections: Iterable[str] = itertools.chain(parsed.sections, config.forced_separate)

    if config.no_sections:
        parsed.imports["no_sections"] = {"straight": {}, "from": {}}
        base_sections: tuple[str, ...] = ()
        for section in sections:
            if section == "FUTURE":
                base_sections = ("FUTURE",)
                continue
            parsed.imports["no_sections"]["straight"].update(
                parsed.imports[section].get("straight", {})
            )
            parsed.imports["no_sections"]["from"].update(parsed.imports[section].get("from", {}))
        sections = (*base_sections, "no_sections")

    output: list[str] = []
    seen_headings: set[str] = set()
    pending_lines_before = False
    for section in sections:
        straight_modules = parsed.imports[section]["straight"]
        if not config.only_sections:
            straight_modules = sorting.sort(
                config,
                straight_modules,
                key=lambda key: sorting.module_key(
                    key, config, section_name=section, straight_import=True
                ),
                reverse=config.reverse_sort,
            )

        from_modules = parsed.imports[section]["from"]
        if not config.only_sections:
            from_modules = sorting.sort(
                config,
                from_modules,
                key=lambda key: sorting.module_key(key, config, section_name=section),
                reverse=config.reverse_sort,
            )

            if config.star_first:
                star_modules = []
                other_modules = []
                for module in from_modules:
                    if "*" in parsed.imports[section]["from"][module]:
                        star_modules.append(module)
                    else:
                        other_modules.append(module)
                from_modules = star_modules + other_modules

        straight_imports = _with_straight_imports(
            parsed, config, straight_modules, section, remove_imports, import_type
        )
        from_imports = _with_from_imports(
            parsed, config, from_modules, section, remove_imports, import_type
        )

        lines_between = [""] * (
            config.lines_between_types if from_modules and straight_modules else 0
        )
        if config.from_first:
            section_output = from_imports + lines_between + straight_imports
        else:
            section_output = straight_imports + lines_between + from_imports

        if config.force_sort_within_sections:
            # collapse comments
            comments_above = []
            new_section_output: list[str] = []
            for line in section_output:
                if not line:
                    continue
                if line.startswith("#"):
                    comments_above.append(line)
                elif comments_above:
                    new_section_output.append(_LineWithComments(line, comments_above))
                    comments_above = []
                else:
                    new_section_output.append(line)
            # only_sections options is not imposed if force_sort_within_sections is True
            new_section_output = sorting.sort(
                config,
                new_section_output,
                key=partial(sorting.section_key, config=config),
                reverse=config.reverse_sort,
            )

            # uncollapse comments
            section_output = []
            for line in new_section_output:
                comments = getattr(line, "comments", ())
                if comments:
                    section_output.extend(comments)
                section_output.append(str(line))

        section_name = section
        no_lines_before = section_name in config.no_lines_before

        if section_output:
            if section_name in parsed.place_imports:
                parsed.place_imports[section_name] = section_output
                continue

            section_title = config.import_headings.get(section_name.lower(), "")
            if section_title and section_title not in seen_headings:
                if config.dedup_headings:
                    seen_headings.add(section_title)
                section_comment = f"# {section_title}"
                if section_comment not in parsed.lines_without_imports[0:1]:  # pragma: no branch
                    section_output.insert(0, section_comment)

            section_footer = config.import_footers.get(section_name.lower(), "")
            if section_footer and section_footer not in seen_headings:
                if config.dedup_headings:
                    seen_headings.add(section_footer)
                section_comment_end = f"# {section_footer}"
                if (
                    section_comment_end not in parsed.lines_without_imports[-1:]
                ):  # pragma: no branch
                    section_output.append("")  # Empty line for black compatibility
                    section_output.append(section_comment_end)

            if pending_lines_before or not no_lines_before:
                output += [""] * config.lines_between_sections

            output += section_output

            pending_lines_before = False
        else:
            pending_lines_before = pending_lines_before or not no_lines_before

    if config.ensure_newline_before_comments:
        output = _ensure_newline_before_comment(output)

    while output and output[-1].strip() == "":
        output.pop()  # pragma: no cover
    while output and output[0].strip() == "":
        output.pop(0)

    if config.formatting_function:
        output = config.formatting_function(
            parsed.line_separator.join(output), extension, config
        ).splitlines()

    output_at = 0
    if parsed.import_index < parsed.original_line_count:
        output_at = parsed.import_index
    formatted_output[output_at:0] = output

    if output:
        imports_tail = output_at + len(output)
        while [
            character.strip() for character in formatted_output[imports_tail : imports_tail + 1]
        ] == [""]:
            formatted_output.pop(imports_tail)

        if len(formatted_output) > imports_tail:
            next_construct = ""
            tail = formatted_output[imports_tail:]

            for index, line in enumerate(tail):  # pragma: no branch
                should_skip, in_quote, *_ = parse.skip_line(
                    line,
                    in_quote="",
                    index=len(formatted_output),
                    section_comments=config.section_comments,
                    needs_import=False,
                )
                if not should_skip and line.strip():
                    if (
                        line.strip().startswith("#")
                        and len(tail) > (index + 1)
                        and tail[index + 1].strip()
                    ):
                        continue
                    next_construct = line
                    break
                if in_quote:  # pragma: no branch
                    next_construct = line
                    break

            if config.lines_after_imports != -1:
                lines_after_imports = config.lines_after_imports
                if config.profile == "black" and extension == "pyi":  # special case for black
                    lines_after_imports = 1
                formatted_output[imports_tail:0] = ["" for line in range(lines_after_imports)]
            elif extension != "pyi" and next_construct.startswith(STATEMENT_DECLARATIONS):
                formatted_output[imports_tail:0] = ["", ""]
            else:
                formatted_output[imports_tail:0] = [""]

            if config.lines_before_imports != -1:
                lines_before_imports = config.lines_before_imports
                if config.profile == "black" and extension == "pyi":  # special case for black
                    lines_before_imports = 1
                formatted_output[:0] = ["" for line in range(lines_before_imports)]

    if parsed.place_imports:
        new_out_lines = []
        for index, line in enumerate(formatted_output):
            new_out_lines.append(line)
            if line in parsed.import_placements:
                new_out_lines.extend(parsed.place_imports[parsed.import_placements[line]])
                if (
                    len(formatted_output) <= (index + 1)
                    or formatted_output[index + 1].strip() != ""
                ):
                    new_out_lines.append("")
        formatted_output = new_out_lines

    return _output_as_string(formatted_output, parsed.line_separator)


# Ignore DeepSource cyclomatic complexity check for this function. It was
# already complex when this check was enabled.
# skipcq: PY-R1000
def _with_from_imports(
    parsed: parse.ParsedContent,
    config: Config,
    from_modules: Iterable[str],
    section: str,
    remove_imports: list[str],
    import_type: str,
) -> list[str]:
    output: list[str] = []
    for module in from_modules:
        if module in remove_imports:
            continue

        import_start = f"from {module} {import_type} "
        from_imports = list(parsed.imports[section]["from"][module])
        if (
            not config.no_inline_sort
            or (config.force_single_line and module not in config.single_line_exclusions)
        ) and not config.only_sections:
            from_imports = sorting.sort(
                config,
                from_imports,
                key=lambda key: sorting.module_key(
                    key,
                    config,
                    True,
                    config.force_alphabetical_sort_within_sections,
                    section_name=section,
                ),
                reverse=config.reverse_sort,
            )
        if remove_imports:
            from_imports = [
                line for line in from_imports if f"{module}.{line}" not in remove_imports
            ]

        sub_modules = [f"{module}.{from_import}" for from_import in from_imports]
        as_imports = {
            from_import: [
                f"{from_import} as {as_module}" for as_module in parsed.as_map["from"][sub_module]
            ]
            for from_import, sub_module in zip(from_imports, sub_modules, strict=False)
            if sub_module in parsed.as_map["from"]
        }
        if config.combine_as_imports and not ("*" in from_imports and config.combine_star):
            if not config.no_inline_sort:
                for as_import in as_imports:
                    if not config.only_sections:
                        as_imports[as_import] = sorting.sort(config, as_imports[as_import])
            for from_import in copy.copy(from_imports):
                if from_import in as_imports:
                    idx = from_imports.index(from_import)
                    if parsed.imports[section]["from"][module][from_import]:
                        from_imports[(idx + 1) : (idx + 1)] = as_imports.pop(from_import)
                    else:
                        from_imports[idx : (idx + 1)] = as_imports.pop(from_import)

        only_show_as_imports = False
        comments = parsed.categorized_comments["from"].pop(module, ())
        above_comments = parsed.categorized_comments["above"]["from"].pop(module, None)
        while from_imports:
            if above_comments:
                output.extend(above_comments)
                above_comments = None

            if "*" in from_imports and config.combine_star:
                import_statement = wrap.line(
                    with_comments(
                        _with_star_comments(parsed, module, list(comments or ())),
                        f"{import_start}*",
                        removed=config.ignore_comments,
                        comment_prefix=config.comment_prefix,
                    ),
                    parsed.line_separator,
                    config,
                )
                from_imports = [
                    from_import for from_import in from_imports if from_import in as_imports
                ]
                only_show_as_imports = True
            elif config.force_single_line and module not in config.single_line_exclusions:
                import_statement = ""
                while from_imports:
                    from_import = from_imports.pop(0)
                    single_import_line = with_comments(
                        comments,
                        import_start + from_import,
                        removed=config.ignore_comments,
                        comment_prefix=config.comment_prefix,
                    )
                    comment = (
                        parsed.categorized_comments["nested"].get(module, {}).pop(from_import, None)
                    )
                    if comment:
                        single_import_line += (
                            f"{(comments and ';') or config.comment_prefix} {comment}"
                        )
                    if from_import in as_imports:
                        if (
                            parsed.imports[section]["from"][module][from_import]
                            and not only_show_as_imports
                        ):
                            output.append(
                                wrap.line(single_import_line, parsed.line_separator, config)
                            )
                        from_comments = parsed.categorized_comments["straight"].get(
                            f"{module}.{from_import}"
                        )

                        if not config.only_sections:
                            output.extend(
                                with_comments(
                                    from_comments,
                                    wrap.line(
                                        import_start + as_import, parsed.line_separator, config
                                    ),
                                    removed=config.ignore_comments,
                                    comment_prefix=config.comment_prefix,
                                )
                                for as_import in sorting.sort(config, as_imports[from_import])
                            )

                        else:
                            output.extend(
                                with_comments(
                                    from_comments,
                                    wrap.line(
                                        import_start + as_import, parsed.line_separator, config
                                    ),
                                    removed=config.ignore_comments,
                                    comment_prefix=config.comment_prefix,
                                )
                                for as_import in as_imports[from_import]
                            )
                    else:
                        output.append(wrap.line(single_import_line, parsed.line_separator, config))
                    comments = None
            else:
                while from_imports and from_imports[0] in as_imports:
                    from_import = from_imports.pop(0)

                    if not config.only_sections:
                        as_imports[from_import] = sorting.sort(config, as_imports[from_import])
                    from_comments = (
                        parsed.categorized_comments["straight"].get(f"{module}.{from_import}") or []
                    )
                    if (
                        parsed.imports[section]["from"][module][from_import]
                        and not only_show_as_imports
                    ):
                        specific_comment = (
                            parsed.categorized_comments["nested"]
                            .get(module, {})
                            .pop(from_import, None)
                        )
                        if specific_comment:
                            from_comments.append(specific_comment)
                        output.append(
                            wrap.line(
                                with_comments(
                                    from_comments,
                                    import_start + from_import,
                                    removed=config.ignore_comments,
                                    comment_prefix=config.comment_prefix,
                                ),
                                parsed.line_separator,
                                config,
                            )
                        )
                        from_comments = []

                    for as_import in as_imports[from_import]:
                        specific_comment = (
                            parsed.categorized_comments["nested"]
                            .get(module, {})
                            .pop(as_import, None)
                        )
                        if specific_comment:
                            from_comments.append(specific_comment)

                        output.append(
                            wrap.line(
                                with_comments(
                                    from_comments,
                                    import_start + as_import,
                                    removed=config.ignore_comments,
                                    comment_prefix=config.comment_prefix,
                                ),
                                parsed.line_separator,
                                config,
                            )
                        )

                        from_comments = []

                if "*" in from_imports:
                    output.append(
                        with_comments(
                            _with_star_comments(parsed, module, []),
                            f"{import_start}*",
                            removed=config.ignore_comments,
                            comment_prefix=config.comment_prefix,
                        )
                    )
                    from_imports.remove("*")

                for from_import in copy.copy(from_imports):
                    comment = (
                        parsed.categorized_comments["nested"].get(module, {}).pop(from_import, None)
                    )
                    if comment:
                        # If the comment is a noqa and hanging indent wrapping is used,
                        # keep the name in the main list and hoist the comment to the statement.
                        if (
                            comment.lower().startswith("noqa")
                            and config.multi_line_output == wrap.Modes.HANGING_INDENT  # type: ignore[attr-defined] # noqa: E501
                        ):
                            comments = list(comments) if comments else []
                            comments.append(comment)
                            continue

                        from_imports.remove(from_import)
                        if from_imports:
                            use_comments = []
                        else:
                            use_comments = comments
                            comments = None
                        single_import_line = with_comments(
                            use_comments,
                            import_start + from_import,
                            removed=config.ignore_comments,
                            comment_prefix=config.comment_prefix,
                        )
                        single_import_line += (
                            f"{(use_comments and ';') or config.comment_prefix} {comment}"
                        )
                        output.append(wrap.line(single_import_line, parsed.line_separator, config))

                from_import_section = []
                while from_imports and (
                    from_imports[0] not in as_imports
                    or (
                        config.combine_as_imports
                        and parsed.imports[section]["from"][module][from_import]
                    )
                ):
                    from_import_section.append(from_imports.pop(0))
                if config.combine_as_imports:
                    comments = (comments or []) + list(
                        parsed.categorized_comments["from"].pop(f"{module}.__combined_as__", ())
                    )
                import_statement = with_comments(
                    comments,
                    import_start + (", ").join(from_import_section),
                    removed=config.ignore_comments,
                    comment_prefix=config.comment_prefix,
                )
                if not from_import_section:
                    import_statement = ""

                do_multiline_reformat = False

                force_grid_wrap = config.force_grid_wrap
                if force_grid_wrap and len(from_import_section) >= force_grid_wrap:
                    do_multiline_reformat = True

                if len(import_statement) > config.line_length and len(from_import_section) > 1:
                    do_multiline_reformat = True

                # If line too long AND have imports AND we are
                # NOT using GRID or VERTICAL wrap modes
                if (
                    len(import_statement) > config.line_length
                    and len(from_import_section) > 0
                    and config.multi_line_output not in (wrap.Modes.GRID, wrap.Modes.VERTICAL)  # type: ignore # noqa: E501
                ):
                    do_multiline_reformat = True

                if (
                    import_statement
                    and config.split_on_trailing_comma
                    and module in parsed.trailing_commas
                ):
                    import_statement = wrap.import_statement(
                        import_start=import_start,
                        from_imports=from_import_section,
                        comments=comments,
                        line_separator=parsed.line_separator,
                        config=config,
                        explode=True,
                    )

                elif do_multiline_reformat:
                    import_statement = wrap.import_statement(
                        import_start=import_start,
                        from_imports=from_import_section,
                        comments=comments,
                        line_separator=parsed.line_separator,
                        config=config,
                    )
                    if config.multi_line_output == wrap.Modes.GRID:  # type: ignore
                        other_import_statement = wrap.import_statement(
                            import_start=import_start,
                            from_imports=from_import_section,
                            comments=comments,
                            line_separator=parsed.line_separator,
                            config=config,
                            multi_line_output=wrap.Modes.VERTICAL_GRID,  # type: ignore
                        )
                        if (
                            max(
                                len(import_line)
                                for import_line in import_statement.split(parsed.line_separator)
                            )
                            > config.line_length
                        ):
                            import_statement = other_import_statement
                elif len(import_statement) > config.line_length:
                    import_statement = wrap.line(import_statement, parsed.line_separator, config)

            if import_statement:
                output.append(import_statement)
    return output


def _with_straight_imports(
    parsed: parse.ParsedContent,
    config: Config,
    straight_modules: Iterable[str],
    section: str,
    remove_imports: list[str],
    import_type: str,
) -> list[str]:
    output: list[str] = []

    as_imports = any(module in parsed.as_map["straight"] for module in straight_modules)

    # combine_straight_imports only works for bare imports, 'as' imports not included
    if config.combine_straight_imports and not as_imports:
        if not straight_modules:
            return []

        above_comments: list[str] = []
        inline_comments: list[str] = []

        for module in straight_modules:
            if module in parsed.categorized_comments["above"]["straight"]:
                above_comments.extend(parsed.categorized_comments["above"]["straight"].pop(module))
            if module in parsed.categorized_comments["straight"]:
                inline_comments.extend(parsed.categorized_comments["straight"][module])

        combined_straight_imports = ", ".join(straight_modules)
        if inline_comments:
            combined_inline_comments = " ".join(inline_comments)
        else:
            combined_inline_comments = ""

        output.extend(above_comments)

        if combined_inline_comments:
            output.append(
                f"{import_type} {combined_straight_imports}  # {combined_inline_comments}"
            )
        else:
            output.append(f"{import_type} {combined_straight_imports}")

        return output

    for module in straight_modules:
        if module in remove_imports:
            continue

        import_definition = []
        if module in parsed.as_map["straight"]:
            if parsed.imports[section]["straight"][module]:
                import_definition.append((f"{import_type} {module}", module))
            import_definition.extend(
                (f"{import_type} {module} as {as_import}", f"{module} as {as_import}")
                for as_import in parsed.as_map["straight"][module]
            )
        else:
            import_definition.append((f"{import_type} {module}", module))

        comments_above = parsed.categorized_comments["above"]["straight"].pop(module, None)
        if comments_above:
            output.extend(comments_above)
        output.extend(
            with_comments(
                parsed.categorized_comments["straight"].get(imodule),
                idef,
                removed=config.ignore_comments,
                comment_prefix=config.comment_prefix,
            )
            for idef, imodule in import_definition
        )

    return output


def _output_as_string(lines: list[str], line_separator: str) -> str:
    return line_separator.join(_normalize_empty_lines(lines))


def _normalize_empty_lines(lines: list[str]) -> list[str]:
    while lines and lines[-1].strip() == "":
        lines.pop(-1)

    lines.append("")
    return lines


class _LineWithComments(str):
    comments: list[str]

    def __new__(
        cls: type["_LineWithComments"], value: Any, comments: list[str]
    ) -> "_LineWithComments":
        instance = super().__new__(cls, value)
        instance.comments = comments
        return instance


def _ensure_newline_before_comment(output: list[str]) -> list[str]:
    new_output: list[str] = []

    def is_comment(line: str | None) -> bool:
        return line.startswith("#") if line else False

    for line, prev_line in zip(output, [None, *output], strict=False):
        if is_comment(line) and prev_line != "" and not is_comment(prev_line):
            new_output.append("")
        new_output.append(line)
    return new_output


def _with_star_comments(parsed: parse.ParsedContent, module: str, comments: list[str]) -> list[str]:
    star_comment = parsed.categorized_comments["nested"].get(module, {}).pop("*", None)
    if star_comment:
        return [*comments, star_comment]
    return comments
