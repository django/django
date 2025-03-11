import textwrap
from io import StringIO
from itertools import chain
from typing import List, TextIO, Union

import isort.literal
from isort.settings import DEFAULT_CONFIG, Config

from . import output, parse
from .exceptions import ExistingSyntaxErrors, FileSkipComment
from .format import format_natural, remove_whitespace
from .settings import FILE_SKIP_COMMENTS

CIMPORT_IDENTIFIERS = ("cimport ", "cimport*", "from.cimport")
IMPORT_START_IDENTIFIERS = ("from ", "from.import", "import ", "import*", *CIMPORT_IDENTIFIERS)
DOCSTRING_INDICATORS = ('"""', "'''")
COMMENT_INDICATORS = (*DOCSTRING_INDICATORS, "'", '"', "#")
CODE_SORT_COMMENTS = (
    "# isort: list",
    "# isort: dict",
    "# isort: set",
    "# isort: unique-list",
    "# isort: tuple",
    "# isort: unique-tuple",
    "# isort: assignments",
)
LITERAL_TYPE_MAPPING = {"(": "tuple", "[": "list", "{": "set"}


# Ignore DeepSource cyclomatic complexity check for this function.
# skipcq: PY-R1000
def process(
    input_stream: TextIO,
    output_stream: TextIO,
    extension: str = "py",
    raise_on_skip: bool = True,
    config: Config = DEFAULT_CONFIG,
) -> bool:
    """Parses stream identifying sections of contiguous imports and sorting them

    Code with unsorted imports is read from the provided `input_stream`, sorted and then
    outputted to the specified `output_stream`.

    - `input_stream`: Text stream with unsorted import sections.
    - `output_stream`: Text stream to output sorted inputs into.
    - `config`: Config settings to use when sorting imports. Defaults settings.
        - *Default*: `isort.settings.DEFAULT_CONFIG`.
    - `extension`: The file extension or file extension rules that should be used.
        - *Default*: `"py"`.
        - *Choices*: `["py", "pyi", "pyx"]`.

    Returns `True` if there were changes that needed to be made (errors present) from what
    was provided in the input_stream, otherwise `False`.
    """
    line_separator: str = config.line_ending
    add_imports: List[str] = [format_natural(addition) for addition in config.add_imports]
    import_section: str = ""
    next_import_section: str = ""
    next_cimports: bool = False
    in_quote: str = ""
    was_in_quote: bool = False
    first_comment_index_start: int = -1
    first_comment_index_end: int = -1
    contains_imports: bool = False
    in_top_comment: bool = False
    first_import_section: bool = True
    indent: str = ""
    isort_off: bool = False
    skip_file: bool = False
    code_sorting: Union[bool, str] = False
    code_sorting_section: str = ""
    code_sorting_indent: str = ""
    cimports: bool = False
    made_changes: bool = False
    stripped_line: str = ""
    end_of_file: bool = False
    verbose_output: List[str] = []
    lines_before: List[str] = []
    is_reexport: bool = False
    reexport_rollback: int = 0

    if config.float_to_top:
        new_input = ""
        current = ""
        isort_off = False
        for line in chain(input_stream, (None,)):
            if isort_off and line is not None:
                if line == "# isort: on\n":
                    isort_off = False
                new_input += line
            elif line in ("# isort: split\n", "# isort: off\n", None) or str(line).endswith(
                "# isort: split\n"
            ):
                if line == "# isort: off\n":
                    isort_off = True
                if current:
                    if add_imports:
                        add_line_separator = line_separator or "\n"
                        current += add_line_separator + add_line_separator.join(add_imports)
                        add_imports = []
                    parsed = parse.file_contents(current, config=config)
                    verbose_output += parsed.verbose_output
                    extra_space = ""
                    while current and current[-1] == "\n":
                        extra_space += "\n"
                        current = current[:-1]
                    extra_space = extra_space.replace("\n", "", 1)
                    sorted_output = output.sorted_imports(
                        parsed, config, extension, import_type="import"
                    )
                    made_changes = made_changes or _has_changed(
                        before=current,
                        after=sorted_output,
                        line_separator=parsed.line_separator,
                        ignore_whitespace=config.ignore_whitespace,
                    )
                    new_input += sorted_output
                    new_input += extra_space
                    current = ""
                new_input += line or ""
            else:
                current += line or ""

        input_stream = StringIO(new_input)

    for index, line in enumerate(chain(input_stream, (None,))):
        if line is None:
            if index == 0 and not config.force_adds:
                return False

            not_imports = True
            end_of_file = True
            line = ""
            if not line_separator:
                line_separator = "\n"

            if code_sorting and code_sorting_section:
                if is_reexport:
                    output_stream.seek(output_stream.tell() - reexport_rollback)
                    reexport_rollback = 0
                sorted_code = textwrap.indent(
                    isort.literal.assignment(
                        code_sorting_section,
                        str(code_sorting),
                        extension,
                        config=_indented_config(config, indent),
                    ),
                    code_sorting_indent,
                )
                made_changes = made_changes or _has_changed(
                    before=code_sorting_section,
                    after=sorted_code,
                    line_separator=line_separator,
                    ignore_whitespace=config.ignore_whitespace,
                )
                output_stream.write(sorted_code)
                if is_reexport:
                    output_stream.truncate()
        else:
            stripped_line = line.strip()
            if stripped_line and not line_separator:
                line_separator = line[len(line.rstrip()) :].replace(" ", "").replace("\t", "")

            for file_skip_comment in FILE_SKIP_COMMENTS:
                if file_skip_comment in line:
                    if raise_on_skip:
                        raise FileSkipComment("Passed in content")
                    isort_off = True
                    skip_file = True

            if not in_quote:
                if stripped_line == "# isort: off":
                    isort_off = True
                elif stripped_line.startswith("# isort: dont-add-imports"):
                    add_imports = []
                elif stripped_line.startswith("# isort: dont-add-import:"):
                    import_not_to_add = stripped_line.split("# isort: dont-add-import:", 1)[
                        1
                    ].strip()
                    add_imports = [
                        import_to_add
                        for import_to_add in add_imports
                        if import_to_add != import_not_to_add
                    ]

            if (
                (index == 0 or (index in {1, 2} and not contains_imports))
                and stripped_line.startswith("#")
                and stripped_line not in config.section_comments
                and stripped_line not in CODE_SORT_COMMENTS
            ):
                in_top_comment = True
            elif in_top_comment and (
                not line.startswith("#")
                or stripped_line in config.section_comments
                or stripped_line in CODE_SORT_COMMENTS
            ):
                in_top_comment = False
                first_comment_index_end = index - 1

            was_in_quote = bool(in_quote)
            if ((not stripped_line.startswith("#") or in_quote) and '"' in line) or "'" in line:
                char_index = 0
                if first_comment_index_start == -1 and line.startswith(('"', "'")):
                    first_comment_index_start = index
                while char_index < len(line):
                    if line[char_index] == "\\":
                        char_index += 1
                    elif in_quote:
                        if line[char_index : char_index + len(in_quote)] == in_quote:
                            in_quote = ""
                            if first_comment_index_end < first_comment_index_start:
                                first_comment_index_end = index
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

            not_imports = bool(in_quote) or was_in_quote or in_top_comment or isort_off
            if not (in_quote or was_in_quote or in_top_comment):
                if isort_off:
                    if not skip_file and stripped_line == "# isort: on":
                        isort_off = False
                elif stripped_line.endswith("# isort: split"):
                    not_imports = True
                elif stripped_line in CODE_SORT_COMMENTS:
                    code_sorting = stripped_line.split("isort: ")[1].strip()
                    code_sorting_indent = line[: -len(line.lstrip())]
                    not_imports = True
                elif config.sort_reexports and stripped_line.startswith("__all__"):
                    _, rhs = stripped_line.split("=")
                    code_sorting = LITERAL_TYPE_MAPPING.get(rhs.lstrip()[0], "tuple")
                    code_sorting_indent = line[: -len(line.lstrip())]
                    not_imports = True
                    code_sorting_section += line
                    reexport_rollback = len(line)
                    is_reexport = True
                elif code_sorting:
                    if not stripped_line:
                        sorted_code = textwrap.indent(
                            isort.literal.assignment(
                                code_sorting_section,
                                str(code_sorting),
                                extension,
                                config=_indented_config(config, indent),
                            ),
                            code_sorting_indent,
                        )
                        made_changes = made_changes or _has_changed(
                            before=code_sorting_section,
                            after=sorted_code,
                            line_separator=line_separator,
                            ignore_whitespace=config.ignore_whitespace,
                        )
                        if is_reexport:
                            output_stream.seek(output_stream.tell() - reexport_rollback)
                            reexport_rollback = 0
                        output_stream.write(sorted_code)
                        if is_reexport:
                            output_stream.truncate()
                        not_imports = True
                        code_sorting = False
                        code_sorting_section = ""
                        code_sorting_indent = ""
                        is_reexport = False
                    else:
                        code_sorting_section += line
                        line = ""
                elif (
                    stripped_line in config.section_comments
                    or stripped_line in config.section_comments_end
                ):
                    if import_section and not contains_imports:
                        output_stream.write(import_section)
                        import_section = line
                        not_imports = False
                    else:
                        import_section += line
                    indent = line[: -len(line.lstrip())]
                elif not (stripped_line or contains_imports):
                    not_imports = True
                elif not stripped_line or (
                    stripped_line.startswith("#")
                    and (not indent or indent + line.lstrip() == line)
                    and not config.treat_all_comments_as_code
                    and stripped_line not in config.treat_comments_as_code
                ):
                    import_section += line
                elif stripped_line.startswith(IMPORT_START_IDENTIFIERS):
                    new_indent = line[: -len(line.lstrip())]
                    import_statement = line
                    stripped_line = line.strip().split("#")[0]
                    while stripped_line.endswith("\\") or (
                        "(" in stripped_line and ")" not in stripped_line
                    ):
                        if stripped_line.endswith("\\"):
                            while stripped_line and stripped_line.endswith("\\"):
                                line = input_stream.readline()
                                stripped_line = line.strip().split("#")[0]
                                import_statement += line
                        else:
                            while ")" not in stripped_line:
                                line = input_stream.readline()

                                if not line:  # end of file without closing parenthesis
                                    raise ExistingSyntaxErrors("Parenthesis is not closed")

                                stripped_line = line.strip().split("#")[0]
                                import_statement += line

                    if (
                        import_statement.lstrip().startswith("from")
                        and "import" not in import_statement
                    ):
                        line = import_statement
                        not_imports = True
                    else:
                        did_contain_imports = contains_imports
                        contains_imports = True

                        cimport_statement: bool = False
                        if (
                            import_statement.lstrip().startswith(CIMPORT_IDENTIFIERS)
                            or " cimport " in import_statement
                            or " cimport*" in import_statement
                            or " cimport(" in import_statement
                            or (
                                ".cimport" in import_statement
                                and "cython.cimports" not in import_statement
                            )  # Allow pure python imports. See #2062
                        ):
                            cimport_statement = True

                        if cimport_statement != cimports or (
                            new_indent != indent
                            and import_section
                            and (not did_contain_imports or len(new_indent) < len(indent))
                        ):
                            indent = new_indent
                            if import_section:
                                next_cimports = cimport_statement
                                next_import_section = import_statement
                                import_statement = ""
                                not_imports = True
                                line = ""
                            else:
                                cimports = cimport_statement
                        else:
                            if new_indent != indent:
                                if import_section and did_contain_imports:
                                    import_statement = indent + import_statement.lstrip()
                                else:
                                    indent = new_indent
                        import_section += import_statement
                else:
                    not_imports = True

        if not_imports:
            if not was_in_quote and config.lines_before_imports > -1:
                if line.strip() == "":
                    lines_before += line
                    continue
                if not import_section:
                    output_stream.write("".join(lines_before))
                lines_before = []

            raw_import_section: str = import_section
            if (
                add_imports
                and (stripped_line or end_of_file)
                and not config.append_only
                and not in_top_comment
                and not was_in_quote
                and not import_section
                and not line.lstrip().startswith(COMMENT_INDICATORS)
                and not (line.rstrip().endswith(DOCSTRING_INDICATORS) and "=" not in line)
            ):
                add_line_separator = line_separator or "\n"
                import_section = add_line_separator.join(add_imports) + add_line_separator
                if end_of_file and index != 0:
                    output_stream.write(add_line_separator)
                contains_imports = True
                add_imports = []

            if next_import_section and not import_section:  # pragma: no cover
                raw_import_section = import_section = next_import_section
                next_import_section = ""

            if import_section:
                if add_imports and (contains_imports or not config.append_only) and not indent:
                    import_section = (
                        line_separator.join(add_imports) + line_separator + import_section
                    )
                    contains_imports = True
                    add_imports = []

                if not indent:
                    import_section += line
                    raw_import_section += line
                if not contains_imports:
                    output_stream.write(import_section)

                else:
                    leading_whitespace = import_section[: -len(import_section.lstrip())]
                    trailing_whitespace = import_section[len(import_section.rstrip()) :]
                    if first_import_section and not import_section.lstrip(
                        line_separator
                    ).startswith(COMMENT_INDICATORS):
                        import_section = import_section.lstrip(line_separator)
                        raw_import_section = raw_import_section.lstrip(line_separator)
                        first_import_section = False

                    if indent:
                        import_section = "".join(
                            line[len(indent) :] for line in import_section.splitlines(keepends=True)
                        )

                    parsed_content = parse.file_contents(import_section, config=config)
                    verbose_output += parsed_content.verbose_output

                    sorted_import_section = output.sorted_imports(
                        parsed_content,
                        _indented_config(config, indent),
                        extension,
                        import_type="cimport" if cimports else "import",
                    )
                    if not (import_section.strip() and not sorted_import_section):
                        if indent:
                            sorted_import_section = (
                                leading_whitespace
                                + textwrap.indent(sorted_import_section, indent).strip()
                                + trailing_whitespace
                            )

                        made_changes = made_changes or _has_changed(
                            before=raw_import_section,
                            after=sorted_import_section,
                            line_separator=line_separator,
                            ignore_whitespace=config.ignore_whitespace,
                        )
                        output_stream.write(sorted_import_section)
                        if not line and not indent and next_import_section:
                            output_stream.write(line_separator)

                if indent:
                    output_stream.write(line)
                    if not next_import_section:
                        indent = ""

                if next_import_section:
                    cimports = next_cimports
                    contains_imports = True
                else:
                    contains_imports = False
                import_section = next_import_section
                next_import_section = ""
            else:
                output_stream.write(line)
                not_imports = False

            if stripped_line and not in_quote and not import_section and not next_import_section:
                if stripped_line == "yield":
                    while not stripped_line or stripped_line == "yield":
                        new_line = input_stream.readline()
                        if not new_line:
                            break

                        output_stream.write(new_line)
                        stripped_line = new_line.strip().split("#")[0]

                if stripped_line.startswith(("raise", "yield")):
                    while stripped_line.endswith("\\"):
                        new_line = input_stream.readline()
                        if not new_line:
                            break

                        output_stream.write(new_line)
                        stripped_line = new_line.strip().split("#")[0]

    if made_changes and config.only_modified:
        for output_str in verbose_output:
            print(output_str)

    return made_changes


def _indented_config(config: Config, indent: str) -> Config:
    if not indent:
        return config

    return Config(
        config=config,
        line_length=max(config.line_length - len(indent), 0),
        wrap_length=max(config.wrap_length - len(indent), 0),
        lines_after_imports=1,
        import_headings=config.import_headings if config.indented_import_headings else {},
        import_footers=config.import_footers if config.indented_import_headings else {},
    )


def _has_changed(before: str, after: str, line_separator: str, ignore_whitespace: bool) -> bool:
    if ignore_whitespace:
        return (
            remove_whitespace(before, line_separator=line_separator).strip()
            != remove_whitespace(after, line_separator=line_separator).strip()
        )
    return before.strip() != after.strip()
