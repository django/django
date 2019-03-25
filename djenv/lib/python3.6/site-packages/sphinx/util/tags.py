# -*- coding: utf-8 -*-
"""
    sphinx.util.tags
    ~~~~~~~~~~~~~~~~

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# (ab)use the Jinja parser for parsing our boolean expressions
from jinja2 import nodes
from jinja2.environment import Environment
from jinja2.parser import Parser

env = Environment()

if False:
    # For type annotation
    from typing import Iterator, List  # NOQA


class BooleanParser(Parser):
    """
    Only allow condition exprs and/or/not operations.
    """

    def parse_compare(self):
        # type: () -> nodes.Node
        node = None  # type: nodes.Node
        token = self.stream.current
        if token.type == 'name':
            if token.value in ('true', 'false', 'True', 'False'):
                node = nodes.Const(token.value in ('true', 'True'),
                                   lineno=token.lineno)
            elif token.value in ('none', 'None'):
                node = nodes.Const(None, lineno=token.lineno)
            else:
                node = nodes.Name(token.value, 'load', lineno=token.lineno)
            next(self.stream)
        elif token.type == 'lparen':
            next(self.stream)
            node = self.parse_expression()
            self.stream.expect('rparen')
        else:
            self.fail("unexpected token '%s'" % (token,), token.lineno)
        return node


class Tags(object):
    def __init__(self, tags=None):
        # type: (List[unicode]) -> None
        self.tags = dict.fromkeys(tags or [], True)

    def has(self, tag):
        # type: (unicode) -> bool
        return tag in self.tags

    __contains__ = has

    def __iter__(self):
        # type: () -> Iterator[unicode]
        return iter(self.tags)

    def add(self, tag):
        # type: (unicode) -> None
        self.tags[tag] = True

    def remove(self, tag):
        # type: (unicode) -> None
        self.tags.pop(tag, None)

    def eval_condition(self, condition):
        # type: (unicode) -> bool
        # exceptions are handled by the caller
        parser = BooleanParser(env, condition, state='variable')
        expr = parser.parse_expression()
        if not parser.stream.eos:
            raise ValueError('chunk after expression')

        def eval_node(node):
            # type: (nodes.Node) -> bool
            if isinstance(node, nodes.CondExpr):
                if eval_node(node.test):  # type: ignore
                    return eval_node(node.expr1)  # type: ignore
                else:
                    return eval_node(node.expr2)  # type: ignore
            elif isinstance(node, nodes.And):
                return eval_node(node.left) and eval_node(node.right)  # type: ignore
            elif isinstance(node, nodes.Or):
                return eval_node(node.left) or eval_node(node.right)  # type: ignore
            elif isinstance(node, nodes.Not):
                return not eval_node(node.node)  # type: ignore
            elif isinstance(node, nodes.Name):
                return self.tags.get(node.name, False)  # type: ignore
            else:
                raise ValueError('invalid node, check parsing')

        return eval_node(expr)
