"""Fast stream based import identification.
Eventually this will likely replace parse.py
"""

from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import NamedTuple, TextIO

from isort.parse import normalize_line, skip_line, strip_syntax

from .comments import parse as parse_comments
from .settings import DEFAULT_CONFIG, Config

STATEMENT_DECLARATIONS: tuple[str, ...] = ("def ", "cdef ", "cpdef ", "class ", "@", "async def")


class Import(NamedTuple):
    line_number: int
    indented: bool
    module: str
    attribute: str | None = None
    alias: str | None = None
    cimport: bool = False
    file_path: Path | None = None

    def statement(self) -> str:
        import_cmd = "cimport" if self.cimport else "import"
        if self.attribute:
            import_string = f"from {self.module} {import_cmd} {self.attribute}"
        else:
            import_string = f"{import_cmd} {self.module}"
        if self.alias:
            import_string += f" as {self.alias}"
        return import_string

    def __str__(self) -> str:
        return (
            f"{self.file_path or ''}:{self.line_number} "
            f"{'indented ' if self.indented else ''}{self.statement()}"
        )


def imports(
    input_stream: TextIO,
    config: Config = DEFAULT_CONFIG,
    file_path: Path | None = None,
    top_only: bool = False,
) -> Iterator[Import]:
    """Parses a python file taking out and categorizing imports."""
    in_quote = ""

    indexed_input = enumerate(input_stream)
    for index, raw_line in indexed_input:
        (skipping_line, in_quote) = skip_line(
            raw_line, in_quote=in_quote, index=index, section_comments=config.section_comments
        )

        if top_only and not in_quote and raw_line.startswith(STATEMENT_DECLARATIONS):
            break
        if skipping_line:
            continue

        stripped_line = raw_line.strip().split("#")[0]
        if stripped_line.startswith(("raise", "yield")):
            if stripped_line == "yield":
                while not stripped_line or stripped_line == "yield":
                    try:
                        index, next_line = next(indexed_input)
                    except StopIteration:
                        break

                    stripped_line = next_line.strip().split("#")[0]
            while stripped_line.endswith("\\"):
                try:
                    index, next_line = next(indexed_input)
                except StopIteration:
                    break

                stripped_line = next_line.strip().split("#")[0]
            continue  # pragma: no cover

        line, *end_of_line_comment = raw_line.split("#", 1)
        statements = [line.strip() for line in line.split(";")]
        if end_of_line_comment:
            statements[-1] = f"{statements[-1]}#{end_of_line_comment[0]}"

        for statement in statements:
            line, _raw_line = normalize_line(statement)
            if line.startswith(("import ", "cimport ")):
                type_of_import = "straight"
            elif line.startswith("from "):
                type_of_import = "from"
            else:
                continue  # pragma: no cover

            import_string, _ = parse_comments(line)
            normalized_import_string = (
                import_string.replace("import(", "import (").replace("\\", " ").replace("\n", " ")
            )
            cimports: bool = (
                " cimport " in normalized_import_string
                or normalized_import_string.startswith("cimport")
            )
            identified_import = partial(
                Import,
                index + 1,  # line numbers use 1 based indexing
                raw_line.startswith((" ", "\t")),
                cimport=cimports,
                file_path=file_path,
            )

            if "(" in line.split("#", 1)[0]:
                while not line.split("#")[0].strip().endswith(")"):
                    try:
                        index, next_line = next(indexed_input)
                    except StopIteration:
                        break

                    line, _ = parse_comments(next_line)
                    import_string += "\n" + line
            else:
                while line.strip().endswith("\\"):
                    try:
                        index, next_line = next(indexed_input)
                    except StopIteration:
                        break

                    line, _ = parse_comments(next_line)

                    # Still need to check for parentheses after an escaped line
                    if "(" in line.split("#")[0] and ")" not in line.split("#")[0]:
                        import_string += "\n" + line

                        while not line.split("#")[0].strip().endswith(")"):
                            try:
                                index, next_line = next(indexed_input)
                            except StopIteration:
                                break
                            line, _ = parse_comments(next_line)
                            import_string += "\n" + line
                    else:
                        if import_string.strip().endswith(
                            (" import", " cimport")
                        ) or line.strip().startswith(("import ", "cimport ")):
                            import_string += "\n" + line
                        else:
                            import_string = (
                                import_string.rstrip().rstrip("\\") + " " + line.lstrip()
                            )

            if type_of_import == "from":
                import_string = (
                    import_string.replace("import(", "import (")
                    .replace("\\", " ")
                    .replace("\n", " ")
                )
                parts = import_string.split(" cimport " if cimports else " import ")

                from_import = parts[0].split(" ")
                import_string = (" cimport " if cimports else " import ").join(
                    [from_import[0] + " " + "".join(from_import[1:]), *parts[1:]]
                )

            just_imports = [
                item.replace("{|", "{ ").replace("|}", " }")
                for item in strip_syntax(import_string).split()
            ]

            direct_imports = just_imports[1:]
            top_level_module = ""
            if "as" in just_imports and (just_imports.index("as") + 1) < len(just_imports):
                while "as" in just_imports:
                    attribute = None
                    as_index = just_imports.index("as")
                    if type_of_import == "from":
                        attribute = just_imports[as_index - 1]
                        top_level_module = just_imports[0]
                        module = top_level_module + "." + attribute
                        alias = just_imports[as_index + 1]
                        direct_imports.remove(attribute)
                        direct_imports.remove(alias)
                        direct_imports.remove("as")
                        just_imports[1:] = direct_imports
                        if attribute == alias and config.remove_redundant_aliases:
                            yield identified_import(top_level_module, attribute)
                        else:
                            yield identified_import(top_level_module, attribute, alias=alias)

                    else:
                        module = just_imports[as_index - 1]
                        alias = just_imports[as_index + 1]
                        just_imports.remove(alias)
                        just_imports.remove("as")
                        just_imports.remove(module)
                        if module == alias and config.remove_redundant_aliases:
                            yield identified_import(module)
                        else:
                            yield identified_import(module, alias=alias)

            if just_imports:
                if type_of_import == "from":
                    module = just_imports.pop(0)
                    for attribute in just_imports:
                        yield identified_import(module, attribute)
                else:
                    for module in just_imports:
                        yield identified_import(module)
