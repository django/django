# -*- coding: utf-8 -*-
"""
    sphinx.pycode.parser
    ~~~~~~~~~~~~~~~~~~~~

    Utilities parsing and analyzing Python code.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import ast
import inspect
import itertools
import re
import sys
import tokenize
from token import NAME, NEWLINE, INDENT, DEDENT, NUMBER, OP, STRING
from tokenize import COMMENT, NL

from six import PY2, text_type

if False:
    # For type annotation
    from typing import Any, Dict, IO, List, Tuple  # NOQA

comment_re = re.compile(u'^\\s*#: ?(.*)\r?\n?$')
indent_re = re.compile(u'^\\s*$')
emptyline_re = re.compile(u'^\\s*(#.*)?$')


if sys.version_info >= (3, 6):
    ASSIGN_NODES = (ast.Assign, ast.AnnAssign)
else:
    ASSIGN_NODES = (ast.Assign)


def filter_whitespace(code):
    # type: (unicode) -> unicode
    return code.replace('\f', ' ')  # replace FF (form feed) with whitespace


def get_assign_targets(node):
    # type: (ast.AST) -> List[ast.expr]
    """Get list of targets from Assign and AnnAssign node."""
    if isinstance(node, ast.Assign):
        return node.targets
    else:
        return [node.target]  # type: ignore


def get_lvar_names(node, self=None):
    # type: (ast.AST, ast.expr) -> List[unicode]
    """Convert assignment-AST to variable names.

    This raises `TypeError` if the assignment does not create new variable::

        ary[0] = 'foo'
        dic["bar"] = 'baz'
        # => TypeError
    """
    if self:
        if PY2:
            self_id = self.id  # type: ignore
        else:
            self_id = self.arg

    node_name = node.__class__.__name__
    if node_name in ('Index', 'Num', 'Slice', 'Str', 'Subscript'):
        raise TypeError('%r does not create new variable' % node)
    elif node_name == 'Name':
        if self is None or node.id == self_id:  # type: ignore
            return [node.id]  # type: ignore
        else:
            raise TypeError('The assignment %r is not instance variable' % node)
    elif node_name in ('Tuple', 'List'):
        members = []
        for elt in node.elts:  # type: ignore
            try:
                members.extend(get_lvar_names(elt, self))
            except TypeError:
                pass
        return members
    elif node_name == 'Attribute':
        if node.value.__class__.__name__ == 'Name' and self and node.value.id == self_id:  # type: ignore  # NOQA
            # instance variable
            return ["%s" % get_lvar_names(node.attr, self)[0]]  # type: ignore
        else:
            raise TypeError('The assignment %r is not instance variable' % node)
    elif node_name == 'str':
        return [node]  # type: ignore
    elif node_name == 'Starred':
        return get_lvar_names(node.value, self)  # type: ignore
    else:
        raise NotImplementedError('Unexpected node name %r' % node_name)


def dedent_docstring(s):
    # type: (unicode) -> unicode
    """Remove common leading indentation from docstring."""
    def dummy():
        # type: () -> None
        # dummy function to mock `inspect.getdoc`.
        pass

    dummy.__doc__ = s  # type: ignore
    docstring = inspect.getdoc(dummy)
    return docstring.lstrip("\r\n").rstrip("\r\n")


class Token(object):
    """Better token wrapper for tokenize module."""

    def __init__(self, kind, value, start, end, source):
        # type: (int, Any, Tuple[int, int], Tuple[int, int], unicode) -> None  # NOQA
        self.kind = kind
        self.value = value
        self.start = start
        self.end = end
        self.source = source

    def __eq__(self, other):
        # type: (Any) -> bool
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

    def __ne__(self, other):
        # type: (Any) -> bool
        return not (self == other)

    def match(self, *conditions):
        # type: (Any) -> bool
        return any(self == candidate for candidate in conditions)

    def __repr__(self):
        # type: () -> str
        return '<Token kind=%r value=%r>' % (tokenize.tok_name[self.kind],
                                             self.value.strip())


class TokenProcessor(object):
    def __init__(self, buffers):
        # type: (List[unicode]) -> None
        lines = iter(buffers)
        self.buffers = buffers
        self.tokens = tokenize.generate_tokens(lambda: next(lines))  # type: ignore  # NOQA
        self.current = None     # type: Token
        self.previous = None    # type: Token

    def get_line(self, lineno):
        # type: (int) -> unicode
        """Returns specified line."""
        return self.buffers[lineno - 1]

    def fetch_token(self):
        # type: () -> Token
        """Fetch a next token from source code.

        Returns ``False`` if sequence finished.
        """
        try:
            self.previous = self.current
            self.current = Token(*next(self.tokens))
        except StopIteration:
            self.current = None

        return self.current

    def fetch_until(self, condition):
        # type: (Any) -> List[Token]
        """Fetch tokens until specified token appeared.

        .. note:: This also handles parenthesis well.
        """
        tokens = []
        while self.fetch_token():
            tokens.append(self.current)
            if self.current == condition:
                break
            elif self.current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif self.current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif self.current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])

        return tokens


class AfterCommentParser(TokenProcessor):
    """Python source code parser to pick up comment after assignment.

    This parser takes a python code starts with assignment statement,
    and returns the comments for variable if exists.
    """

    def __init__(self, lines):
        # type: (List[unicode]) -> None
        super(AfterCommentParser, self).__init__(lines)
        self.comment = None  # type: unicode

    def fetch_rvalue(self):
        # type: () -> List[Token]
        """Fetch right-hand value of assignment."""
        tokens = []
        while self.fetch_token():
            tokens.append(self.current)
            if self.current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif self.current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif self.current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])
            elif self.current == INDENT:
                tokens += self.fetch_until(DEDENT)
            elif self.current == [OP, ';']:
                break
            elif self.current.kind not in (OP, NAME, NUMBER, STRING):
                break

        return tokens

    def parse(self):
        # type: () -> None
        """Parse the code and obtain comment after assignment."""
        # skip lvalue (or whole of AnnAssign)
        while not self.fetch_token().match([OP, '='], NEWLINE, COMMENT):
            assert self.current

        # skip rvalue (if exists)
        if self.current == [OP, '=']:
            self.fetch_rvalue()

        if self.current == COMMENT:
            self.comment = self.current.value


class VariableCommentPicker(ast.NodeVisitor):
    """Python source code parser to pick up variable comments."""

    def __init__(self, buffers, encoding):
        # type: (List[unicode], unicode) -> None
        self.counter = itertools.count()
        self.buffers = buffers
        self.encoding = encoding
        self.context = []               # type: List[unicode]
        self.current_classes = []       # type: List[unicode]
        self.current_function = None    # type: ast.FunctionDef
        self.comments = {}              # type: Dict[Tuple[unicode, unicode], unicode]
        self.previous = None            # type: ast.AST
        self.deforders = {}             # type: Dict[unicode, int]
        super(VariableCommentPicker, self).__init__()

    def add_entry(self, name):
        # type: (unicode) -> None
        if self.current_function:
            if self.current_classes and self.context[-1] == "__init__":
                # store variable comments inside __init__ method of classes
                definition = self.context[:-1] + [name]
            else:
                return
        else:
            definition = self.context + [name]

        self.deforders[".".join(definition)] = next(self.counter)

    def add_variable_comment(self, name, comment):
        # type: (unicode, unicode) -> None
        if self.current_function:
            if self.current_classes and self.context[-1] == "__init__":
                # store variable comments inside __init__ method of classes
                context = ".".join(self.context[:-1])
            else:
                return
        else:
            context = ".".join(self.context)

        self.comments[(context, name)] = comment

    def get_self(self):
        # type: () -> ast.expr
        """Returns the name of first argument if in function."""
        if self.current_function and self.current_function.args.args:
            return self.current_function.args.args[0]
        else:
            return None

    def get_line(self, lineno):
        # type: (int) -> unicode
        """Returns specified line."""
        return self.buffers[lineno - 1]

    def visit(self, node):
        # type: (ast.AST) -> None
        """Updates self.previous to ."""
        super(VariableCommentPicker, self).visit(node)
        self.previous = node

    def visit_Assign(self, node):
        # type: (ast.Assign) -> None
        """Handles Assign node and pick up a variable comment."""
        try:
            targets = get_assign_targets(node)
            varnames = sum([get_lvar_names(t, self=self.get_self()) for t in targets], [])
            current_line = self.get_line(node.lineno)
        except TypeError:
            return  # this assignment is not new definition!

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

    def visit_AnnAssign(self, node):
        # type: (ast.AST) -> None
        """Handles AnnAssign node and pick up a variable comment."""
        self.visit_Assign(node)  # type: ignore

    def visit_Expr(self, node):
        # type: (ast.Expr) -> None
        """Handles Expr node and pick up a comment if string."""
        if (isinstance(self.previous, ASSIGN_NODES) and isinstance(node.value, ast.Str)):
            try:
                targets = get_assign_targets(self.previous)
                varnames = get_lvar_names(targets[0], self.get_self())
                for varname in varnames:
                    if isinstance(node.value.s, text_type):
                        docstring = node.value.s
                    else:
                        docstring = node.value.s.decode(self.encoding or 'utf-8')

                    self.add_variable_comment(varname, dedent_docstring(docstring))
                    self.add_entry(varname)
            except TypeError:
                pass  # this assignment is not new definition!

    def visit_ClassDef(self, node):
        # type: (ast.ClassDef) -> None
        """Handles ClassDef node and set context."""
        self.current_classes.append(node.name)
        self.add_entry(node.name)
        self.context.append(node.name)
        self.previous = node
        for child in node.body:
            self.visit(child)
        self.context.pop()
        self.current_classes.pop()

    def visit_FunctionDef(self, node):
        # type: (ast.FunctionDef) -> None
        """Handles FunctionDef node and set context."""
        if self.current_function is None:
            self.add_entry(node.name)  # should be called before setting self.current_function
            self.context.append(node.name)
            self.current_function = node
            for child in node.body:
                self.visit(child)
            self.context.pop()
            self.current_function = None


class DefinitionFinder(TokenProcessor):
    def __init__(self, lines):
        # type: (List[unicode]) -> None
        super(DefinitionFinder, self).__init__(lines)
        self.decorator = None   # type: Token
        self.context = []       # type: List[unicode]
        self.indents = []       # type: List
        self.definitions = {}   # type: Dict[unicode, Tuple[unicode, int, int]]

    def add_definition(self, name, entry):
        # type: (unicode, Tuple[unicode, int, int]) -> None
        if self.indents and self.indents[-1][0] == 'def' and entry[0] == 'def':
            # ignore definition of inner function
            pass
        else:
            self.definitions[name] = entry

    def parse(self):
        # type: () -> None
        while True:
            token = self.fetch_token()
            if token is None:
                break
            elif token == COMMENT:
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

    def parse_definition(self, typ):
        # type: (unicode) -> None
        name = self.fetch_token()
        self.context.append(name.value)
        funcname = '.'.join(self.context)

        if self.decorator:
            start_pos = self.decorator.start[0]
            self.decorator = None
        else:
            start_pos = name.start[0]

        self.fetch_until([OP, ':'])
        if self.fetch_token().match(COMMENT, NEWLINE):
            self.fetch_until(INDENT)
            self.indents.append((typ, funcname, start_pos))
        else:
            # one-liner
            self.add_definition(funcname, (typ, start_pos, name.end[0]))
            self.context.pop()

    def finalize_block(self):
        # type: () -> None
        definition = self.indents.pop()
        if definition[0] != 'other':
            typ, funcname, start_pos = definition
            end_pos = self.current.end[0] - 1
            while emptyline_re.match(self.get_line(end_pos)):
                end_pos -= 1

            self.add_definition(funcname, (typ, start_pos, end_pos))
            self.context.pop()


class Parser(object):
    """Python source code parser to pick up variable comments.

    This is a better wrapper for ``VariableCommentPicker``.
    """

    def __init__(self, code, encoding='utf-8'):
        # type: (unicode, unicode) -> None
        self.code = filter_whitespace(code)
        self.encoding = encoding
        self.comments = {}          # type: Dict[Tuple[unicode, unicode], unicode]
        self.deforders = {}         # type: Dict[unicode, int]
        self.definitions = {}       # type: Dict[unicode, Tuple[unicode, int, int]]

    def parse(self):
        # type: () -> None
        """Parse the source code."""
        self.parse_comments()
        self.parse_definition()

    def parse_comments(self):
        # type: () -> None
        """Parse the code and pick up comments."""
        tree = ast.parse(self.code.encode('utf-8'))
        picker = VariableCommentPicker(self.code.splitlines(True), self.encoding)
        picker.visit(tree)
        self.comments = picker.comments
        self.deforders = picker.deforders

    def parse_definition(self):
        # type: () -> None
        """Parse the location of definitions from the code."""
        parser = DefinitionFinder(self.code.splitlines(True))
        parser.parse()
        self.definitions = parser.definitions
