import ast
from pprint import PrettyPrinter
from typing import Any, Callable, Dict, List, Set, Tuple

from isort.exceptions import (
    AssignmentsFormatMismatch,
    LiteralParsingFailure,
    LiteralSortTypeMismatch,
)
from isort.settings import DEFAULT_CONFIG, Config


class ISortPrettyPrinter(PrettyPrinter):
    """an isort customized pretty printer for sorted literals"""

    def __init__(self, config: Config):
        super().__init__(width=config.line_length, compact=True)


type_mapping: Dict[str, Tuple[type, Callable[[Any, ISortPrettyPrinter], str]]] = {}


def assignments(code: str) -> str:
    values = {}
    for line in code.splitlines(keepends=True):
        if not line.strip():
            continue
        if " = " not in line:
            raise AssignmentsFormatMismatch(code)
        variable_name, value = line.split(" = ", 1)
        values[variable_name] = value

    return "".join(
        f"{variable_name} = {values[variable_name]}" for variable_name in sorted(values.keys())
    )


def assignment(code: str, sort_type: str, extension: str, config: Config = DEFAULT_CONFIG) -> str:
    """Sorts the literal present within the provided code against the provided sort type,
    returning the sorted representation of the source code.
    """
    if sort_type == "assignments":
        return assignments(code)
    if sort_type not in type_mapping:
        raise ValueError(
            "Trying to sort using an undefined sort_type. "
            f"Defined sort types are {', '.join(type_mapping.keys())}."
        )

    variable_name, literal = code.split("=")
    variable_name = variable_name.strip()
    literal = literal.lstrip()
    try:
        value = ast.literal_eval(literal)
    except Exception as error:
        raise LiteralParsingFailure(code, error)

    expected_type, sort_function = type_mapping[sort_type]
    if type(value) is not expected_type:
        raise LiteralSortTypeMismatch(type(value), expected_type)

    printer = ISortPrettyPrinter(config)
    sorted_value_code = f"{variable_name} = {sort_function(value, printer)}"
    if config.formatting_function:
        sorted_value_code = config.formatting_function(
            sorted_value_code, extension, config
        ).rstrip()

    sorted_value_code += code[len(code.rstrip()) :]
    return sorted_value_code


def register_type(
    name: str, kind: type
) -> Callable[[Callable[[Any, ISortPrettyPrinter], str]], Callable[[Any, ISortPrettyPrinter], str]]:
    """Registers a new literal sort type."""

    def wrap(
        function: Callable[[Any, ISortPrettyPrinter], str]
    ) -> Callable[[Any, ISortPrettyPrinter], str]:
        type_mapping[name] = (kind, function)
        return function

    return wrap


@register_type("dict", dict)
def _dict(value: Dict[Any, Any], printer: ISortPrettyPrinter) -> str:
    return printer.pformat(dict(sorted(value.items(), key=lambda item: item[1])))


@register_type("list", list)
def _list(value: List[Any], printer: ISortPrettyPrinter) -> str:
    return printer.pformat(sorted(value))


@register_type("unique-list", list)
def _unique_list(value: List[Any], printer: ISortPrettyPrinter) -> str:
    return printer.pformat(sorted(set(value)))


@register_type("set", set)
def _set(value: Set[Any], printer: ISortPrettyPrinter) -> str:
    return "{" + printer.pformat(tuple(sorted(value)))[1:-1] + "}"


@register_type("tuple", tuple)
def _tuple(value: Tuple[Any, ...], printer: ISortPrettyPrinter) -> str:
    return printer.pformat(tuple(sorted(value)))


@register_type("unique-tuple", tuple)
def _unique_tuple(value: Tuple[Any, ...], printer: ISortPrettyPrinter) -> str:
    return printer.pformat(tuple(sorted(set(value))))
