"""Helpers for AST (Abstract Syntax Tree)."""

from __future__ import annotations

import ast
from typing import overload

OPERATORS: dict[type[ast.AST], str] = {
    ast.Add: "+",
    ast.And: "and",
    ast.BitAnd: "&",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Invert: "~",
    ast.LShift: "<<",
    ast.MatMult: "@",
    ast.Mult: "*",
    ast.Mod: "%",
    ast.Not: "not",
    ast.Pow: "**",
    ast.Or: "or",
    ast.RShift: ">>",
    ast.Sub: "-",
    ast.UAdd: "+",
    ast.USub: "-",
}


@overload
def unparse(node: None, code: str = '') -> None:
    ...


@overload
def unparse(node: ast.AST, code: str = '') -> str:
    ...


def unparse(node: ast.AST | None, code: str = '') -> str | None:
    """Unparse an AST to string."""
    if node is None:
        return None
    elif isinstance(node, str):
        return node
    return _UnparseVisitor(code).visit(node)


# a greatly cut-down version of `ast._Unparser`
class _UnparseVisitor(ast.NodeVisitor):
    def __init__(self, code: str = '') -> None:
        self.code = code

    def _visit_op(self, node: ast.AST) -> str:
        return OPERATORS[node.__class__]
    for _op in OPERATORS:
        locals()[f'visit_{_op.__name__}'] = _visit_op

    def visit_arg(self, node: ast.arg) -> str:
        if node.annotation:
            return f"{node.arg}: {self.visit(node.annotation)}"
        else:
            return node.arg

    def _visit_arg_with_default(self, arg: ast.arg, default: ast.AST | None) -> str:
        """Unparse a single argument to a string."""
        name = self.visit(arg)
        if default:
            if arg.annotation:
                name += " = %s" % self.visit(default)
            else:
                name += "=%s" % self.visit(default)
        return name

    def visit_arguments(self, node: ast.arguments) -> str:
        defaults: list[ast.expr | None] = list(node.defaults)
        positionals = len(node.args)
        posonlyargs = len(node.posonlyargs)
        positionals += posonlyargs
        for _ in range(len(defaults), positionals):
            defaults.insert(0, None)

        kw_defaults: list[ast.expr | None] = list(node.kw_defaults)
        for _ in range(len(kw_defaults), len(node.kwonlyargs)):
            kw_defaults.insert(0, None)

        args: list[str] = []
        for i, arg in enumerate(node.posonlyargs):
            args.append(self._visit_arg_with_default(arg, defaults[i]))

        if node.posonlyargs:
            args.append('/')

        for i, arg in enumerate(node.args):
            args.append(self._visit_arg_with_default(arg, defaults[i + posonlyargs]))

        if node.vararg:
            args.append("*" + self.visit(node.vararg))

        if node.kwonlyargs and not node.vararg:
            args.append('*')
        for i, arg in enumerate(node.kwonlyargs):
            args.append(self._visit_arg_with_default(arg, kw_defaults[i]))

        if node.kwarg:
            args.append("**" + self.visit(node.kwarg))

        return ", ".join(args)

    def visit_Attribute(self, node: ast.Attribute) -> str:
        return f"{self.visit(node.value)}.{node.attr}"

    def visit_BinOp(self, node: ast.BinOp) -> str:
        # Special case ``**`` to not have surrounding spaces.
        if isinstance(node.op, ast.Pow):
            return "".join(map(self.visit, (node.left, node.op, node.right)))
        return " ".join(self.visit(e) for e in [node.left, node.op, node.right])

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        op = " %s " % self.visit(node.op)
        return op.join(self.visit(e) for e in node.values)

    def visit_Call(self, node: ast.Call) -> str:
        args = ', '.join([self.visit(e) for e in node.args]
                         + [f"{k.arg}={self.visit(k.value)}" for k in node.keywords])
        return f"{self.visit(node.func)}({args})"

    def visit_Constant(self, node: ast.Constant) -> str:
        if node.value is Ellipsis:
            return "..."
        elif isinstance(node.value, (int, float, complex)):
            if self.code:
                return ast.get_source_segment(self.code, node) or repr(node.value)
            else:
                return repr(node.value)
        else:
            return repr(node.value)

    def visit_Dict(self, node: ast.Dict) -> str:
        keys = (self.visit(k) for k in node.keys if k is not None)
        values = (self.visit(v) for v in node.values)
        items = (k + ": " + v for k, v in zip(keys, values))
        return "{" + ", ".join(items) + "}"

    def visit_Lambda(self, node: ast.Lambda) -> str:
        return "lambda %s: ..." % self.visit(node.args)

    def visit_List(self, node: ast.List) -> str:
        return "[" + ", ".join(self.visit(e) for e in node.elts) + "]"

    def visit_Name(self, node: ast.Name) -> str:
        return node.id

    def visit_Set(self, node: ast.Set) -> str:
        return "{" + ", ".join(self.visit(e) for e in node.elts) + "}"

    def visit_Subscript(self, node: ast.Subscript) -> str:
        def is_simple_tuple(value: ast.expr) -> bool:
            return (
                isinstance(value, ast.Tuple)
                and bool(value.elts)
                and not any(isinstance(elt, ast.Starred) for elt in value.elts)
            )

        if is_simple_tuple(node.slice):
            elts = ", ".join(self.visit(e)
                             for e in node.slice.elts)  # type: ignore[attr-defined]
            return f"{self.visit(node.value)}[{elts}]"
        return f"{self.visit(node.value)}[{self.visit(node.slice)}]"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        # UnaryOp is one of {UAdd, USub, Invert, Not}, which refer to ``+x``,
        # ``-x``, ``~x``, and ``not x``. Only Not needs a space.
        if isinstance(node.op, ast.Not):
            return f"{self.visit(node.op)} {self.visit(node.operand)}"
        return f"{self.visit(node.op)}{self.visit(node.operand)}"

    def visit_Tuple(self, node: ast.Tuple) -> str:
        if len(node.elts) == 0:
            return "()"
        elif len(node.elts) == 1:
            return "(%s,)" % self.visit(node.elts[0])
        else:
            return "(" + ", ".join(self.visit(e) for e in node.elts) + ")"

    def generic_visit(self, node):
        raise NotImplementedError('Unable to parse %s object' % type(node).__name__)
