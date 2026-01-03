from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, TypeVar, Union

from black.nodes import Visitor
from black.output import out
from black.parsing import lib2to3_parse
from blib2to3.pgen2 import token
from blib2to3.pytree import Leaf, Node, type_repr

LN = Union[Leaf, Node]
T = TypeVar("T")


@dataclass
class DebugVisitor(Visitor[T]):
    tree_depth: int = 0
    list_output: list[str] = field(default_factory=list)
    print_output: bool = True

    def out(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.list_output.append(message)
        if self.print_output:
            out(message, *args, **kwargs)

    def visit_default(self, node: LN) -> Iterator[T]:
        indent = " " * (2 * self.tree_depth)
        if isinstance(node, Node):
            _type = type_repr(node.type)
            self.out(f"{indent}{_type}", fg="yellow")
            self.tree_depth += 1
            for child in node.children:
                yield from self.visit(child)

            self.tree_depth -= 1
            self.out(f"{indent}/{_type}", fg="yellow", bold=False)
        else:
            _type = token.tok_name.get(node.type, str(node.type))
            self.out(f"{indent}{_type}", fg="blue", nl=False)
            if node.prefix:
                # We don't have to handle prefixes for `Node` objects since
                # that delegates to the first child anyway.
                self.out(f" {node.prefix!r}", fg="green", bold=False, nl=False)
            self.out(f" {node.value!r}", fg="blue", bold=False)

    @classmethod
    def show(cls, code: str | Leaf | Node) -> None:
        """Pretty-print the lib2to3 AST of a given string of `code`.

        Convenience method for debugging.
        """
        v: DebugVisitor[None] = DebugVisitor()
        if isinstance(code, str):
            code = lib2to3_parse(code)
        list(v.visit(code))
