"""The Python domain."""

from __future__ import annotations

import ast
import builtins
import contextlib
import inspect
import re
import token
import typing
from inspect import Parameter
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.addnodes import desc_signature, pending_xref, pending_xref_condition
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, IndexEntry, ObjType
from sphinx.locale import _, __
from sphinx.pycode.parser import Token, TokenProcessor
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.inspect import signature_from_str
from sphinx.util.nodes import (
    find_pending_xref_condition,
    make_id,
    make_refnode,
    nested_parse_with_titles,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from docutils.nodes import Element, Node
    from docutils.parsers.rst.states import Inliner

    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec, TextlikeNode

logger = logging.getLogger(__name__)


# REs for Python signatures
py_sig_re = re.compile(
    r'''^ ([\w.]*\.)?            # class name(s)
          (\w+)  \s*             # thing name
          (?: \[\s*(.*)\s*])?    # optional: type parameters list
          (?: \(\s*(.*)\s*\)     # optional: arguments
           (?:\s* -> \s* (.*))?  #           return annotation
          )? $                   # and nothing more
          ''', re.VERBOSE)


pairindextypes = {
    'module': 'module',
    'keyword': 'keyword',
    'operator': 'operator',
    'object': 'object',
    'exception': 'exception',
    'statement': 'statement',
    'builtin': 'built-in function',
}


class ObjectEntry(NamedTuple):
    docname: str
    node_id: str
    objtype: str
    aliased: bool


class ModuleEntry(NamedTuple):
    docname: str
    node_id: str
    synopsis: str
    platform: str
    deprecated: bool


def parse_reftarget(reftarget: str, suppress_prefix: bool = False,
                    ) -> tuple[str, str, str, bool]:
    """Parse a type string and return (reftype, reftarget, title, refspecific flag)"""
    refspecific = False
    if reftarget.startswith('.'):
        reftarget = reftarget[1:]
        title = reftarget
        refspecific = True
    elif reftarget.startswith('~'):
        reftarget = reftarget[1:]
        title = reftarget.split('.')[-1]
    elif suppress_prefix:
        title = reftarget.split('.')[-1]
    elif reftarget.startswith('typing.'):
        title = reftarget[7:]
    else:
        title = reftarget

    if reftarget == 'None' or reftarget.startswith('typing.'):
        # typing module provides non-class types.  Obj reference is good to refer them.
        reftype = 'obj'
    else:
        reftype = 'class'

    return reftype, reftarget, title, refspecific


def type_to_xref(target: str, env: BuildEnvironment, *,
                 suppress_prefix: bool = False) -> addnodes.pending_xref:
    """Convert a type string to a cross reference node."""
    if env:
        kwargs = {'py:module': env.ref_context.get('py:module'),
                  'py:class': env.ref_context.get('py:class')}
    else:
        kwargs = {}

    reftype, target, title, refspecific = parse_reftarget(target, suppress_prefix)

    if env.config.python_use_unqualified_type_names:
        # Note: It would be better to use qualname to describe the object to support support
        # nested classes.  But python domain can't access the real python object because this
        # module should work not-dynamically.
        shortname = title.split('.')[-1]
        contnodes: list[Node] = [pending_xref_condition('', shortname, condition='resolved'),
                                 pending_xref_condition('', title, condition='*')]
    else:
        contnodes = [nodes.Text(title)]

    return pending_xref('', *contnodes,
                        refdomain='py', reftype=reftype, reftarget=target,
                        refspecific=refspecific, **kwargs)


def _parse_annotation(annotation: str, env: BuildEnvironment) -> list[Node]:
    """Parse type annotation."""
    short_literals = env.config.python_display_short_literal_types

    def unparse(node: ast.AST) -> list[Node]:
        if isinstance(node, ast.Attribute):
            return [nodes.Text(f"{unparse(node.value)[0]}.{node.attr}")]
        if isinstance(node, ast.BinOp):
            result: list[Node] = unparse(node.left)
            result.extend(unparse(node.op))
            result.extend(unparse(node.right))
            return result
        if isinstance(node, ast.BitOr):
            return [addnodes.desc_sig_space(),
                    addnodes.desc_sig_punctuation('', '|'),
                    addnodes.desc_sig_space()]
        if isinstance(node, ast.Constant):
            if node.value is Ellipsis:
                return [addnodes.desc_sig_punctuation('', "...")]
            if isinstance(node.value, bool):
                return [addnodes.desc_sig_keyword('', repr(node.value))]
            if isinstance(node.value, int):
                return [addnodes.desc_sig_literal_number('', repr(node.value))]
            if isinstance(node.value, str):
                return [addnodes.desc_sig_literal_string('', repr(node.value))]
            else:
                # handles None, which is further handled by type_to_xref later
                # and fallback for other types that should be converted
                return [nodes.Text(repr(node.value))]
        if isinstance(node, ast.Expr):
            return unparse(node.value)
        if isinstance(node, ast.Invert):
            return [addnodes.desc_sig_punctuation('', '~')]
        if isinstance(node, ast.List):
            result = [addnodes.desc_sig_punctuation('', '[')]
            if node.elts:
                # check if there are elements in node.elts to only pop the
                # last element of result if the for-loop was run at least
                # once
                for elem in node.elts:
                    result.extend(unparse(elem))
                    result.append(addnodes.desc_sig_punctuation('', ','))
                    result.append(addnodes.desc_sig_space())
                result.pop()
                result.pop()
            result.append(addnodes.desc_sig_punctuation('', ']'))
            return result
        if isinstance(node, ast.Module):
            return sum((unparse(e) for e in node.body), [])
        if isinstance(node, ast.Name):
            return [nodes.Text(node.id)]
        if isinstance(node, ast.Subscript):
            if getattr(node.value, 'id', '') in {'Optional', 'Union'}:
                return _unparse_pep_604_annotation(node)
            if short_literals and getattr(node.value, 'id', '') == 'Literal':
                return _unparse_pep_604_annotation(node)
            result = unparse(node.value)
            result.append(addnodes.desc_sig_punctuation('', '['))
            result.extend(unparse(node.slice))
            result.append(addnodes.desc_sig_punctuation('', ']'))

            # Wrap the Text nodes inside brackets by literal node if the subscript is a Literal
            if result[0] in ('Literal', 'typing.Literal'):
                for i, subnode in enumerate(result[1:], start=1):
                    if isinstance(subnode, nodes.Text):
                        result[i] = nodes.literal('', '', subnode)
            return result
        if isinstance(node, ast.UnaryOp):
            return unparse(node.op) + unparse(node.operand)
        if isinstance(node, ast.Tuple):
            if node.elts:
                result = []
                for elem in node.elts:
                    result.extend(unparse(elem))
                    result.append(addnodes.desc_sig_punctuation('', ','))
                    result.append(addnodes.desc_sig_space())
                result.pop()
                result.pop()
            else:
                result = [addnodes.desc_sig_punctuation('', '('),
                          addnodes.desc_sig_punctuation('', ')')]

            return result
        raise SyntaxError  # unsupported syntax

    def _unparse_pep_604_annotation(node: ast.Subscript) -> list[Node]:
        subscript = node.slice

        flattened: list[Node] = []
        if isinstance(subscript, ast.Tuple):
            flattened.extend(unparse(subscript.elts[0]))
            for elt in subscript.elts[1:]:
                flattened.extend(unparse(ast.BitOr()))
                flattened.extend(unparse(elt))
        else:
            # e.g. a Union[] inside an Optional[]
            flattened.extend(unparse(subscript))

        if getattr(node.value, 'id', '') == 'Optional':
            flattened.extend(unparse(ast.BitOr()))
            flattened.append(nodes.Text('None'))

        return flattened

    try:
        tree = ast.parse(annotation, type_comments=True)
        result: list[Node] = []
        for node in unparse(tree):
            if isinstance(node, nodes.literal):
                result.append(node[0])
            elif isinstance(node, nodes.Text) and node.strip():
                if (result and isinstance(result[-1], addnodes.desc_sig_punctuation) and
                        result[-1].astext() == '~'):
                    result.pop()
                    result.append(type_to_xref(str(node), env, suppress_prefix=True))
                else:
                    result.append(type_to_xref(str(node), env))
            else:
                result.append(node)
        return result
    except SyntaxError:
        return [type_to_xref(annotation, env)]


class _TypeParameterListParser(TokenProcessor):
    def __init__(self, sig: str) -> None:
        signature = sig.replace('\n', '').strip()
        super().__init__([signature])
        # Each item is a tuple (name, kind, default, annotation) mimicking
        # ``inspect.Parameter`` to allow default values on VAR_POSITIONAL
        # or VAR_KEYWORD parameters.
        self.type_params: list[tuple[str, int, Any, Any]] = []

    def fetch_type_param_spec(self) -> list[Token]:
        tokens = []
        while current := self.fetch_token():
            tokens.append(current)
            for ldelim, rdelim in ('(', ')'), ('{', '}'), ('[', ']'):
                if current == [token.OP, ldelim]:
                    tokens += self.fetch_until([token.OP, rdelim])
                    break
            else:
                if current == token.INDENT:
                    tokens += self.fetch_until(token.DEDENT)
                elif current.match(
                        [token.OP, ':'], [token.OP, '='], [token.OP, ',']):
                    tokens.pop()
                    break
        return tokens

    def parse(self) -> None:
        while current := self.fetch_token():
            if current == token.NAME:
                tp_name = current.value.strip()
                if self.previous and self.previous.match([token.OP, '*'], [token.OP, '**']):
                    if self.previous == [token.OP, '*']:
                        tp_kind = Parameter.VAR_POSITIONAL
                    else:
                        tp_kind = Parameter.VAR_KEYWORD  # type: ignore[assignment]
                else:
                    tp_kind = Parameter.POSITIONAL_OR_KEYWORD  # type: ignore[assignment]

                tp_ann: Any = Parameter.empty
                tp_default: Any = Parameter.empty

                current = self.fetch_token()
                if current and current.match([token.OP, ':'], [token.OP, '=']):
                    if current == [token.OP, ':']:
                        tokens = self.fetch_type_param_spec()
                        tp_ann = self._build_identifier(tokens)

                    if self.current and self.current == [token.OP, '=']:
                        tokens = self.fetch_type_param_spec()
                        tp_default = self._build_identifier(tokens)

                if tp_kind != Parameter.POSITIONAL_OR_KEYWORD and tp_ann != Parameter.empty:
                    msg = ('type parameter bound or constraint is not allowed '
                           f'for {tp_kind.description} parameters')
                    raise SyntaxError(msg)

                type_param = (tp_name, tp_kind, tp_default, tp_ann)
                self.type_params.append(type_param)

    def _build_identifier(self, tokens: list[Token]) -> str:
        from itertools import chain, tee

        def pairwise(iterable):
            a, b = tee(iterable)
            next(b, None)
            return zip(a, b)

        def triplewise(iterable):
            for (a, _z), (b, c) in pairwise(pairwise(iterable)):
                yield a, b, c

        idents: list[str] = []
        tokens: Iterable[Token] = iter(tokens)  # type: ignore[no-redef]
        # do not format opening brackets
        for tok in tokens:
            if not tok.match([token.OP, '('], [token.OP, '['], [token.OP, '{']):
                # check if the first non-delimiter character is an unpack operator
                is_unpack_operator = tok.match([token.OP, '*'], [token.OP, ['**']])
                idents.append(self._pformat_token(tok, native=is_unpack_operator))
                break
            idents.append(tok.value)

        # check the remaining tokens
        stop = Token(token.ENDMARKER, '', (-1, -1), (-1, -1), '<sentinel>')
        is_unpack_operator = False
        for tok, op, after in triplewise(chain(tokens, [stop, stop])):
            ident = self._pformat_token(tok, native=is_unpack_operator)
            idents.append(ident)
            # determine if the next token is an unpack operator depending
            # on the left and right hand side of the operator symbol
            is_unpack_operator = (
                op.match([token.OP, '*'], [token.OP, '**']) and not (
                    tok.match(token.NAME, token.NUMBER, token.STRING,
                              [token.OP, ')'], [token.OP, ']'], [token.OP, '}'])
                    and after.match(token.NAME, token.NUMBER, token.STRING,
                                    [token.OP, '('], [token.OP, '['], [token.OP, '{'])
                )
            )

        return ''.join(idents).strip()

    def _pformat_token(self, tok: Token, native: bool = False) -> str:
        if native:
            return tok.value

        if tok.match(token.NEWLINE, token.ENDMARKER):
            return ''

        if tok.match([token.OP, ':'], [token.OP, ','], [token.OP, '#']):
            return f'{tok.value} '

        # Arithmetic operators are allowed because PEP 695 specifies the
        # default type parameter to be *any* expression (so "T1 << T2" is
        # allowed if it makes sense). The caller is responsible to ensure
        # that a multiplication operator ("*") is not to be confused with
        # an unpack operator (which will not be surrounded by spaces).
        #
        # The operators are ordered according to how likely they are to
        # be used and for (possible) future implementations (e.g., "&" for
        # an intersection type).
        if tok.match(
            # Most likely operators to appear
            [token.OP, '='], [token.OP, '|'],
            # Type composition (future compatibility)
            [token.OP, '&'], [token.OP, '^'], [token.OP, '<'], [token.OP, '>'],
            # Unlikely type composition
            [token.OP, '+'], [token.OP, '-'], [token.OP, '*'], [token.OP, '**'],
            # Unlikely operators but included for completeness
            [token.OP, '@'], [token.OP, '/'], [token.OP, '//'], [token.OP, '%'],
            [token.OP, '<<'], [token.OP, '>>'], [token.OP, '>>>'],
            [token.OP, '<='], [token.OP, '>='], [token.OP, '=='], [token.OP, '!='],
        ):
            return f' {tok.value} '

        return tok.value


def _parse_type_list(
    tp_list: str, env: BuildEnvironment,
    multi_line_parameter_list: bool = False,
) -> addnodes.desc_type_parameter_list:
    """Parse a list of type parameters according to PEP 695."""
    type_params = addnodes.desc_type_parameter_list(tp_list)
    type_params['multi_line_parameter_list'] = multi_line_parameter_list
    # formal parameter names are interpreted as type parameter names and
    # type annotations are interpreted as type parameter bound or constraints
    parser = _TypeParameterListParser(tp_list)
    parser.parse()
    for (tp_name, tp_kind, tp_default, tp_ann) in parser.type_params:
        # no positional-only or keyword-only allowed in a type parameters list
        if tp_kind in {Parameter.POSITIONAL_ONLY, Parameter.KEYWORD_ONLY}:
            msg = ('positional-only or keyword-only parameters '
                   'are prohibited in type parameter lists')
            raise SyntaxError(msg)

        node = addnodes.desc_type_parameter()
        if tp_kind == Parameter.VAR_POSITIONAL:
            node += addnodes.desc_sig_operator('', '*')
        elif tp_kind == Parameter.VAR_KEYWORD:
            node += addnodes.desc_sig_operator('', '**')
        node += addnodes.desc_sig_name('', tp_name)

        if tp_ann is not Parameter.empty:
            annotation = _parse_annotation(tp_ann, env)
            if not annotation:
                continue

            node += addnodes.desc_sig_punctuation('', ':')
            node += addnodes.desc_sig_space()

            type_ann_expr = addnodes.desc_sig_name('', '',
                                                   *annotation)  # type: ignore[arg-type]
            # a type bound is ``T: U`` whereas type constraints
            # must be enclosed with parentheses. ``T: (U, V)``
            if tp_ann.startswith('(') and tp_ann.endswith(')'):
                type_ann_text = type_ann_expr.astext()
                if type_ann_text.startswith('(') and type_ann_text.endswith(')'):
                    node += type_ann_expr
                else:
                    # surrounding braces are lost when using _parse_annotation()
                    node += addnodes.desc_sig_punctuation('', '(')
                    node += type_ann_expr  # type constraint
                    node += addnodes.desc_sig_punctuation('', ')')
            else:
                node += type_ann_expr  # type bound

        if tp_default is not Parameter.empty:
            # Always surround '=' with spaces, even if there is no annotation
            node += addnodes.desc_sig_space()
            node += addnodes.desc_sig_operator('', '=')
            node += addnodes.desc_sig_space()
            node += nodes.inline('', tp_default,
                                 classes=['default_value'],
                                 support_smartquotes=False)

        type_params += node
    return type_params


def _parse_arglist(
    arglist: str, env: BuildEnvironment, multi_line_parameter_list: bool = False,
) -> addnodes.desc_parameterlist:
    """Parse a list of arguments using AST parser"""
    params = addnodes.desc_parameterlist(arglist)
    params['multi_line_parameter_list'] = multi_line_parameter_list
    sig = signature_from_str('(%s)' % arglist)
    last_kind = None
    for param in sig.parameters.values():
        if param.kind != param.POSITIONAL_ONLY and last_kind == param.POSITIONAL_ONLY:
            # PEP-570: Separator for Positional Only Parameter: /
            params += addnodes.desc_parameter('', '', addnodes.desc_sig_operator('', '/'))
        if param.kind == param.KEYWORD_ONLY and last_kind in (param.POSITIONAL_OR_KEYWORD,
                                                              param.POSITIONAL_ONLY,
                                                              None):
            # PEP-3102: Separator for Keyword Only Parameter: *
            params += addnodes.desc_parameter('', '', addnodes.desc_sig_operator('', '*'))

        node = addnodes.desc_parameter()
        if param.kind == param.VAR_POSITIONAL:
            node += addnodes.desc_sig_operator('', '*')
            node += addnodes.desc_sig_name('', param.name)
        elif param.kind == param.VAR_KEYWORD:
            node += addnodes.desc_sig_operator('', '**')
            node += addnodes.desc_sig_name('', param.name)
        else:
            node += addnodes.desc_sig_name('', param.name)

        if param.annotation is not param.empty:
            children = _parse_annotation(param.annotation, env)
            node += addnodes.desc_sig_punctuation('', ':')
            node += addnodes.desc_sig_space()
            node += addnodes.desc_sig_name('', '', *children)  # type: ignore[arg-type]
        if param.default is not param.empty:
            if param.annotation is not param.empty:
                node += addnodes.desc_sig_space()
                node += addnodes.desc_sig_operator('', '=')
                node += addnodes.desc_sig_space()
            else:
                node += addnodes.desc_sig_operator('', '=')
            node += nodes.inline('', param.default, classes=['default_value'],
                                 support_smartquotes=False)

        params += node
        last_kind = param.kind

    if last_kind == Parameter.POSITIONAL_ONLY:
        # PEP-570: Separator for Positional Only Parameter: /
        params += addnodes.desc_parameter('', '', addnodes.desc_sig_operator('', '/'))

    return params


def _pseudo_parse_arglist(
    signode: desc_signature, arglist: str, multi_line_parameter_list: bool = False,
) -> None:
    """"Parse" a list of arguments separated by commas.

    Arguments can have "optional" annotations given by enclosing them in
    brackets.  Currently, this will split at any comma, even if it's inside a
    string literal (e.g. default argument value).
    """
    paramlist = addnodes.desc_parameterlist()
    paramlist['multi_line_parameter_list'] = multi_line_parameter_list
    stack: list[Element] = [paramlist]
    try:
        for argument in arglist.split(','):
            argument = argument.strip()
            ends_open = ends_close = 0
            while argument.startswith('['):
                stack.append(addnodes.desc_optional())
                stack[-2] += stack[-1]
                argument = argument[1:].strip()
            while argument.startswith(']'):
                stack.pop()
                argument = argument[1:].strip()
            while argument.endswith(']') and not argument.endswith('[]'):
                ends_close += 1
                argument = argument[:-1].strip()
            while argument.endswith('['):
                ends_open += 1
                argument = argument[:-1].strip()
            if argument:
                stack[-1] += addnodes.desc_parameter(
                    '', '', addnodes.desc_sig_name(argument, argument))
            while ends_open:
                stack.append(addnodes.desc_optional())
                stack[-2] += stack[-1]
                ends_open -= 1
            while ends_close:
                stack.pop()
                ends_close -= 1
        if len(stack) != 1:
            raise IndexError
    except IndexError:
        # if there are too few or too many elements on the stack, just give up
        # and treat the whole argument list as one argument, discarding the
        # already partially populated paramlist node
        paramlist = addnodes.desc_parameterlist()
        paramlist += addnodes.desc_parameter(arglist, arglist)
        signode += paramlist
    else:
        signode += paramlist


# This override allows our inline type specifiers to behave like :class: link
# when it comes to handling "." and "~" prefixes.
class PyXrefMixin:
    def make_xref(
        self,
        rolename: str,
        domain: str,
        target: str,
        innernode: type[TextlikeNode] = nodes.emphasis,
        contnode: Node | None = None,
        env: BuildEnvironment | None = None,
        inliner: Inliner | None = None,
        location: Node | None = None,
    ) -> Node:
        # we use inliner=None to make sure we get the old behaviour with a single
        # pending_xref node
        result = super().make_xref(rolename, domain, target,  # type: ignore[misc]
                                   innernode, contnode,
                                   env, inliner=None, location=None)
        if isinstance(result, pending_xref):
            assert env is not None
            result['refspecific'] = True
            result['py:module'] = env.ref_context.get('py:module')
            result['py:class'] = env.ref_context.get('py:class')

            reftype, reftarget, reftitle, _ = parse_reftarget(target)
            if reftarget != reftitle:
                result['reftype'] = reftype
                result['reftarget'] = reftarget

                result.clear()
                result += innernode(reftitle, reftitle)
            elif env.config.python_use_unqualified_type_names:
                children = result.children
                result.clear()

                shortname = target.split('.')[-1]
                textnode = innernode('', shortname)
                contnodes = [pending_xref_condition('', '', textnode, condition='resolved'),
                             pending_xref_condition('', '', *children, condition='*')]
                result.extend(contnodes)

        return result

    def make_xrefs(
        self,
        rolename: str,
        domain: str,
        target: str,
        innernode: type[TextlikeNode] = nodes.emphasis,
        contnode: Node | None = None,
        env: BuildEnvironment | None = None,
        inliner: Inliner | None = None,
        location: Node | None = None,
    ) -> list[Node]:
        delims = r'(\s*[\[\]\(\),](?:\s*o[rf]\s)?\s*|\s+o[rf]\s+|\s*\|\s*|\.\.\.)'
        delims_re = re.compile(delims)
        sub_targets = re.split(delims, target)

        split_contnode = bool(contnode and contnode.astext() == target)

        in_literal = False
        results = []
        for sub_target in filter(None, sub_targets):
            if split_contnode:
                contnode = nodes.Text(sub_target)

            if in_literal or delims_re.match(sub_target):
                results.append(contnode or innernode(sub_target, sub_target))
            else:
                results.append(self.make_xref(rolename, domain, sub_target,
                                              innernode, contnode, env, inliner, location))

            if sub_target in ('Literal', 'typing.Literal', '~typing.Literal'):
                in_literal = True

        return results


class PyField(PyXrefMixin, Field):
    pass


class PyGroupedField(PyXrefMixin, GroupedField):
    pass


class PyTypedField(PyXrefMixin, TypedField):
    pass


class PyObject(ObjectDescription[tuple[str, str]]):
    """
    Description of a general Python object.

    :cvar allow_nesting: Class is an object that allows for nested namespaces
    :vartype allow_nesting: bool
    """
    option_spec: OptionSpec = {
        'no-index': directives.flag,
        'no-index-entry': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindex': directives.flag,
        'noindexentry': directives.flag,
        'nocontentsentry': directives.flag,
        'single-line-parameter-list': directives.flag,
        'single-line-type-parameter-list': directives.flag,
        'module': directives.unchanged,
        'canonical': directives.unchanged,
        'annotation': directives.unchanged,
    }

    doc_field_types = [
        PyTypedField('parameter', label=_('Parameters'),
                     names=('param', 'parameter', 'arg', 'argument',
                            'keyword', 'kwarg', 'kwparam'),
                     typerolename='class', typenames=('paramtype', 'type'),
                     can_collapse=True),
        PyTypedField('variable', label=_('Variables'),
                     names=('var', 'ivar', 'cvar'),
                     typerolename='class', typenames=('vartype',),
                     can_collapse=True),
        PyGroupedField('exceptions', label=_('Raises'), rolename='exc',
                       names=('raises', 'raise', 'exception', 'except'),
                       can_collapse=True),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
        PyField('returntype', label=_('Return type'), has_arg=False,
                names=('rtype',), bodyrolename='class'),
    ]

    allow_nesting = False

    def get_signature_prefix(self, sig: str) -> list[nodes.Node]:
        """May return a prefix to put before the object name in the
        signature.
        """
        return []

    def needs_arglist(self) -> bool:
        """May return true if an empty argument list is to be generated even if
        the document contains none.
        """
        return False

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        """Transform a Python signature into RST nodes.

        Return (fully qualified name of the thing, classname if any).

        If inside a class, the current class name is handled intelligently:
        * it is stripped from the displayed name if present
        * it is added to the full name (return value) if not present
        """
        m = py_sig_re.match(sig)
        if m is None:
            raise ValueError
        prefix, name, tp_list, arglist, retann = m.groups()

        # determine module and class name (if applicable), as well as full name
        modname = self.options.get('module', self.env.ref_context.get('py:module'))
        classname = self.env.ref_context.get('py:class')
        if classname:
            add_module = False
            if prefix and (prefix == classname or
                           prefix.startswith(classname + ".")):
                fullname = prefix + name
                # class name is given again in the signature
                prefix = prefix[len(classname):].lstrip('.')
            elif prefix:
                # class name is given in the signature, but different
                # (shouldn't happen)
                fullname = classname + '.' + prefix + name
            else:
                # class name is not given in the signature
                fullname = classname + '.' + name
        else:
            add_module = True
            if prefix:
                classname = prefix.rstrip('.')
                fullname = prefix + name
            else:
                classname = ''
                fullname = name

        signode['module'] = modname
        signode['class'] = classname
        signode['fullname'] = fullname

        max_len = (self.env.config.python_maximum_signature_line_length
                   or self.env.config.maximum_signature_line_length
                   or 0)

        # determine if the function arguments (without its type parameters)
        # should be formatted on a multiline or not by removing the width of
        # the type parameters list (if any)
        sig_len = len(sig)
        tp_list_span = m.span(3)
        multi_line_parameter_list = (
            'single-line-parameter-list' not in self.options
            and (sig_len - (tp_list_span[1] - tp_list_span[0])) > max_len > 0
        )

        # determine whether the type parameter list must be wrapped or not
        arglist_span = m.span(4)
        multi_line_type_parameter_list = (
            'single-line-type-parameter-list' not in self.options
            and (sig_len - (arglist_span[1] - arglist_span[0])) > max_len > 0
        )

        sig_prefix = self.get_signature_prefix(sig)
        if sig_prefix:
            if type(sig_prefix) is str:
                msg = ("Python directive method get_signature_prefix()"
                       " must return a list of nodes."
                       f" Return value was '{sig_prefix}'.")
                raise TypeError(msg)
            signode += addnodes.desc_annotation(str(sig_prefix), '', *sig_prefix)

        if prefix:
            signode += addnodes.desc_addname(prefix, prefix)
        elif modname and add_module and self.env.config.add_module_names:
            nodetext = modname + '.'
            signode += addnodes.desc_addname(nodetext, nodetext)

        signode += addnodes.desc_name(name, name)

        if tp_list:
            try:
                signode += _parse_type_list(tp_list, self.env, multi_line_type_parameter_list)
            except Exception as exc:
                logger.warning("could not parse tp_list (%r): %s", tp_list, exc,
                               location=signode)

        if arglist:
            try:
                signode += _parse_arglist(arglist, self.env, multi_line_parameter_list)
            except SyntaxError:
                # fallback to parse arglist original parser
                # (this may happen if the argument list is incorrectly used
                # as a list of bases when documenting a class)
                # it supports to represent optional arguments (ex. "func(foo [, bar])")
                _pseudo_parse_arglist(signode, arglist, multi_line_parameter_list)
            except (NotImplementedError, ValueError) as exc:
                # duplicated parameter names raise ValueError and not a SyntaxError
                logger.warning("could not parse arglist (%r): %s", arglist, exc,
                               location=signode)
                _pseudo_parse_arglist(signode, arglist, multi_line_parameter_list)
        else:
            if self.needs_arglist():
                # for callables, add an empty parameter list
                signode += addnodes.desc_parameterlist()

        if retann:
            children = _parse_annotation(retann, self.env)
            signode += addnodes.desc_returns(retann, '', *children)

        anno = self.options.get('annotation')
        if anno:
            signode += addnodes.desc_annotation(' ' + anno, '',
                                                addnodes.desc_sig_space(),
                                                nodes.Text(anno))

        return fullname, prefix

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        if 'fullname' not in sig_node:
            return ()
        modname = sig_node.get('module')
        fullname = sig_node['fullname']

        if modname:
            return (modname, *fullname.split('.'))
        else:
            return tuple(fullname.split('.'))

    def get_index_text(self, modname: str, name: tuple[str, str]) -> str:
        """Return the text for the index entry of the object."""
        msg = 'must be implemented in subclasses'
        raise NotImplementedError(msg)

    def add_target_and_index(self, name_cls: tuple[str, str], sig: str,
                             signode: desc_signature) -> None:
        modname = self.options.get('module', self.env.ref_context.get('py:module'))
        fullname = (modname + '.' if modname else '') + name_cls[0]
        node_id = make_id(self.env, self.state.document, '', fullname)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)

        domain = cast(PythonDomain, self.env.get_domain('py'))
        domain.note_object(fullname, self.objtype, node_id, location=signode)

        canonical_name = self.options.get('canonical')
        if canonical_name:
            domain.note_object(canonical_name, self.objtype, node_id, aliased=True,
                               location=signode)

        if 'no-index-entry' not in self.options:
            indextext = self.get_index_text(modname, name_cls)
            if indextext:
                self.indexnode['entries'].append(('single', indextext, node_id, '', None))

    def before_content(self) -> None:
        """Handle object nesting before content

        :py:class:`PyObject` represents Python language constructs. For
        constructs that are nestable, such as a Python classes, this method will
        build up a stack of the nesting hierarchy so that it can be later
        de-nested correctly, in :py:meth:`after_content`.

        For constructs that aren't nestable, the stack is bypassed, and instead
        only the most recent object is tracked. This object prefix name will be
        removed with :py:meth:`after_content`.
        """
        prefix = None
        if self.names:
            # fullname and name_prefix come from the `handle_signature` method.
            # fullname represents the full object name that is constructed using
            # object nesting and explicit prefixes. `name_prefix` is the
            # explicit prefix given in a signature
            (fullname, name_prefix) = self.names[-1]
            if self.allow_nesting:
                prefix = fullname
            elif name_prefix:
                prefix = name_prefix.strip('.')
        if prefix:
            self.env.ref_context['py:class'] = prefix
            if self.allow_nesting:
                classes = self.env.ref_context.setdefault('py:classes', [])
                classes.append(prefix)
        if 'module' in self.options:
            modules = self.env.ref_context.setdefault('py:modules', [])
            modules.append(self.env.ref_context.get('py:module'))
            self.env.ref_context['py:module'] = self.options['module']

    def after_content(self) -> None:
        """Handle object de-nesting after content

        If this class is a nestable object, removing the last nested class prefix
        ends further nesting in the object.

        If this class is not a nestable object, the list of classes should not
        be altered as we didn't affect the nesting levels in
        :py:meth:`before_content`.
        """
        classes = self.env.ref_context.setdefault('py:classes', [])
        if self.allow_nesting:
            with contextlib.suppress(IndexError):
                classes.pop()

        self.env.ref_context['py:class'] = (classes[-1] if len(classes) > 0
                                            else None)
        if 'module' in self.options:
            modules = self.env.ref_context.setdefault('py:modules', [])
            if modules:
                self.env.ref_context['py:module'] = modules.pop()
            else:
                self.env.ref_context.pop('py:module')

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        if not sig_node.get('_toc_parts'):
            return ''

        config = self.env.app.config
        objtype = sig_node.parent.get('objtype')
        if config.add_function_parentheses and objtype in {'function', 'method'}:
            parens = '()'
        else:
            parens = ''
        *parents, name = sig_node['_toc_parts']
        if config.toc_object_entries_show_parents == 'domain':
            return sig_node.get('fullname', name) + parens
        if config.toc_object_entries_show_parents == 'hide':
            return name + parens
        if config.toc_object_entries_show_parents == 'all':
            return '.'.join(parents + [name + parens])
        return ''


class PyFunction(PyObject):
    """Description of a function."""

    option_spec: OptionSpec = PyObject.option_spec.copy()
    option_spec.update({
        'async': directives.flag,
    })

    def get_signature_prefix(self, sig: str) -> list[nodes.Node]:
        if 'async' in self.options:
            return [addnodes.desc_sig_keyword('', 'async'),
                    addnodes.desc_sig_space()]
        else:
            return []

    def needs_arglist(self) -> bool:
        return True

    def add_target_and_index(self, name_cls: tuple[str, str], sig: str,
                             signode: desc_signature) -> None:
        super().add_target_and_index(name_cls, sig, signode)
        if 'no-index-entry' not in self.options:
            modname = self.options.get('module', self.env.ref_context.get('py:module'))
            node_id = signode['ids'][0]

            name, cls = name_cls
            if modname:
                text = _('%s() (in module %s)') % (name, modname)
                self.indexnode['entries'].append(('single', text, node_id, '', None))
            else:
                text = f'built-in function; {name}()'
                self.indexnode['entries'].append(('pair', text, node_id, '', None))

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        # add index in own add_target_and_index() instead.
        return ''


class PyDecoratorFunction(PyFunction):
    """Description of a decorator."""

    def run(self) -> list[Node]:
        # a decorator function is a function after all
        self.name = 'py:function'
        return super().run()

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        ret = super().handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_addname('@', '@'))
        return ret

    def needs_arglist(self) -> bool:
        return False


class PyVariable(PyObject):
    """Description of a variable."""

    option_spec: OptionSpec = PyObject.option_spec.copy()
    option_spec.update({
        'type': directives.unchanged,
        'value': directives.unchanged,
    })

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        fullname, prefix = super().handle_signature(sig, signode)

        typ = self.options.get('type')
        if typ:
            annotations = _parse_annotation(typ, self.env)
            signode += addnodes.desc_annotation(typ, '',
                                                addnodes.desc_sig_punctuation('', ':'),
                                                addnodes.desc_sig_space(), *annotations)

        value = self.options.get('value')
        if value:
            signode += addnodes.desc_annotation(value, '',
                                                addnodes.desc_sig_space(),
                                                addnodes.desc_sig_punctuation('', '='),
                                                addnodes.desc_sig_space(),
                                                nodes.Text(value))

        return fullname, prefix

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        name, cls = name_cls
        if modname:
            return _('%s (in module %s)') % (name, modname)
        else:
            return _('%s (built-in variable)') % name


class PyClasslike(PyObject):
    """
    Description of a class-like object (classes, interfaces, exceptions).
    """

    option_spec: OptionSpec = PyObject.option_spec.copy()
    option_spec.update({
        'final': directives.flag,
    })

    allow_nesting = True

    def get_signature_prefix(self, sig: str) -> list[nodes.Node]:
        if 'final' in self.options:
            return [nodes.Text('final'), addnodes.desc_sig_space(),
                    nodes.Text(self.objtype), addnodes.desc_sig_space()]
        else:
            return [nodes.Text(self.objtype), addnodes.desc_sig_space()]

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        if self.objtype == 'class':
            if not modname:
                return _('%s (built-in class)') % name_cls[0]
            return _('%s (class in %s)') % (name_cls[0], modname)
        elif self.objtype == 'exception':
            return name_cls[0]
        else:
            return ''


class PyMethod(PyObject):
    """Description of a method."""

    option_spec: OptionSpec = PyObject.option_spec.copy()
    option_spec.update({
        'abstractmethod': directives.flag,
        'async': directives.flag,
        'classmethod': directives.flag,
        'final': directives.flag,
        'staticmethod': directives.flag,
    })

    def needs_arglist(self) -> bool:
        return True

    def get_signature_prefix(self, sig: str) -> list[nodes.Node]:
        prefix: list[nodes.Node] = []
        if 'final' in self.options:
            prefix.append(nodes.Text('final'))
            prefix.append(addnodes.desc_sig_space())
        if 'abstractmethod' in self.options:
            prefix.append(nodes.Text('abstract'))
            prefix.append(addnodes.desc_sig_space())
        if 'async' in self.options:
            prefix.append(nodes.Text('async'))
            prefix.append(addnodes.desc_sig_space())
        if 'classmethod' in self.options:
            prefix.append(nodes.Text('classmethod'))
            prefix.append(addnodes.desc_sig_space())
        if 'staticmethod' in self.options:
            prefix.append(nodes.Text('static'))
            prefix.append(addnodes.desc_sig_space())
        return prefix

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        name, cls = name_cls
        try:
            clsname, methname = name.rsplit('.', 1)
            if modname and self.env.config.add_module_names:
                clsname = '.'.join([modname, clsname])
        except ValueError:
            if modname:
                return _('%s() (in module %s)') % (name, modname)
            else:
                return '%s()' % name

        if 'classmethod' in self.options:
            return _('%s() (%s class method)') % (methname, clsname)
        elif 'staticmethod' in self.options:
            return _('%s() (%s static method)') % (methname, clsname)
        else:
            return _('%s() (%s method)') % (methname, clsname)


class PyClassMethod(PyMethod):
    """Description of a classmethod."""

    option_spec: OptionSpec = PyObject.option_spec.copy()

    def run(self) -> list[Node]:
        self.name = 'py:method'
        self.options['classmethod'] = True

        return super().run()


class PyStaticMethod(PyMethod):
    """Description of a staticmethod."""

    option_spec: OptionSpec = PyObject.option_spec.copy()

    def run(self) -> list[Node]:
        self.name = 'py:method'
        self.options['staticmethod'] = True

        return super().run()


class PyDecoratorMethod(PyMethod):
    """Description of a decoratormethod."""

    def run(self) -> list[Node]:
        self.name = 'py:method'
        return super().run()

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        ret = super().handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_addname('@', '@'))
        return ret

    def needs_arglist(self) -> bool:
        return False


class PyAttribute(PyObject):
    """Description of an attribute."""

    option_spec: OptionSpec = PyObject.option_spec.copy()
    option_spec.update({
        'type': directives.unchanged,
        'value': directives.unchanged,
    })

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        fullname, prefix = super().handle_signature(sig, signode)

        typ = self.options.get('type')
        if typ:
            annotations = _parse_annotation(typ, self.env)
            signode += addnodes.desc_annotation(typ, '',
                                                addnodes.desc_sig_punctuation('', ':'),
                                                addnodes.desc_sig_space(),
                                                *annotations)

        value = self.options.get('value')
        if value:
            signode += addnodes.desc_annotation(value, '',
                                                addnodes.desc_sig_space(),
                                                addnodes.desc_sig_punctuation('', '='),
                                                addnodes.desc_sig_space(),
                                                nodes.Text(value))

        return fullname, prefix

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        name, cls = name_cls
        try:
            clsname, attrname = name.rsplit('.', 1)
            if modname and self.env.config.add_module_names:
                clsname = '.'.join([modname, clsname])
        except ValueError:
            if modname:
                return _('%s (in module %s)') % (name, modname)
            else:
                return name

        return _('%s (%s attribute)') % (attrname, clsname)


class PyProperty(PyObject):
    """Description of an attribute."""

    option_spec = PyObject.option_spec.copy()
    option_spec.update({
        'abstractmethod': directives.flag,
        'classmethod': directives.flag,
        'type': directives.unchanged,
    })

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        fullname, prefix = super().handle_signature(sig, signode)

        typ = self.options.get('type')
        if typ:
            annotations = _parse_annotation(typ, self.env)
            signode += addnodes.desc_annotation(typ, '',
                                                addnodes.desc_sig_punctuation('', ':'),
                                                addnodes.desc_sig_space(),
                                                *annotations)

        return fullname, prefix

    def get_signature_prefix(self, sig: str) -> list[nodes.Node]:
        prefix: list[nodes.Node] = []
        if 'abstractmethod' in self.options:
            prefix.append(nodes.Text('abstract'))
            prefix.append(addnodes.desc_sig_space())
        if 'classmethod' in self.options:
            prefix.append(nodes.Text('class'))
            prefix.append(addnodes.desc_sig_space())

        prefix.append(nodes.Text('property'))
        prefix.append(addnodes.desc_sig_space())
        return prefix

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        name, cls = name_cls
        try:
            clsname, attrname = name.rsplit('.', 1)
            if modname and self.env.config.add_module_names:
                clsname = '.'.join([modname, clsname])
        except ValueError:
            if modname:
                return _('%s (in module %s)') % (name, modname)
            else:
                return name

        return _('%s (%s property)') % (attrname, clsname)


class PyModule(SphinxDirective):
    """
    Directive to mark description of a new module.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: OptionSpec = {
        'platform': lambda x: x,
        'synopsis': lambda x: x,
        'no-index': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindex': directives.flag,
        'nocontentsentry': directives.flag,
        'deprecated': directives.flag,
    }

    def run(self) -> list[Node]:
        domain = cast(PythonDomain, self.env.get_domain('py'))

        modname = self.arguments[0].strip()
        no_index = 'no-index' in self.options or 'noindex' in self.options
        self.env.ref_context['py:module'] = modname

        content_node: Element = nodes.section()
        # necessary so that the child nodes get the right source/line set
        content_node.document = self.state.document
        nested_parse_with_titles(self.state, self.content, content_node, self.content_offset)

        ret: list[Node] = []
        if not no_index:
            # note module to the domain
            node_id = make_id(self.env, self.state.document, 'module', modname)
            target = nodes.target('', '', ids=[node_id], ismod=True)
            self.set_source_info(target)
            self.state.document.note_explicit_target(target)

            domain.note_module(modname,
                               node_id,
                               self.options.get('synopsis', ''),
                               self.options.get('platform', ''),
                               'deprecated' in self.options)
            domain.note_object(modname, 'module', node_id, location=target)

            # the platform and synopsis aren't printed; in fact, they are only
            # used in the modindex currently
            indextext = f'module; {modname}'
            inode = addnodes.index(entries=[('pair', indextext, node_id, '', None)])
            # The node order is: index node first, then target node.
            ret.append(inode)
            ret.append(target)
        ret.extend(content_node.children)
        return ret


class PyCurrentModule(SphinxDirective):
    """
    This directive is just to tell Sphinx that we're documenting
    stuff in module foo, but links to module foo won't lead here.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        modname = self.arguments[0].strip()
        if modname == 'None':
            self.env.ref_context.pop('py:module', None)
        else:
            self.env.ref_context['py:module'] = modname
        return []


class PyXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element,
                     has_explicit_title: bool, title: str, target: str) -> tuple[str, str]:
        refnode['py:module'] = env.ref_context.get('py:module')
        refnode['py:class'] = env.ref_context.get('py:class')
        if not has_explicit_title:
            title = title.lstrip('.')    # only has a meaning for the target
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        # if the first character is a dot, search more specific namespaces first
        # else search builtins first
        if target[0:1] == '.':
            target = target[1:]
            refnode['refspecific'] = True
        return title, target


def filter_meta_fields(app: Sphinx, domain: str, objtype: str, content: Element) -> None:
    """Filter ``:meta:`` field from its docstring."""
    if domain != 'py':
        return

    for node in content:
        if isinstance(node, nodes.field_list):
            fields = cast(list[nodes.field], node)
            # removing list items while iterating the list needs reversed()
            for field in reversed(fields):
                field_name = cast(nodes.field_body, field[0]).astext().strip()
                if field_name == 'meta' or field_name.startswith('meta '):
                    node.remove(field)


class PythonModuleIndex(Index):
    """
    Index subclass to provide the Python module index.
    """

    name = 'modindex'
    localname = _('Python Module Index')
    shortname = _('modules')

    def generate(self, docnames: Iterable[str] | None = None,
                 ) -> tuple[list[tuple[str, list[IndexEntry]]], bool]:
        content: dict[str, list[IndexEntry]] = {}
        # list of prefixes to ignore
        ignores: list[str] = self.domain.env.config['modindex_common_prefix']
        ignores = sorted(ignores, key=len, reverse=True)
        # list of all modules, sorted by module name
        modules = sorted(self.domain.data['modules'].items(),
                         key=lambda x: x[0].lower())
        # sort out collapsible modules
        prev_modname = ''
        num_toplevels = 0
        for modname, (docname, node_id, synopsis, platforms, deprecated) in modules:
            if docnames and docname not in docnames:
                continue

            for ignore in ignores:
                if modname.startswith(ignore):
                    modname = modname[len(ignore):]
                    stripped = ignore
                    break
            else:
                stripped = ''

            # we stripped the whole module name?
            if not modname:
                modname, stripped = stripped, ''

            entries = content.setdefault(modname[0].lower(), [])

            package = modname.split('.')[0]
            if package != modname:
                # it's a submodule
                if prev_modname == package:
                    # first submodule - make parent a group head
                    if entries:
                        last = entries[-1]
                        entries[-1] = IndexEntry(last[0], 1, last[2], last[3],
                                                 last[4], last[5], last[6])
                elif not prev_modname.startswith(package):
                    # submodule without parent in list, add dummy entry
                    entries.append(IndexEntry(stripped + package, 1, '', '', '', '', ''))
                subtype = 2
            else:
                num_toplevels += 1
                subtype = 0

            qualifier = _('Deprecated') if deprecated else ''
            entries.append(IndexEntry(stripped + modname, subtype, docname,
                                      node_id, platforms, qualifier, synopsis))
            prev_modname = modname

        # apply heuristics when to collapse modindex at page load:
        # only collapse if number of toplevel modules is larger than
        # number of submodules
        collapse = len(modules) - num_toplevels < num_toplevels

        # sort by first letter
        sorted_content = sorted(content.items())

        return sorted_content, collapse


class PythonDomain(Domain):
    """Python language domain."""
    name = 'py'
    label = 'Python'
    object_types: dict[str, ObjType] = {
        'function':     ObjType(_('function'),      'func', 'obj'),
        'data':         ObjType(_('data'),          'data', 'obj'),
        'class':        ObjType(_('class'),         'class', 'exc', 'obj'),
        'exception':    ObjType(_('exception'),     'exc', 'class', 'obj'),
        'method':       ObjType(_('method'),        'meth', 'obj'),
        'classmethod':  ObjType(_('class method'),  'meth', 'obj'),
        'staticmethod': ObjType(_('static method'), 'meth', 'obj'),
        'attribute':    ObjType(_('attribute'),     'attr', 'obj'),
        'property':     ObjType(_('property'),      'attr', '_prop', 'obj'),
        'module':       ObjType(_('module'),        'mod', 'obj'),
    }

    directives = {
        'function':        PyFunction,
        'data':            PyVariable,
        'class':           PyClasslike,
        'exception':       PyClasslike,
        'method':          PyMethod,
        'classmethod':     PyClassMethod,
        'staticmethod':    PyStaticMethod,
        'attribute':       PyAttribute,
        'property':        PyProperty,
        'module':          PyModule,
        'currentmodule':   PyCurrentModule,
        'decorator':       PyDecoratorFunction,
        'decoratormethod': PyDecoratorMethod,
    }
    roles = {
        'data':  PyXRefRole(),
        'exc':   PyXRefRole(),
        'func':  PyXRefRole(fix_parens=True),
        'class': PyXRefRole(),
        'const': PyXRefRole(),
        'attr':  PyXRefRole(),
        'meth':  PyXRefRole(fix_parens=True),
        'mod':   PyXRefRole(),
        'obj':   PyXRefRole(),
    }
    initial_data: dict[str, dict[str, tuple[Any]]] = {
        'objects': {},  # fullname -> docname, objtype
        'modules': {},  # modname -> docname, synopsis, platform, deprecated
    }
    indices = [
        PythonModuleIndex,
    ]

    @property
    def objects(self) -> dict[str, ObjectEntry]:
        return self.data.setdefault('objects', {})  # fullname -> ObjectEntry

    def note_object(self, name: str, objtype: str, node_id: str,
                    aliased: bool = False, location: Any = None) -> None:
        """Note a python object for cross reference.

        .. versionadded:: 2.1
        """
        if name in self.objects:
            other = self.objects[name]
            if other.aliased and aliased is False:
                # The original definition found. Override it!
                pass
            elif other.aliased is False and aliased:
                # The original definition is already registered.
                return
            else:
                # duplicated
                logger.warning(__('duplicate object description of %s, '
                                  'other instance in %s, use :no-index: for one of them'),
                               name, other.docname, location=location)
        self.objects[name] = ObjectEntry(self.env.docname, node_id, objtype, aliased)

    @property
    def modules(self) -> dict[str, ModuleEntry]:
        return self.data.setdefault('modules', {})  # modname -> ModuleEntry

    def note_module(self, name: str, node_id: str, synopsis: str,
                    platform: str, deprecated: bool) -> None:
        """Note a python module for cross reference.

        .. versionadded:: 2.1
        """
        self.modules[name] = ModuleEntry(self.env.docname, node_id,
                                         synopsis, platform, deprecated)

    def clear_doc(self, docname: str) -> None:
        for fullname, obj in list(self.objects.items()):
            if obj.docname == docname:
                del self.objects[fullname]
        for modname, mod in list(self.modules.items()):
            if mod.docname == docname:
                del self.modules[modname]

    def merge_domaindata(self, docnames: list[str], otherdata: dict[str, Any]) -> None:
        # XXX check duplicates?
        for fullname, obj in otherdata['objects'].items():
            if obj.docname in docnames:
                self.objects[fullname] = obj
        for modname, mod in otherdata['modules'].items():
            if mod.docname in docnames:
                self.modules[modname] = mod

    def find_obj(self, env: BuildEnvironment, modname: str, classname: str,
                 name: str, type: str | None, searchmode: int = 0,
                 ) -> list[tuple[str, ObjectEntry]]:
        """Find a Python object for "name", perhaps using the given module
        and/or classname.  Returns a list of (name, object entry) tuples.
        """
        # skip parens
        if name[-2:] == '()':
            name = name[:-2]

        if not name:
            return []

        matches: list[tuple[str, ObjectEntry]] = []

        newname = None
        if searchmode == 1:
            if type is None:
                objtypes: list[str] | None = list(self.object_types)
            else:
                objtypes = self.objtypes_for_role(type)
            if objtypes is not None:
                if modname and classname:
                    fullname = modname + '.' + classname + '.' + name
                    if fullname in self.objects and self.objects[fullname].objtype in objtypes:
                        newname = fullname
                if not newname:
                    if modname and modname + '.' + name in self.objects and \
                       self.objects[modname + '.' + name].objtype in objtypes:
                        newname = modname + '.' + name
                    elif name in self.objects and self.objects[name].objtype in objtypes:
                        newname = name
                    else:
                        # "fuzzy" searching mode
                        searchname = '.' + name
                        matches = [(oname, self.objects[oname]) for oname in self.objects
                                   if oname.endswith(searchname) and
                                   self.objects[oname].objtype in objtypes]
        else:
            # NOTE: searching for exact match, object type is not considered
            if name in self.objects:
                newname = name
            elif type == 'mod':
                # only exact matches allowed for modules
                return []
            elif classname and classname + '.' + name in self.objects:
                newname = classname + '.' + name
            elif modname and modname + '.' + name in self.objects:
                newname = modname + '.' + name
            elif modname and classname and \
                    modname + '.' + classname + '.' + name in self.objects:
                newname = modname + '.' + classname + '.' + name
        if newname is not None:
            matches.append((newname, self.objects[newname]))
        return matches

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     type: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
        modname = node.get('py:module')
        clsname = node.get('py:class')
        searchmode = 1 if node.hasattr('refspecific') else 0
        matches = self.find_obj(env, modname, clsname, target,
                                type, searchmode)

        if not matches and type == 'attr':
            # fallback to meth (for property; Sphinx 2.4.x)
            # this ensures that `:attr:` role continues to refer to the old property entry
            # that defined by ``method`` directive in old reST files.
            matches = self.find_obj(env, modname, clsname, target, 'meth', searchmode)
        if not matches and type == 'meth':
            # fallback to attr (for property)
            # this ensures that `:meth:` in the old reST files can refer to the property
            # entry that defined by ``property`` directive.
            #
            # Note: _prop is a secret role only for internal look-up.
            matches = self.find_obj(env, modname, clsname, target, '_prop', searchmode)

        if not matches:
            return None
        elif len(matches) > 1:
            canonicals = [m for m in matches if not m[1].aliased]
            if len(canonicals) == 1:
                matches = canonicals
            else:
                logger.warning(__('more than one target found for cross-reference %r: %s'),
                               target, ', '.join(match[0] for match in matches),
                               type='ref', subtype='python', location=node)
        name, obj = matches[0]

        if obj[2] == 'module':
            return self._make_module_refnode(builder, fromdocname, name, contnode)
        else:
            # determine the content of the reference by conditions
            content = find_pending_xref_condition(node, 'resolved')
            if content:
                children = content.children
            else:
                # if not found, use contnode
                children = [contnode]

            return make_refnode(builder, fromdocname, obj[0], obj[1], children, name)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        modname = node.get('py:module')
        clsname = node.get('py:class')
        results: list[tuple[str, Element]] = []

        # always search in "refspecific" mode with the :any: role
        matches = self.find_obj(env, modname, clsname, target, None, 1)
        multiple_matches = len(matches) > 1

        for name, obj in matches:

            if multiple_matches and obj.aliased:
                # Skip duplicated matches
                continue

            if obj[2] == 'module':
                results.append(('py:mod',
                                self._make_module_refnode(builder, fromdocname,
                                                          name, contnode)))
            else:
                # determine the content of the reference by conditions
                content = find_pending_xref_condition(node, 'resolved')
                if content:
                    children = content.children
                else:
                    # if not found, use contnode
                    children = [contnode]

                role = 'py:' + self.role_for_objtype(obj[2])  # type: ignore[operator]
                results.append((role, make_refnode(builder, fromdocname, obj[0], obj[1],
                                                   children, name)))
        return results

    def _make_module_refnode(self, builder: Builder, fromdocname: str, name: str,
                             contnode: Node) -> Element:
        # get additional info for modules
        module = self.modules[name]
        title = name
        if module.synopsis:
            title += ': ' + module.synopsis
        if module.deprecated:
            title += _(' (deprecated)')
        if module.platform:
            title += ' (' + module.platform + ')'
        return make_refnode(builder, fromdocname, module.docname, module.node_id,
                            contnode, title)

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        for modname, mod in self.modules.items():
            yield (modname, modname, 'module', mod.docname, mod.node_id, 0)
        for refname, obj in self.objects.items():
            if obj.objtype != 'module':  # modules are already handled
                if obj.aliased:
                    # aliased names are not full-text searchable.
                    yield (refname, refname, obj.objtype, obj.docname, obj.node_id, -1)
                else:
                    yield (refname, refname, obj.objtype, obj.docname, obj.node_id, 1)

    def get_full_qualified_name(self, node: Element) -> str | None:
        modname = node.get('py:module')
        clsname = node.get('py:class')
        target = node.get('reftarget')
        if target is None:
            return None
        else:
            return '.'.join(filter(None, [modname, clsname, target]))


def builtin_resolver(app: Sphinx, env: BuildEnvironment,
                     node: pending_xref, contnode: Element) -> Element | None:
    """Do not emit nitpicky warnings for built-in types."""
    def istyping(s: str) -> bool:
        if s.startswith('typing.'):
            s = s.split('.', 1)[1]

        return s in typing.__all__

    if node.get('refdomain') != 'py':
        return None
    elif node.get('reftype') in ('class', 'obj') and node.get('reftarget') == 'None':
        return contnode
    elif node.get('reftype') in ('class', 'obj', 'exc'):
        reftarget = node.get('reftarget')
        if inspect.isclass(getattr(builtins, reftarget, None)):
            # built-in class
            return contnode
        if istyping(reftarget):
            # typing class
            return contnode

    return None


def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension('sphinx.directives')

    app.add_domain(PythonDomain)
    app.add_config_value('python_use_unqualified_type_names', False, 'env')
    app.add_config_value('python_maximum_signature_line_length', None, 'env',
                         types={int, None})
    app.add_config_value('python_display_short_literal_types', False, 'env')
    app.connect('object-description-transform', filter_meta_fields)
    app.connect('missing-reference', builtin_resolver, priority=900)

    return {
        'version': 'builtin',
        'env_version': 4,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
