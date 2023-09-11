"""
Parse Python code and perform AST validation.
"""
import ast
import sys
from typing import Final, Iterable, Iterator, List, Set, Tuple

from black.mode import VERSION_TO_FEATURES, Feature, TargetVersion, supports_feature
from black.nodes import syms
from blib2to3 import pygram
from blib2to3.pgen2 import driver
from blib2to3.pgen2.grammar import Grammar
from blib2to3.pgen2.parse import ParseError
from blib2to3.pgen2.tokenize import TokenError
from blib2to3.pytree import Leaf, Node

PY2_HINT: Final = "Python 2 support was removed in version 22.0."


class InvalidInput(ValueError):
    """Raised when input source code fails all parse attempts."""


def get_grammars(target_versions: Set[TargetVersion]) -> List[Grammar]:
    if not target_versions:
        # No target_version specified, so try all grammars.
        return [
            # Python 3.7-3.9
            pygram.python_grammar_no_print_statement_no_exec_statement_async_keywords,
            # Python 3.0-3.6
            pygram.python_grammar_no_print_statement_no_exec_statement,
            # Python 3.10+
            pygram.python_grammar_soft_keywords,
        ]

    grammars = []
    # If we have to parse both, try to parse async as a keyword first
    if not supports_feature(
        target_versions, Feature.ASYNC_IDENTIFIERS
    ) and not supports_feature(target_versions, Feature.PATTERN_MATCHING):
        # Python 3.7-3.9
        grammars.append(
            pygram.python_grammar_no_print_statement_no_exec_statement_async_keywords
        )
    if not supports_feature(target_versions, Feature.ASYNC_KEYWORDS):
        # Python 3.0-3.6
        grammars.append(pygram.python_grammar_no_print_statement_no_exec_statement)
    if any(Feature.PATTERN_MATCHING in VERSION_TO_FEATURES[v] for v in target_versions):
        # Python 3.10+
        grammars.append(pygram.python_grammar_soft_keywords)

    # At least one of the above branches must have been taken, because every Python
    # version has exactly one of the two 'ASYNC_*' flags
    return grammars


def lib2to3_parse(src_txt: str, target_versions: Iterable[TargetVersion] = ()) -> Node:
    """Given a string with source, return the lib2to3 Node."""
    if not src_txt.endswith("\n"):
        src_txt += "\n"

    grammars = get_grammars(set(target_versions))
    errors = {}
    for grammar in grammars:
        drv = driver.Driver(grammar)
        try:
            result = drv.parse_string(src_txt, True)
            break

        except ParseError as pe:
            lineno, column = pe.context[1]
            lines = src_txt.splitlines()
            try:
                faulty_line = lines[lineno - 1]
            except IndexError:
                faulty_line = "<line number missing in source>"
            errors[grammar.version] = InvalidInput(
                f"Cannot parse: {lineno}:{column}: {faulty_line}"
            )

        except TokenError as te:
            # In edge cases these are raised; and typically don't have a "faulty_line".
            lineno, column = te.args[1]
            errors[grammar.version] = InvalidInput(
                f"Cannot parse: {lineno}:{column}: {te.args[0]}"
            )

    else:
        # Choose the latest version when raising the actual parsing error.
        assert len(errors) >= 1
        exc = errors[max(errors)]

        if matches_grammar(src_txt, pygram.python_grammar) or matches_grammar(
            src_txt, pygram.python_grammar_no_print_statement
        ):
            original_msg = exc.args[0]
            msg = f"{original_msg}\n{PY2_HINT}"
            raise InvalidInput(msg) from None

        raise exc from None

    if isinstance(result, Leaf):
        result = Node(syms.file_input, [result])
    return result


def matches_grammar(src_txt: str, grammar: Grammar) -> bool:
    drv = driver.Driver(grammar)
    try:
        drv.parse_string(src_txt, True)
    except (ParseError, TokenError, IndentationError):
        return False
    else:
        return True


def lib2to3_unparse(node: Node) -> str:
    """Given a lib2to3 node, return its string representation."""
    code = str(node)
    return code


def parse_single_version(
    src: str, version: Tuple[int, int], *, type_comments: bool
) -> ast.AST:
    filename = "<unknown>"
    return ast.parse(
        src, filename, feature_version=version, type_comments=type_comments
    )


def parse_ast(src: str) -> ast.AST:
    # TODO: support Python 4+ ;)
    versions = [(3, minor) for minor in range(3, sys.version_info[1] + 1)]

    first_error = ""
    for version in sorted(versions, reverse=True):
        try:
            return parse_single_version(src, version, type_comments=True)
        except SyntaxError as e:
            if not first_error:
                first_error = str(e)

    # Try to parse without type comments
    for version in sorted(versions, reverse=True):
        try:
            return parse_single_version(src, version, type_comments=False)
        except SyntaxError:
            pass

    raise SyntaxError(first_error)


def _normalize(lineend: str, value: str) -> str:
    # To normalize, we strip any leading and trailing space from
    # each line...
    stripped: List[str] = [i.strip() for i in value.splitlines()]
    normalized = lineend.join(stripped)
    # ...and remove any blank lines at the beginning and end of
    # the whole string
    return normalized.strip()


def stringify_ast(node: ast.AST, depth: int = 0) -> Iterator[str]:
    """Simple visitor generating strings to compare ASTs by content."""

    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.kind == "u"
    ):
        # It's a quirk of history that we strip the u prefix over here. We used to
        # rewrite the AST nodes for Python version compatibility and we never copied
        # over the kind
        node.kind = None

    yield f"{'  ' * depth}{node.__class__.__name__}("

    for field in sorted(node._fields):  # noqa: F402
        # TypeIgnore has only one field 'lineno' which breaks this comparison
        if isinstance(node, ast.TypeIgnore):
            break

        try:
            value: object = getattr(node, field)
        except AttributeError:
            continue

        yield f"{'  ' * (depth+1)}{field}="

        if isinstance(value, list):
            for item in value:
                # Ignore nested tuples within del statements, because we may insert
                # parentheses and they change the AST.
                if (
                    field == "targets"
                    and isinstance(node, ast.Delete)
                    and isinstance(item, ast.Tuple)
                ):
                    for elt in item.elts:
                        yield from stringify_ast(elt, depth + 2)

                elif isinstance(item, ast.AST):
                    yield from stringify_ast(item, depth + 2)

        elif isinstance(value, ast.AST):
            yield from stringify_ast(value, depth + 2)

        else:
            normalized: object
            if (
                isinstance(node, ast.Constant)
                and field == "value"
                and isinstance(value, str)
            ):
                # Constant strings may be indented across newlines, if they are
                # docstrings; fold spaces after newlines when comparing. Similarly,
                # trailing and leading space may be removed.
                normalized = _normalize("\n", value)
            elif field == "type_comment" and isinstance(value, str):
                # Trailing whitespace in type comments is removed.
                normalized = value.rstrip()
            else:
                normalized = value
            yield f"{'  ' * (depth+2)}{normalized!r},  # {value.__class__.__name__}"

    yield f"{'  ' * depth})  # /{node.__class__.__name__}"
