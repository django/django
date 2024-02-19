"""Utilities parsing and analyzing Python code."""

from __future__ import annotations

import ast
import contextlib
import inspect
import itertools
import re
import tokenize
from inspect import Signature
from token import DEDENT, INDENT, NAME, NEWLINE, NUMBER, OP, STRING
from tokenize import COMMENT, NL
from typing import Any

from sphinx.pycode.ast import unparse as ast_unparse

comment_re = re.compile('^\\s*#: ?(.*)\r?\n?$')
indent_re = re.compile('^\\s*$')
emptyline_re = re.compile('^\\s*(#.*)?$')


def filter_whitespace(code: str) -> str:
    return code.replace('\f', ' ')  # replace FF (form feed) with whitespace


def get_assign_targets(node: ast.AST) -> list[ast.expr]:
    """Get list of targets from Assign and AnnAssign node."""
    if isinstance(node, ast.Assign):
        return node.targets
    else:
        return [node.target]  # type: ignore[attr-defined]


def get_lvar_names(node: ast.AST, self: ast.arg | None = None) -> list[str]:
    """Convert assignment-AST to variable names.

    This raises `TypeError` if the assignment does not create new variable::

        ary[0] = 'foo'
        dic["bar"] = 'baz'
        # => TypeError
    """
    if self:
        self_id = self.arg

    node_name = node.__class__.__name__
    if node_name in ('Constant', 'Index', 'Slice', 'Subscript'):
        raise TypeError('%r does not create new variable' % node)
    if node_name == 'Name':
        if self is None or node.id == self_id:  # type: ignore[attr-defined]
            return [node.id]  # type: ignore[attr-defined]
        else:
            raise TypeError('The assignment %r is not instance variable' % node)
    elif node_name in ('Tuple', 'List'):
        members = []
        for elt in node.elts:  # type: ignore[attr-defined]
            with contextlib.suppress(TypeError):
                members.extend(get_lvar_names(elt, self))

        return members
    elif node_name == 'Attribute':
        if (
            node.value.__class__.__name__ == 'Name' and  # type: ignore[attr-defined]
            self and node.value.id == self_id  # type: ignore[attr-defined]
        ):
            # instance variable
            return ["%s" % get_lvar_names(node.attr, self)[0]]  # type: ignore[attr-defined]
        else:
            raise TypeError('The assignment %r is not instance variable' % node)
    elif node_name == 'str':
        return [node]  # type: ignore[list-item]
    elif node_name == 'Starred':
        return get_lvar_names(node.value, self)  # type: ignore[attr-defined]
    else:
        raise NotImplementedError('Unexpected node name %r' % node_name)


def dedent_docstring(s: str) -> str:
    """Remove common leading indentation from docstring."""
    def dummy() -> None:
        # dummy function to mock `inspect.getdoc`.
        pass

    dummy.__doc__ = s
    docstring = inspect.getdoc(dummy)
    if docstring:
        return docstring.lstrip("\r\n").rstrip("\r\n")
    else:
        return ""


class Token:
    """Better token wrapper for tokenize module."""

    def __init__(self, kind: int, value: Any, start: tuple[int, int], end: tuple[int, int],
                 source: str) -> None:
        self.kind = kind
        self.value = value
        self.start = start
        self.end = end
        self.source = source

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, int):
            return self.kind == other
        elif isinstance(other, str):
            return self.value == other
        elif isinstance(other, (list, tuple)):
            return [self.kind, self.value] == list(other)
        elif other is None:
            return False
        else:
            raise ValueError('Unknown value: %r' % other)

    def match(self, *conditions: Any) -> bool:
        return any(self == candidate for candidate in conditions)

    def __repr__(self) -> str:
        return f'<Token kind={tokenize.tok_name[self.kind]!r} value={self.value.strip()!r}>'


class TokenProcessor:
    def __init__(self, buffers: list[str]) -> None:
        lines = iter(buffers)
        self.buffers = buffers
        self.tokens = tokenize.generate_tokens(lambda: next(lines))
        self.current: Token | None = None
        self.previous: Token | None = None

    def get_line(self, lineno: int) -> str:
        """Returns specified line."""
        return self.buffers[lineno - 1]

    def fetch_token(self) -> Token | None:
        """Fetch the next token from source code.

        Returns ``None`` if sequence finished.
        """
        try:
            self.previous = self.current
            self.current = Token(*next(self.tokens))
        except StopIteration:
            self.current = None

        return self.current

    def fetch_until(self, condition: Any) -> list[Token]:
        """Fetch tokens until specified token appeared.

        .. note:: This also handles parenthesis well.
        """
        tokens = []
        while current := self.fetch_token():
            tokens.append(current)
            if current == condition:
                break
            if current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])

        return tokens


class AfterCommentParser(TokenProcessor):
    """Python source code parser to pick up comments after assignments.

    This parser takes code which starts with an assignment statement,
    and returns the comment for the variable if one exists.
    """

    def __init__(self, lines: list[str]) -> None:
        super().__init__(lines)
        self.comment: str | None = None

    def fetch_rvalue(self) -> list[Token]:
        """Fetch right-hand value of assignment."""
        tokens = []
        while current := self.fetch_token():
            tokens.append(current)
            if current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])
            elif current == INDENT:
                tokens += self.fetch_until(DEDENT)
            elif current == [OP, ';']:  # NoQA: SIM114
                break
            elif current and current.kind not in {OP, NAME, NUMBER, STRING}:
                break

        return tokens

    def parse(self) -> None:
        """Parse the code and obtain comment after assignment."""
        # skip lvalue (or whole of AnnAssign)
        while (tok := self.fetch_token()) and not tok.match([OP, '='], NEWLINE, COMMENT):
            assert tok
        assert tok is not None

        # skip rvalue (if exists)
        if tok == [OP, '=']:
            self.fetch_rvalue()
            tok = self.current
            assert tok is not None

        if tok == COMMENT:
            self.comment = tok.value


class VariableCommentPicker(ast.NodeVisitor):
    """Python source code parser to pick up variable comments."""

    def __init__(self, buffers: list[str], encoding: str) -> None:
        self.counter = itertools.count()
        self.buffers = buffers
        self.encoding = encoding
        self.context: list[str] = []
        self.current_classes: list[str] = []
        self.current_function: ast.FunctionDef | None = None
        self.comments: dict[tuple[str, str], str] = {}
        self.annotations: dict[tuple[str, str], str] = {}
        self.previous: ast.AST | None = None
        self.deforders: dict[str, int] = {}
        self.finals: list[str] = []
        self.overloads: dict[str, list[Signature]] = {}
        self.typing: str | None = None
        self.typing_final: str | None = None
        self.typing_overload: str | None = None
        super().__init__()

    def get_qualname_for(self, name: str) -> list[str] | None:
        """Get qualified name for given object as a list of string(s)."""
        if self.current_function:
            if self.current_classes and self.context[-1] == "__init__":
                # store variable comments inside __init__ method of classes
                return self.context[:-1] + [name]
            else:
                return None
        else:
            return self.context + [name]

    def add_entry(self, name: str) -> None:
        qualname = self.get_qualname_for(name)
        if qualname:
            self.deforders[".".join(qualname)] = next(self.counter)

    def add_final_entry(self, name: str) -> None:
        qualname = self.get_qualname_for(name)
        if qualname:
            self.finals.append(".".join(qualname))

    def add_overload_entry(self, func: ast.FunctionDef) -> None:
        # avoid circular import problem
        from sphinx.util.inspect import signature_from_ast
        qualname = self.get_qualname_for(func.name)
        if qualname:
            overloads = self.overloads.setdefault(".".join(qualname), [])
            overloads.append(signature_from_ast(func))

    def add_variable_comment(self, name: str, comment: str) -> None:
        qualname = self.get_qualname_for(name)
        if qualname:
            basename = ".".join(qualname[:-1])
            self.comments[(basename, name)] = comment

    def add_variable_annotation(self, name: str, annotation: ast.AST) -> None:
        qualname = self.get_qualname_for(name)
        if qualname:
            basename = ".".join(qualname[:-1])
            self.annotations[(basename, name)] = ast_unparse(annotation)

    def is_final(self, decorators: list[ast.expr]) -> bool:
        final = []
        if self.typing:
            final.append('%s.final' % self.typing)
        if self.typing_final:
            final.append(self.typing_final)

        for decorator in decorators:
            try:
                if ast_unparse(decorator) in final:
                    return True
            except NotImplementedError:
                pass

        return False

    def is_overload(self, decorators: list[ast.expr]) -> bool:
        overload = []
        if self.typing:
            overload.append('%s.overload' % self.typing)
        if self.typing_overload:
            overload.append(self.typing_overload)

        for decorator in decorators:
            try:
                if ast_unparse(decorator) in overload:
                    return True
            except NotImplementedError:
                pass

        return False

    def get_self(self) -> ast.arg | None:
        """Returns the name of the first argument if in a function."""
        if self.current_function and self.current_function.args.args:
            return self.current_function.args.args[0]
        if self.current_function and self.current_function.args.posonlyargs:
            return self.current_function.args.posonlyargs[0]
        return None

    def get_line(self, lineno: int) -> str:
        """Returns specified line."""
        return self.buffers[lineno - 1]

    def visit(self, node: ast.AST) -> None:
        """Updates self.previous to the given node."""
        super().visit(node)
        self.previous = node

    def visit_Import(self, node: ast.Import) -> None:
        """Handles Import node and record the order of definitions."""
        for name in node.names:
            self.add_entry(name.asname or name.name)

            if name.name == 'typing':
                self.typing = name.asname or name.name
            elif name.name == 'typing.final':
                self.typing_final = name.asname or name.name
            elif name.name == 'typing.overload':
                self.typing_overload = name.asname or name.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handles Import node and record the order of definitions."""
        for name in node.names:
            self.add_entry(name.asname or name.name)

            if node.module == 'typing' and name.name == 'final':
                self.typing_final = name.asname or name.name
            elif node.module == 'typing' and name.name == 'overload':
                self.typing_overload = name.asname or name.name

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handles Assign node and pick up a variable comment."""
        try:
            targets = get_assign_targets(node)
            varnames: list[str] = sum(
                [get_lvar_names(t, self=self.get_self()) for t in targets], [],
            )
            current_line = self.get_line(node.lineno)
        except TypeError:
            return  # this assignment is not new definition!

        # record annotation
        if hasattr(node, 'annotation') and node.annotation:
            for varname in varnames:
                self.add_variable_annotation(varname, node.annotation)
        elif hasattr(node, 'type_comment') and node.type_comment:
            for varname in varnames:
                self.add_variable_annotation(
                    varname, node.type_comment)  # type: ignore[arg-type]

        # check comments after assignment
        parser = AfterCommentParser([current_line[node.col_offset:]] +
                                    self.buffers[node.lineno:])
        parser.parse()
        if parser.comment and comment_re.match(parser.comment):
            for varname in varnames:
                self.add_variable_comment(varname, comment_re.sub('\\1', parser.comment))
                self.add_entry(varname)
            return

        # check comments before assignment
        if indent_re.match(current_line[:node.col_offset]):
            comment_lines = []
            for i in range(node.lineno - 1):
                before_line = self.get_line(node.lineno - 1 - i)
                if comment_re.match(before_line):
                    comment_lines.append(comment_re.sub('\\1', before_line))
                else:
                    break

            if comment_lines:
                comment = dedent_docstring('\n'.join(reversed(comment_lines)))
                for varname in varnames:
                    self.add_variable_comment(varname, comment)
                    self.add_entry(varname)
                return

        # not commented (record deforders only)
        for varname in varnames:
            self.add_entry(varname)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Handles AnnAssign node and pick up a variable comment."""
        self.visit_Assign(node)  # type: ignore[arg-type]

    def visit_Expr(self, node: ast.Expr) -> None:
        """Handles Expr node and pick up a comment if string."""
        if (isinstance(self.previous, (ast.Assign, ast.AnnAssign)) and
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            try:
                targets = get_assign_targets(self.previous)
                varnames = get_lvar_names(targets[0], self.get_self())
                for varname in varnames:
                    if isinstance(node.value.value, str):
                        docstring = node.value.value
                    else:
                        docstring = node.value.value.decode(self.encoding or 'utf-8')

                    self.add_variable_comment(varname, dedent_docstring(docstring))
                    self.add_entry(varname)
            except TypeError:
                pass  # this assignment is not new definition!

    def visit_Try(self, node: ast.Try) -> None:
        """Handles Try node and processes body and else-clause.

        .. note:: pycode parser ignores objects definition in except-clause.
        """
        for subnode in node.body:
            self.visit(subnode)
        for subnode in node.orelse:
            self.visit(subnode)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handles ClassDef node and set context."""
        self.current_classes.append(node.name)
        self.add_entry(node.name)
        if self.is_final(node.decorator_list):
            self.add_final_entry(node.name)
        self.context.append(node.name)
        self.previous = node
        for child in node.body:
            self.visit(child)
        self.context.pop()
        self.current_classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handles FunctionDef node and set context."""
        if self.current_function is None:
            self.add_entry(node.name)  # should be called before setting self.current_function
            if self.is_final(node.decorator_list):
                self.add_final_entry(node.name)
            if self.is_overload(node.decorator_list):
                self.add_overload_entry(node)
            self.context.append(node.name)
            self.current_function = node
            for child in node.body:
                self.visit(child)
            self.context.pop()
            self.current_function = None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handles AsyncFunctionDef node and set context."""
        self.visit_FunctionDef(node)  # type: ignore[arg-type]


class DefinitionFinder(TokenProcessor):
    """Python source code parser to detect location of functions,
    classes and methods.
    """

    def __init__(self, lines: list[str]) -> None:
        super().__init__(lines)
        self.decorator: Token | None = None
        self.context: list[str] = []
        self.indents: list[tuple[str, str | None, int | None]] = []
        self.definitions: dict[str, tuple[str, int, int]] = {}

    def add_definition(self, name: str, entry: tuple[str, int, int]) -> None:
        """Add a location of definition."""
        if self.indents and self.indents[-1][0] == 'def' and entry[0] == 'def':
            # ignore definition of inner function
            pass
        else:
            self.definitions[name] = entry

    def parse(self) -> None:
        """Parse the code to obtain location of definitions."""
        while True:
            token = self.fetch_token()
            if token is None:
                break
            if token == COMMENT:
                pass
            elif token == [OP, '@'] and (self.previous is None or
                                         self.previous.match(NEWLINE, NL, INDENT, DEDENT)):
                if self.decorator is None:
                    self.decorator = token
            elif token.match([NAME, 'class']):
                self.parse_definition('class')
            elif token.match([NAME, 'def']):
                self.parse_definition('def')
            elif token == INDENT:
                self.indents.append(('other', None, None))
            elif token == DEDENT:
                self.finalize_block()

    def parse_definition(self, typ: str) -> None:
        """Parse AST of definition."""
        name = self.fetch_token()
        self.context.append(name.value)  # type: ignore[union-attr]
        funcname = '.'.join(self.context)

        if self.decorator:
            start_pos = self.decorator.start[0]
            self.decorator = None
        else:
            start_pos = name.start[0]  # type: ignore[union-attr]

        self.fetch_until([OP, ':'])
        if self.fetch_token().match(COMMENT, NEWLINE):  # type: ignore[union-attr]
            self.fetch_until(INDENT)
            self.indents.append((typ, funcname, start_pos))
        else:
            # one-liner
            self.add_definition(funcname,
                                (typ, start_pos, name.end[0]))  # type: ignore[union-attr]
            self.context.pop()

    def finalize_block(self) -> None:
        """Finalize definition block."""
        definition = self.indents.pop()
        if definition[0] != 'other':
            typ, funcname, start_pos = definition
            end_pos = self.current.end[0] - 1  # type: ignore[union-attr]
            while emptyline_re.match(self.get_line(end_pos)):
                end_pos -= 1

            self.add_definition(funcname, (typ, start_pos, end_pos))  # type: ignore[arg-type]
            self.context.pop()


class Parser:
    """Python source code parser to pick up variable comments.

    This is a better wrapper for ``VariableCommentPicker``.
    """

    def __init__(self, code: str, encoding: str = 'utf-8') -> None:
        self.code = filter_whitespace(code)
        self.encoding = encoding
        self.annotations: dict[tuple[str, str], str] = {}
        self.comments: dict[tuple[str, str], str] = {}
        self.deforders: dict[str, int] = {}
        self.definitions: dict[str, tuple[str, int, int]] = {}
        self.finals: list[str] = []
        self.overloads: dict[str, list[Signature]] = {}

    def parse(self) -> None:
        """Parse the source code."""
        self.parse_comments()
        self.parse_definition()

    def parse_comments(self) -> None:
        """Parse the code and pick up comments."""
        tree = ast.parse(self.code, type_comments=True)
        picker = VariableCommentPicker(self.code.splitlines(True), self.encoding)
        picker.visit(tree)
        self.annotations = picker.annotations
        self.comments = picker.comments
        self.deforders = picker.deforders
        self.finals = picker.finals
        self.overloads = picker.overloads

    def parse_definition(self) -> None:
        """Parse the location of definitions from the code."""
        parser = DefinitionFinder(self.code.splitlines(True))
        parser.parse()
        self.definitions = parser.definitions
