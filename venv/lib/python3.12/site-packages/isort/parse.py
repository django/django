"""Defines parsing functions used by isort for parsing import definitions"""

import re
from collections import OrderedDict, defaultdict
from functools import partial
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Set, Tuple
from warnings import warn

from . import place
from .comments import parse as parse_comments
from .exceptions import MissingSection
from .settings import DEFAULT_CONFIG, Config

if TYPE_CHECKING:
    from mypy_extensions import TypedDict

    CommentsAboveDict = TypedDict(
        "CommentsAboveDict", {"straight": Dict[str, Any], "from": Dict[str, Any]}
    )

    CommentsDict = TypedDict(
        "CommentsDict",
        {
            "from": Dict[str, Any],
            "straight": Dict[str, Any],
            "nested": Dict[str, Any],
            "above": CommentsAboveDict,
        },
    )


def _infer_line_separator(contents: str) -> str:
    if "\r\n" in contents:
        return "\r\n"
    if "\r" in contents:
        return "\r"
    return "\n"


def normalize_line(raw_line: str) -> Tuple[str, str]:
    """Normalizes import related statements in the provided line.

    Returns (normalized_line: str, raw_line: str)
    """
    line = re.sub(r"from(\.+)cimport ", r"from \g<1> cimport ", raw_line)
    line = re.sub(r"from(\.+)import ", r"from \g<1> import ", line)
    line = line.replace("import*", "import *")
    line = re.sub(r" (\.+)import ", r" \g<1> import ", line)
    line = re.sub(r" (\.+)cimport ", r" \g<1> cimport ", line)
    line = line.replace("\t", " ")
    return line, raw_line


def import_type(line: str, config: Config = DEFAULT_CONFIG) -> Optional[str]:
    """If the current line is an import line it will return its type (from or straight)"""
    if config.honor_noqa and line.lower().rstrip().endswith("noqa"):
        return None
    if "isort:skip" in line or "isort: skip" in line or "isort: split" in line:
        return None
    if line.startswith(("import ", "cimport ")):
        return "straight"
    if line.startswith("from "):
        return "from"
    return None


def strip_syntax(import_string: str) -> str:
    import_string = import_string.replace("_import", "[[i]]")
    import_string = import_string.replace("_cimport", "[[ci]]")
    for remove_syntax in ["\\", "(", ")", ","]:
        import_string = import_string.replace(remove_syntax, " ")
    import_list = import_string.split()
    for key in ("from", "import", "cimport"):
        if key in import_list:
            import_list.remove(key)
    import_string = " ".join(import_list)
    import_string = import_string.replace("[[i]]", "_import")
    import_string = import_string.replace("[[ci]]", "_cimport")
    return import_string.replace("{ ", "{|").replace(" }", "|}")


def skip_line(
    line: str,
    in_quote: str,
    index: int,
    section_comments: Tuple[str, ...],
    needs_import: bool = True,
) -> Tuple[bool, str]:
    """Determine if a given line should be skipped.

    Returns back a tuple containing:

    (skip_line: bool,
     in_quote: str,)
    """
    should_skip = bool(in_quote)
    if '"' in line or "'" in line:
        char_index = 0
        while char_index < len(line):
            if line[char_index] == "\\":
                char_index += 1
            elif in_quote:
                if line[char_index : char_index + len(in_quote)] == in_quote:
                    in_quote = ""
            elif line[char_index] in ("'", '"'):
                long_quote = line[char_index : char_index + 3]
                if long_quote in ('"""', "'''"):
                    in_quote = long_quote
                    char_index += 2
                else:
                    in_quote = line[char_index]
            elif line[char_index] == "#":
                break
            char_index += 1

    if ";" in line.split("#")[0] and needs_import:
        for part in (part.strip() for part in line.split(";")):
            if (
                part
                and not part.startswith("from ")
                and not part.startswith(("import ", "cimport "))
            ):
                should_skip = True

    return (bool(should_skip or in_quote), in_quote)


class ParsedContent(NamedTuple):
    in_lines: List[str]
    lines_without_imports: List[str]
    import_index: int
    place_imports: Dict[str, List[str]]
    import_placements: Dict[str, str]
    as_map: Dict[str, Dict[str, List[str]]]
    imports: Dict[str, Dict[str, Any]]
    categorized_comments: "CommentsDict"
    change_count: int
    original_line_count: int
    line_separator: str
    sections: Any
    verbose_output: List[str]
    trailing_commas: Set[str]


def file_contents(contents: str, config: Config = DEFAULT_CONFIG) -> ParsedContent:
    """Parses a python file taking out and categorizing imports."""
    line_separator: str = config.line_ending or _infer_line_separator(contents)
    in_lines = contents.splitlines()
    if contents and contents[-1] in ("\n", "\r"):
        in_lines.append("")

    out_lines = []
    original_line_count = len(in_lines)
    if config.old_finders:
        from .deprecated.finders import FindersManager

        finder = FindersManager(config=config).find
    else:
        finder = partial(place.module, config=config)

    line_count = len(in_lines)

    place_imports: Dict[str, List[str]] = {}
    import_placements: Dict[str, str] = {}
    as_map: Dict[str, Dict[str, List[str]]] = {
        "straight": defaultdict(list),
        "from": defaultdict(list),
    }
    imports: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    verbose_output: List[str] = []

    for section in chain(config.sections, config.forced_separate):
        imports[section] = {"straight": OrderedDict(), "from": OrderedDict()}
    categorized_comments: CommentsDict = {
        "from": {},
        "straight": {},
        "nested": {},
        "above": {"straight": {}, "from": {}},
    }

    trailing_commas: Set[str] = set()

    index = 0
    import_index = -1
    in_quote = ""
    while index < line_count:
        line = in_lines[index]
        index += 1
        statement_index = index
        (skipping_line, in_quote) = skip_line(
            line, in_quote=in_quote, index=index, section_comments=config.section_comments
        )

        if (
            line in config.section_comments or line in config.section_comments_end
        ) and not skipping_line:
            if import_index == -1:  # pragma: no branch
                import_index = index - 1
            continue

        if "isort:imports-" in line and line.startswith("#"):
            section = line.split("isort:imports-")[-1].split()[0].upper()
            place_imports[section] = []
            import_placements[line] = section
        elif "isort: imports-" in line and line.startswith("#"):
            section = line.split("isort: imports-")[-1].split()[0].upper()
            place_imports[section] = []
            import_placements[line] = section

        if skipping_line:
            out_lines.append(line)
            continue

        lstripped_line = line.lstrip()
        if (
            config.float_to_top
            and import_index == -1
            and line
            and not in_quote
            and not lstripped_line.startswith("#")
            and not lstripped_line.startswith("'''")
            and not lstripped_line.startswith('"""')
        ):
            if not lstripped_line.startswith("import") and not lstripped_line.startswith("from"):
                import_index = index - 1
                while import_index and not in_lines[import_index - 1]:
                    import_index -= 1
            else:
                commentless = line.split("#", 1)[0].strip()
                if (
                    ("isort:skip" in line or "isort: skip" in line)
                    and "(" in commentless
                    and ")" not in commentless
                ):
                    import_index = index

                    starting_line = line
                    while "isort:skip" in starting_line or "isort: skip" in starting_line:
                        commentless = starting_line.split("#", 1)[0]
                        if (
                            "(" in commentless
                            and not commentless.rstrip().endswith(")")
                            and import_index < line_count
                        ):
                            while import_index < line_count and not commentless.rstrip().endswith(
                                ")"
                            ):
                                commentless = in_lines[import_index].split("#", 1)[0]
                                import_index += 1
                        else:
                            import_index += 1

                        if import_index >= line_count:
                            break

                        starting_line = in_lines[import_index]

        line, *end_of_line_comment = line.split("#", 1)
        if ";" in line:
            statements = [line.strip() for line in line.split(";")]
        else:
            statements = [line]
        if end_of_line_comment:
            statements[-1] = f"{statements[-1]}#{end_of_line_comment[0]}"

        for statement in statements:
            line, raw_line = normalize_line(statement)
            type_of_import = import_type(line, config) or ""
            raw_lines = [raw_line]
            if not type_of_import:
                out_lines.append(raw_line)
                continue

            if import_index == -1:
                import_index = index - 1
            nested_comments = {}
            import_string, comment = parse_comments(line)
            comments = [comment] if comment else []
            line_parts = [part for part in strip_syntax(import_string).strip().split(" ") if part]
            if type_of_import == "from" and len(line_parts) == 2 and comments:
                nested_comments[line_parts[-1]] = comments[0]

            if "(" in line.split("#", 1)[0] and index < line_count:
                while not line.split("#")[0].strip().endswith(")") and index < line_count:
                    line, new_comment = parse_comments(in_lines[index])
                    index += 1
                    if new_comment:
                        comments.append(new_comment)
                    stripped_line = strip_syntax(line).strip()
                    if (
                        type_of_import == "from"
                        and stripped_line
                        and " " not in stripped_line.replace(" as ", "")
                        and new_comment
                    ):
                        nested_comments[stripped_line] = comments[-1]
                    import_string += line_separator + line
                    raw_lines.append(line)
            else:
                while line.strip().endswith("\\"):
                    line, new_comment = parse_comments(in_lines[index])
                    line = line.lstrip()
                    index += 1
                    if new_comment:
                        comments.append(new_comment)

                    # Still need to check for parentheses after an escaped line
                    if (
                        "(" in line.split("#")[0]
                        and ")" not in line.split("#")[0]
                        and index < line_count
                    ):
                        stripped_line = strip_syntax(line).strip()
                        if (
                            type_of_import == "from"
                            and stripped_line
                            and " " not in stripped_line.replace(" as ", "")
                            and new_comment
                        ):
                            nested_comments[stripped_line] = comments[-1]
                        import_string += line_separator + line
                        raw_lines.append(line)

                        while not line.split("#")[0].strip().endswith(")") and index < line_count:
                            line, new_comment = parse_comments(in_lines[index])
                            index += 1
                            if new_comment:
                                comments.append(new_comment)
                            stripped_line = strip_syntax(line).strip()
                            if (
                                type_of_import == "from"
                                and stripped_line
                                and " " not in stripped_line.replace(" as ", "")
                                and new_comment
                            ):
                                nested_comments[stripped_line] = comments[-1]
                            import_string += line_separator + line
                            raw_lines.append(line)

                    stripped_line = strip_syntax(line).strip()
                    if (
                        type_of_import == "from"
                        and stripped_line
                        and " " not in stripped_line.replace(" as ", "")
                        and new_comment
                    ):
                        nested_comments[stripped_line] = comments[-1]
                    if import_string.strip().endswith(
                        (" import", " cimport")
                    ) or line.strip().startswith(("import ", "cimport ")):
                        import_string += line_separator + line
                    else:
                        import_string = import_string.rstrip().rstrip("\\") + " " + line.lstrip()

            if type_of_import == "from":
                cimports: bool
                import_string = (
                    import_string.replace("import(", "import (")
                    .replace("\\", " ")
                    .replace("\n", " ")
                )
                if "import " not in import_string:
                    out_lines.extend(raw_lines)
                    continue

                if " cimport " in import_string:
                    parts = import_string.split(" cimport ")
                    cimports = True

                else:
                    parts = import_string.split(" import ")
                    cimports = False

                from_import = parts[0].split(" ")
                import_string = (" cimport " if cimports else " import ").join(
                    [from_import[0] + " " + "".join(from_import[1:])] + parts[1:]
                )

            just_imports = [
                item.replace("{|", "{ ").replace("|}", " }")
                for item in strip_syntax(import_string).split()
            ]

            attach_comments_to: Optional[List[Any]] = None
            direct_imports = just_imports[1:]
            straight_import = True
            top_level_module = ""
            if "as" in just_imports and (just_imports.index("as") + 1) < len(just_imports):
                straight_import = False
                while "as" in just_imports:
                    nested_module = None
                    as_index = just_imports.index("as")
                    if type_of_import == "from":
                        nested_module = just_imports[as_index - 1]
                        top_level_module = just_imports[0]
                        module = top_level_module + "." + nested_module
                        as_name = just_imports[as_index + 1]
                        direct_imports.remove(nested_module)
                        direct_imports.remove(as_name)
                        direct_imports.remove("as")
                        if nested_module == as_name and config.remove_redundant_aliases:
                            pass
                        elif as_name not in as_map["from"][module]:  # pragma: no branch
                            as_map["from"][module].append(as_name)

                        full_name = f"{nested_module} as {as_name}"
                        associated_comment = nested_comments.get(full_name)
                        if associated_comment:
                            categorized_comments["nested"].setdefault(top_level_module, {})[
                                full_name
                            ] = associated_comment
                            if associated_comment in comments:  # pragma: no branch
                                comments.pop(comments.index(associated_comment))
                    else:
                        module = just_imports[as_index - 1]
                        as_name = just_imports[as_index + 1]
                        if module == as_name and config.remove_redundant_aliases:
                            pass
                        elif as_name not in as_map["straight"][module]:
                            as_map["straight"][module].append(as_name)

                    if comments and attach_comments_to is None:
                        if nested_module and config.combine_as_imports:
                            attach_comments_to = categorized_comments["from"].setdefault(
                                f"{top_level_module}.__combined_as__", []
                            )
                        else:
                            if type_of_import == "from" or (
                                config.remove_redundant_aliases and as_name == module.split(".")[-1]
                            ):
                                attach_comments_to = categorized_comments["straight"].setdefault(
                                    module, []
                                )
                            else:
                                attach_comments_to = categorized_comments["straight"].setdefault(
                                    f"{module} as {as_name}", []
                                )
                    del just_imports[as_index : as_index + 2]

            if type_of_import == "from":
                import_from = just_imports.pop(0)
                placed_module = finder(import_from)
                if config.verbose and not config.only_modified:
                    print(f"from-type place_module for {import_from} returned {placed_module}")

                elif config.verbose:
                    verbose_output.append(
                        f"from-type place_module for {import_from} returned {placed_module}"
                    )
                if placed_module == "":
                    warn(
                        f"could not place module {import_from} of line {line} --"
                        " Do you need to define a default section?",
                        stacklevel=2,
                    )

                if placed_module and placed_module not in imports:
                    raise MissingSection(import_module=import_from, section=placed_module)

                root = imports[placed_module][type_of_import]  # type: ignore
                for import_name in just_imports:
                    associated_comment = nested_comments.get(import_name)
                    if associated_comment:
                        categorized_comments["nested"].setdefault(import_from, {})[
                            import_name
                        ] = associated_comment
                        if associated_comment in comments:  # pragma: no branch
                            comments.pop(comments.index(associated_comment))
                if (
                    config.force_single_line
                    and comments
                    and attach_comments_to is None
                    and len(just_imports) == 1
                ):
                    nested_from_comments = categorized_comments["nested"].setdefault(
                        import_from, {}
                    )
                    existing_comment = nested_from_comments.get(just_imports[0], "")
                    nested_from_comments[just_imports[0]] = (
                        f"{existing_comment}{'; ' if existing_comment else ''}{'; '.join(comments)}"
                    )
                    comments = []

                if comments and attach_comments_to is None:
                    attach_comments_to = categorized_comments["from"].setdefault(import_from, [])

                if len(out_lines) > max(import_index, 1) - 1:
                    last = out_lines[-1].rstrip() if out_lines else ""
                    while (
                        last.startswith("#")
                        and not last.endswith('"""')
                        and not last.endswith("'''")
                        and "isort:imports-" not in last
                        and "isort: imports-" not in last
                        and not config.treat_all_comments_as_code
                        and last.strip() not in config.treat_comments_as_code
                    ):
                        categorized_comments["above"]["from"].setdefault(import_from, []).insert(
                            0, out_lines.pop(-1)
                        )
                        if out_lines:
                            last = out_lines[-1].rstrip()
                        else:
                            last = ""
                    if statement_index - 1 == import_index:  # pragma: no cover
                        import_index -= len(
                            categorized_comments["above"]["from"].get(import_from, [])
                        )

                if import_from not in root:
                    root[import_from] = OrderedDict(
                        (module, module in direct_imports) for module in just_imports
                    )
                else:
                    root[import_from].update(
                        (module, root[import_from].get(module, False) or module in direct_imports)
                        for module in just_imports
                    )

                if comments and attach_comments_to is not None:
                    attach_comments_to.extend(comments)

                if (
                    just_imports
                    and just_imports[-1]
                    and "," in import_string.split(just_imports[-1])[-1]
                ):
                    trailing_commas.add(import_from)
            else:
                if comments and attach_comments_to is not None:
                    attach_comments_to.extend(comments)
                    comments = []

                for module in just_imports:
                    if comments:
                        categorized_comments["straight"][module] = comments
                        comments = []

                    if len(out_lines) > max(import_index, +1, 1) - 1:
                        last = out_lines[-1].rstrip() if out_lines else ""
                        while (
                            last.startswith("#")
                            and not last.endswith('"""')
                            and not last.endswith("'''")
                            and "isort:imports-" not in last
                            and "isort: imports-" not in last
                            and not config.treat_all_comments_as_code
                            and last.strip() not in config.treat_comments_as_code
                        ):
                            categorized_comments["above"]["straight"].setdefault(module, []).insert(
                                0, out_lines.pop(-1)
                            )
                            if out_lines:
                                last = out_lines[-1].rstrip()
                            else:
                                last = ""
                        if index - 1 == import_index:
                            import_index -= len(
                                categorized_comments["above"]["straight"].get(module, [])
                            )
                    placed_module = finder(module)
                    if config.verbose and not config.only_modified:
                        print(f"else-type place_module for {module} returned {placed_module}")

                    elif config.verbose:
                        verbose_output.append(
                            f"else-type place_module for {module} returned {placed_module}"
                        )
                    if placed_module == "":
                        warn(
                            f"could not place module {module} of line {line} --"
                            " Do you need to define a default section?",
                            stacklevel=2,
                        )
                        imports.setdefault("", {"straight": OrderedDict(), "from": OrderedDict()})

                    if placed_module and placed_module not in imports:
                        raise MissingSection(import_module=module, section=placed_module)

                    straight_import |= imports[placed_module][type_of_import].get(  # type: ignore
                        module, False
                    )
                    imports[placed_module][type_of_import][module] = straight_import  # type: ignore

    change_count = len(out_lines) - original_line_count

    return ParsedContent(
        in_lines=in_lines,
        lines_without_imports=out_lines,
        import_index=import_index,
        place_imports=place_imports,
        import_placements=import_placements,
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
        change_count=change_count,
        original_line_count=original_line_count,
        line_separator=line_separator,
        sections=config.sections,
        verbose_output=verbose_output,
        trailing_commas=trailing_commas,
    )
