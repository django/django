"""The C language domain."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union, cast

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.locale import _, __
from sphinx.roles import SphinxRole, XRefRole
from sphinx.transforms import SphinxTransform
from sphinx.transforms.post_transforms import ReferencesResolver
from sphinx.util import logging
from sphinx.util.cfamily import (
    ASTAttributeList,
    ASTBaseBase,
    ASTBaseParenExprList,
    BaseParser,
    DefinitionError,
    NoOldIdError,
    StringifyTransform,
    UnsupportedMultiCharacterCharLiteral,
    anon_identifier_re,
    binary_literal_re,
    char_literal_re,
    float_literal_re,
    float_literal_suffix_re,
    hex_literal_re,
    identifier_re,
    integer_literal_re,
    integers_literal_suffix_re,
    octal_literal_re,
    verify_description_mode,
)
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from docutils.nodes import Element, Node, TextElement, system_message

    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec

logger = logging.getLogger(__name__)
T = TypeVar('T')

DeclarationType = Union[
    "ASTStruct", "ASTUnion", "ASTEnum", "ASTEnumerator",
    "ASTType", "ASTTypeWithInit", "ASTMacro",
]

# https://en.cppreference.com/w/c/keyword
_keywords = [
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double',
    'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'inline', 'int', 'long',
    'register', 'restrict', 'return', 'short', 'signed', 'sizeof', 'static', 'struct',
    'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
    '_Alignas', '_Alignof', '_Atomic', '_Bool', '_Complex',
    '_Decimal32', '_Decimal64', '_Decimal128',
    '_Generic', '_Imaginary', '_Noreturn', '_Static_assert', '_Thread_local',
]
# These are only keyword'y when the corresponding headers are included.
# They are used as default value for c_extra_keywords.
_macroKeywords = [
    'alignas', 'alignof', 'bool', 'complex', 'imaginary', 'noreturn', 'static_assert',
    'thread_local',
]

# these are ordered by precedence
_expression_bin_ops = [
    ['||', 'or'],
    ['&&', 'and'],
    ['|', 'bitor'],
    ['^', 'xor'],
    ['&', 'bitand'],
    ['==', '!=', 'not_eq'],
    ['<=', '>=', '<', '>'],
    ['<<', '>>'],
    ['+', '-'],
    ['*', '/', '%'],
    ['.*', '->*'],
]
_expression_unary_ops = ["++", "--", "*", "&", "+", "-", "!", "not", "~", "compl"]
_expression_assignment_ops = ["=", "*=", "/=", "%=", "+=", "-=",
                              ">>=", "<<=", "&=", "and_eq", "^=", "xor_eq", "|=", "or_eq"]

_max_id = 1
_id_prefix = [None, 'c.', 'Cv2.']
# Ids are used in lookup keys which are used across pickled files,
# so when _max_id changes, make sure to update the ENV_VERSION.

_string_re = re.compile(r"[LuU8]?('([^'\\]*(?:\\.[^'\\]*)*)'"
                        r'|"([^"\\]*(?:\\.[^"\\]*)*)")', re.S)

# bool, complex, and imaginary are macro "keywords", so they are handled separately
_simple_type_specifiers_re = re.compile(r"""
    \b(
    void|_Bool
    |signed|unsigned
    |short|long
    |char
    |int
    |__uint128|__int128
    |__int(8|16|32|64|128)  # extension
    |float|double
    |_Decimal(32|64|128)
    |_Complex|_Imaginary
    |__float80|_Float64x|__float128|_Float128|__ibm128  # extension
    |__fp16  # extension
    |_Sat|_Fract|fract|_Accum|accum  # extension
    )\b
""", re.VERBOSE)


class _DuplicateSymbolError(Exception):
    def __init__(self, symbol: Symbol, declaration: ASTDeclaration) -> None:
        assert symbol
        assert declaration
        self.symbol = symbol
        self.declaration = declaration

    def __str__(self) -> str:
        return "Internal C duplicate symbol error:\n%s" % self.symbol.dump(0)


class ASTBase(ASTBaseBase):
    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))


# Names
################################################################################

class ASTIdentifier(ASTBaseBase):
    def __init__(self, identifier: str) -> None:
        assert identifier is not None
        assert len(identifier) != 0
        self.identifier = identifier

    def __eq__(self, other: Any) -> bool:
        return type(other) is ASTIdentifier and self.identifier == other.identifier

    def is_anon(self) -> bool:
        return self.identifier[0] == '@'

    # and this is where we finally make a difference between __str__ and the display string

    def __str__(self) -> str:
        return self.identifier

    def get_display_string(self) -> str:
        return "[anonymous]" if self.is_anon() else self.identifier

    def describe_signature(self, signode: TextElement, mode: str, env: BuildEnvironment,
                           prefix: str, symbol: Symbol) -> None:
        # note: slightly different signature of describe_signature due to the prefix
        verify_description_mode(mode)
        if self.is_anon():
            node = addnodes.desc_sig_name(text="[anonymous]")
        else:
            node = addnodes.desc_sig_name(self.identifier, self.identifier)
        if mode == 'markType':
            targetText = prefix + self.identifier
            pnode = addnodes.pending_xref('', refdomain='c',
                                          reftype='identifier',
                                          reftarget=targetText, modname=None,
                                          classname=None)
            pnode['c:parent_key'] = symbol.get_lookup_key()
            pnode += node
            signode += pnode
        elif mode == 'lastIsName':
            nameNode = addnodes.desc_name()
            nameNode += node
            signode += nameNode
        elif mode == 'noneIsName':
            signode += node
        else:
            raise Exception('Unknown description mode: %s' % mode)


class ASTNestedName(ASTBase):
    def __init__(self, names: list[ASTIdentifier], rooted: bool) -> None:
        assert len(names) > 0
        self.names = names
        self.rooted = rooted

    @property
    def name(self) -> ASTNestedName:
        return self

    def get_id(self, version: int) -> str:
        return '.'.join(str(n) for n in self.names)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = '.'.join(transform(n) for n in self.names)
        if self.rooted:
            return '.' + res
        else:
            return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        # just print the name part, with template args, not template params
        if mode == 'noneIsName':
            if self.rooted:
                unreachable = "Can this happen?"
                raise AssertionError(unreachable)  # TODO
                signode += nodes.Text('.')
            for i in range(len(self.names)):
                if i != 0:
                    unreachable = "Can this happen?"
                    raise AssertionError(unreachable)  # TODO
                    signode += nodes.Text('.')
                n = self.names[i]
                n.describe_signature(signode, mode, env, '', symbol)
        elif mode == 'param':
            assert not self.rooted, str(self)
            assert len(self.names) == 1
            self.names[0].describe_signature(signode, 'noneIsName', env, '', symbol)
        elif mode in ('markType', 'lastIsName', 'markName'):
            # Each element should be a pending xref targeting the complete
            # prefix.
            prefix = ''
            first = True
            names = self.names[:-1] if mode == 'lastIsName' else self.names
            # If lastIsName, then wrap all of the prefix in a desc_addname,
            # else append directly to signode.
            # TODO: also for C?
            #  NOTE: Breathe previously relied on the prefix being in the desc_addname node,
            #       so it can remove it in inner declarations.
            dest = signode
            if mode == 'lastIsName':
                dest = addnodes.desc_addname()
            if self.rooted:
                prefix += '.'
                if mode == 'lastIsName' and len(names) == 0:
                    signode += addnodes.desc_sig_punctuation('.', '.')
                else:
                    dest += addnodes.desc_sig_punctuation('.', '.')
            for i in range(len(names)):
                ident = names[i]
                if not first:
                    dest += addnodes.desc_sig_punctuation('.', '.')
                    prefix += '.'
                first = False
                txt_ident = str(ident)
                if txt_ident != '':
                    ident.describe_signature(dest, 'markType', env, prefix, symbol)
                prefix += txt_ident
            if mode == 'lastIsName':
                if len(self.names) > 1:
                    dest += addnodes.desc_sig_punctuation('.', '.')
                    signode += dest
                self.names[-1].describe_signature(signode, mode, env, '', symbol)
        else:
            raise Exception('Unknown description mode: %s' % mode)


################################################################################
# Expressions
################################################################################

class ASTExpression(ASTBase):
    pass


# Primary expressions
################################################################################

class ASTLiteral(ASTExpression):
    pass


class ASTBooleanLiteral(ASTLiteral):
    def __init__(self, value: bool) -> None:
        self.value = value

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.value:
            return 'true'
        else:
            return 'false'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        txt = str(self)
        signode += addnodes.desc_sig_keyword(txt, txt)


class ASTNumberLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data

    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        txt = str(self)
        signode += addnodes.desc_sig_literal_number(txt, txt)


class ASTCharLiteral(ASTLiteral):
    def __init__(self, prefix: str, data: str) -> None:
        self.prefix = prefix  # may be None when no prefix
        self.data = data
        decoded = data.encode().decode('unicode-escape')
        if len(decoded) == 1:
            self.value = ord(decoded)
        else:
            raise UnsupportedMultiCharacterCharLiteral(decoded)

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.prefix is None:
            return "'" + self.data + "'"
        else:
            return self.prefix + "'" + self.data + "'"

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        txt = str(self)
        signode += addnodes.desc_sig_literal_char(txt, txt)


class ASTStringLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data

    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        txt = str(self)
        signode += addnodes.desc_sig_literal_string(txt, txt)


class ASTIdExpression(ASTExpression):
    def __init__(self, name: ASTNestedName):
        # note: this class is basically to cast a nested name as an expression
        self.name = name

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.name)

    def get_id(self, version: int) -> str:
        return self.name.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.name.describe_signature(signode, mode, env, symbol)


class ASTParenExpr(ASTExpression):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return '(' + transform(self.expr) + ')'

    def get_id(self, version: int) -> str:
        return self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


# Postfix expressions
################################################################################

class ASTPostfixOp(ASTBase):
    pass


class ASTPostfixCallExpr(ASTPostfixOp):
    def __init__(self, lst: ASTParenExprList | ASTBracedInitList) -> None:
        self.lst = lst

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.lst)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.lst.describe_signature(signode, mode, env, symbol)


class ASTPostfixArray(ASTPostfixOp):
    def __init__(self, expr: ASTExpression) -> None:
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return '[' + transform(self.expr) + ']'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('[', '[')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(']', ']')


class ASTPostfixInc(ASTPostfixOp):
    def _stringify(self, transform: StringifyTransform) -> str:
        return '++'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('++', '++')


class ASTPostfixDec(ASTPostfixOp):
    def _stringify(self, transform: StringifyTransform) -> str:
        return '--'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('--', '--')


class ASTPostfixMemberOfPointer(ASTPostfixOp):
    def __init__(self, name):
        self.name = name

    def _stringify(self, transform: StringifyTransform) -> str:
        return '->' + transform(self.name)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('->', '->')
        self.name.describe_signature(signode, 'noneIsName', env, symbol)


class ASTPostfixExpr(ASTExpression):
    def __init__(self, prefix: ASTExpression, postFixes: list[ASTPostfixOp]):
        self.prefix = prefix
        self.postFixes = postFixes

    def _stringify(self, transform: StringifyTransform) -> str:
        res = [transform(self.prefix)]
        for p in self.postFixes:
            res.append(transform(p))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.prefix.describe_signature(signode, mode, env, symbol)
        for p in self.postFixes:
            p.describe_signature(signode, mode, env, symbol)


# Unary expressions
################################################################################

class ASTUnaryOpExpr(ASTExpression):
    def __init__(self, op: str, expr: ASTExpression):
        self.op = op
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.op[0] in 'cn':
            return self.op + " " + transform(self.expr)
        else:
            return self.op + transform(self.expr)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.op[0] in 'cn':
            signode += addnodes.desc_sig_keyword(self.op, self.op)
            signode += addnodes.desc_sig_space()
        else:
            signode += addnodes.desc_sig_operator(self.op, self.op)
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTSizeofType(ASTExpression):
    def __init__(self, typ):
        self.typ = typ

    def _stringify(self, transform: StringifyTransform) -> str:
        return "sizeof(" + transform(self.typ) + ")"

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('sizeof', 'sizeof')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTSizeofExpr(ASTExpression):
    def __init__(self, expr: ASTExpression):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return "sizeof " + transform(self.expr)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('sizeof', 'sizeof')
        signode += addnodes.desc_sig_space()
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTAlignofExpr(ASTExpression):
    def __init__(self, typ: ASTType):
        self.typ = typ

    def _stringify(self, transform: StringifyTransform) -> str:
        return "alignof(" + transform(self.typ) + ")"

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('alignof', 'alignof')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


# Other expressions
################################################################################

class ASTCastExpr(ASTExpression):
    def __init__(self, typ: ASTType, expr: ASTExpression):
        self.typ = typ
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['(']
        res.append(transform(self.typ))
        res.append(')')
        res.append(transform(self.expr))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTBinOpExpr(ASTBase):
    def __init__(self, exprs: list[ASTExpression], ops: list[str]):
        assert len(exprs) > 0
        assert len(exprs) == len(ops) + 1
        self.exprs = exprs
        self.ops = ops

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.exprs[0]))
        for i in range(1, len(self.exprs)):
            res.append(' ')
            res.append(self.ops[i - 1])
            res.append(' ')
            res.append(transform(self.exprs[i]))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.exprs[0].describe_signature(signode, mode, env, symbol)
        for i in range(1, len(self.exprs)):
            signode += addnodes.desc_sig_space()
            op = self.ops[i - 1]
            if ord(op[0]) >= ord('a') and ord(op[0]) <= ord('z'):
                signode += addnodes.desc_sig_keyword(op, op)
            else:
                signode += addnodes.desc_sig_operator(op, op)
            signode += addnodes.desc_sig_space()
            self.exprs[i].describe_signature(signode, mode, env, symbol)


class ASTAssignmentExpr(ASTExpression):
    def __init__(self, exprs: list[ASTExpression], ops: list[str]):
        assert len(exprs) > 0
        assert len(exprs) == len(ops) + 1
        self.exprs = exprs
        self.ops = ops

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.exprs[0]))
        for i in range(1, len(self.exprs)):
            res.append(' ')
            res.append(self.ops[i - 1])
            res.append(' ')
            res.append(transform(self.exprs[i]))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.exprs[0].describe_signature(signode, mode, env, symbol)
        for i in range(1, len(self.exprs)):
            signode += addnodes.desc_sig_space()
            op = self.ops[i - 1]
            if ord(op[0]) >= ord('a') and ord(op[0]) <= ord('z'):
                signode += addnodes.desc_sig_keyword(op, op)
            else:
                signode += addnodes.desc_sig_operator(op, op)
            signode += addnodes.desc_sig_space()
            self.exprs[i].describe_signature(signode, mode, env, symbol)


class ASTFallbackExpr(ASTExpression):
    def __init__(self, expr: str):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return self.expr

    def get_id(self, version: int) -> str:
        return str(self.expr)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += nodes.literal(self.expr, self.expr)


################################################################################
# Types
################################################################################

class ASTTrailingTypeSpec(ASTBase):
    pass


class ASTTrailingTypeSpecFundamental(ASTTrailingTypeSpec):
    def __init__(self, names: list[str]) -> None:
        assert len(names) != 0
        self.names = names

    def _stringify(self, transform: StringifyTransform) -> str:
        return ' '.join(self.names)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        first = True
        for n in self.names:
            if not first:
                signode += addnodes.desc_sig_space()
            else:
                first = False
            signode += addnodes.desc_sig_keyword_type(n, n)


class ASTTrailingTypeSpecName(ASTTrailingTypeSpec):
    def __init__(self, prefix: str, nestedName: ASTNestedName) -> None:
        self.prefix = prefix
        self.nestedName = nestedName

    @property
    def name(self) -> ASTNestedName:
        return self.nestedName

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.prefix:
            res.append(self.prefix)
            res.append(' ')
        res.append(transform(self.nestedName))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.prefix:
            signode += addnodes.desc_sig_keyword(self.prefix, self.prefix)
            signode += addnodes.desc_sig_space()
        self.nestedName.describe_signature(signode, mode, env, symbol=symbol)


class ASTFunctionParameter(ASTBase):
    def __init__(self, arg: ASTTypeWithInit | None, ellipsis: bool = False) -> None:
        self.arg = arg
        self.ellipsis = ellipsis

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        # the anchor will be our parent
        return symbol.parent.declaration.get_id(version, prefixed=False)

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.ellipsis:
            return '...'
        else:
            return transform(self.arg)

    def describe_signature(self, signode: Any, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.ellipsis:
            signode += addnodes.desc_sig_punctuation('...', '...')
        else:
            self.arg.describe_signature(signode, mode, env, symbol=symbol)


class ASTParameters(ASTBase):
    def __init__(self, args: list[ASTFunctionParameter], attrs: ASTAttributeList) -> None:
        self.args = args
        self.attrs = attrs

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.args

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append('(')
        first = True
        for a in self.args:
            if not first:
                res.append(', ')
            first = False
            res.append(str(a))
        res.append(')')
        if len(self.attrs) != 0:
            res.append(' ')
            res.append(transform(self.attrs))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        multi_line_parameter_list = False
        test_node: Element = signode
        while test_node.parent:
            if not isinstance(test_node, addnodes.desc_signature):
                test_node = test_node.parent
                continue
            multi_line_parameter_list = test_node.get('multi_line_parameter_list', False)
            break

        # only use the desc_parameterlist for the outer list, not for inner lists
        if mode == 'lastIsName':
            paramlist = addnodes.desc_parameterlist()
            paramlist['multi_line_parameter_list'] = multi_line_parameter_list
            for arg in self.args:
                param = addnodes.desc_parameter('', '', noemph=True)
                arg.describe_signature(param, 'param', env, symbol=symbol)
                paramlist += param
            signode += paramlist
        else:
            signode += addnodes.desc_sig_punctuation('(', '(')
            first = True
            for arg in self.args:
                if not first:
                    signode += addnodes.desc_sig_punctuation(',', ',')
                    signode += addnodes.desc_sig_space()
                first = False
                arg.describe_signature(signode, 'markType', env, symbol=symbol)
            signode += addnodes.desc_sig_punctuation(')', ')')

        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
            self.attrs.describe_signature(signode)


class ASTDeclSpecsSimple(ASTBaseBase):
    def __init__(self, storage: str, threadLocal: str, inline: bool,
                 restrict: bool, volatile: bool, const: bool, attrs: ASTAttributeList) -> None:
        self.storage = storage
        self.threadLocal = threadLocal
        self.inline = inline
        self.restrict = restrict
        self.volatile = volatile
        self.const = const
        self.attrs = attrs

    def mergeWith(self, other: ASTDeclSpecsSimple) -> ASTDeclSpecsSimple:
        if not other:
            return self
        return ASTDeclSpecsSimple(self.storage or other.storage,
                                  self.threadLocal or other.threadLocal,
                                  self.inline or other.inline,
                                  self.volatile or other.volatile,
                                  self.const or other.const,
                                  self.restrict or other.restrict,
                                  self.attrs + other.attrs)

    def _stringify(self, transform: StringifyTransform) -> str:
        res: list[str] = []
        if len(self.attrs) != 0:
            res.append(transform(self.attrs))
        if self.storage:
            res.append(self.storage)
        if self.threadLocal:
            res.append(self.threadLocal)
        if self.inline:
            res.append('inline')
        if self.restrict:
            res.append('restrict')
        if self.volatile:
            res.append('volatile')
        if self.const:
            res.append('const')
        return ' '.join(res)

    def describe_signature(self, modifiers: list[Node]) -> None:
        def _add(modifiers: list[Node], text: str) -> None:
            if len(modifiers) != 0:
                modifiers.append(addnodes.desc_sig_space())
            modifiers.append(addnodes.desc_sig_keyword(text, text))

        if len(modifiers) != 0 and len(self.attrs) != 0:
            modifiers.append(addnodes.desc_sig_space())
        tempNode = nodes.TextElement()
        self.attrs.describe_signature(tempNode)
        modifiers.extend(tempNode.children)
        if self.storage:
            _add(modifiers, self.storage)
        if self.threadLocal:
            _add(modifiers, self.threadLocal)
        if self.inline:
            _add(modifiers, 'inline')
        if self.restrict:
            _add(modifiers, 'restrict')
        if self.volatile:
            _add(modifiers, 'volatile')
        if self.const:
            _add(modifiers, 'const')


class ASTDeclSpecs(ASTBase):
    def __init__(self, outer: str,
                 leftSpecs: ASTDeclSpecsSimple,
                 rightSpecs: ASTDeclSpecsSimple,
                 trailing: ASTTrailingTypeSpec) -> None:
        # leftSpecs and rightSpecs are used for output
        # allSpecs are used for id generation TODO: remove?
        self.outer = outer
        self.leftSpecs = leftSpecs
        self.rightSpecs = rightSpecs
        self.allSpecs = self.leftSpecs.mergeWith(self.rightSpecs)
        self.trailingTypeSpec = trailing

    def _stringify(self, transform: StringifyTransform) -> str:
        res: list[str] = []
        l = transform(self.leftSpecs)
        if len(l) > 0:
            res.append(l)
        if self.trailingTypeSpec:
            if len(res) > 0:
                res.append(" ")
            res.append(transform(self.trailingTypeSpec))
            r = str(self.rightSpecs)
            if len(r) > 0:
                if len(res) > 0:
                    res.append(" ")
                res.append(r)
        return "".join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        modifiers: list[Node] = []

        self.leftSpecs.describe_signature(modifiers)

        for m in modifiers:
            signode += m
        if self.trailingTypeSpec:
            if len(modifiers) > 0:
                signode += addnodes.desc_sig_space()
            self.trailingTypeSpec.describe_signature(signode, mode, env,
                                                     symbol=symbol)
            modifiers = []
            self.rightSpecs.describe_signature(modifiers)
            if len(modifiers) > 0:
                signode += addnodes.desc_sig_space()
            for m in modifiers:
                signode += m


# Declarator
################################################################################

class ASTArray(ASTBase):
    def __init__(self, static: bool, const: bool, volatile: bool, restrict: bool,
                 vla: bool, size: ASTExpression):
        self.static = static
        self.const = const
        self.volatile = volatile
        self.restrict = restrict
        self.vla = vla
        self.size = size
        if vla:
            assert size is None
        if size is not None:
            assert not vla

    def _stringify(self, transform: StringifyTransform) -> str:
        el = []
        if self.static:
            el.append('static')
        if self.restrict:
            el.append('restrict')
        if self.volatile:
            el.append('volatile')
        if self.const:
            el.append('const')
        if self.vla:
            return '[' + ' '.join(el) + '*]'
        elif self.size:
            el.append(transform(self.size))
        return '[' + ' '.join(el) + ']'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('[', '[')
        addSpace = False

        def _add(signode: TextElement, text: str) -> bool:
            if addSpace:
                signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_keyword(text, text)
            return True

        if self.static:
            addSpace = _add(signode, 'static')
        if self.restrict:
            addSpace = _add(signode, 'restrict')
        if self.volatile:
            addSpace = _add(signode, 'volatile')
        if self.const:
            addSpace = _add(signode, 'const')
        if self.vla:
            signode += addnodes.desc_sig_punctuation('*', '*')
        elif self.size:
            if addSpace:
                signode += addnodes.desc_sig_space()
            self.size.describe_signature(signode, 'markType', env, symbol)
        signode += addnodes.desc_sig_punctuation(']', ']')


class ASTDeclarator(ASTBase):
    @property
    def name(self) -> ASTNestedName:
        raise NotImplementedError(repr(self))

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        raise NotImplementedError(repr(self))

    def require_space_after_declSpecs(self) -> bool:
        raise NotImplementedError(repr(self))


class ASTDeclaratorNameParam(ASTDeclarator):
    def __init__(self, declId: ASTNestedName,
                 arrayOps: list[ASTArray], param: ASTParameters) -> None:
        self.declId = declId
        self.arrayOps = arrayOps
        self.param = param

    @property
    def name(self) -> ASTNestedName:
        return self.declId

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.param.function_params

    # ------------------------------------------------------------------------

    def require_space_after_declSpecs(self) -> bool:
        return self.declId is not None

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.declId:
            res.append(transform(self.declId))
        for op in self.arrayOps:
            res.append(transform(op))
        if self.param:
            res.append(transform(self.param))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.declId:
            self.declId.describe_signature(signode, mode, env, symbol)
        for op in self.arrayOps:
            op.describe_signature(signode, mode, env, symbol)
        if self.param:
            self.param.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorNameBitField(ASTDeclarator):
    def __init__(self, declId: ASTNestedName, size: ASTExpression):
        self.declId = declId
        self.size = size

    @property
    def name(self) -> ASTNestedName:
        return self.declId

    # ------------------------------------------------------------------------

    def require_space_after_declSpecs(self) -> bool:
        return self.declId is not None

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.declId:
            res.append(transform(self.declId))
        res.append(" : ")
        res.append(transform(self.size))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.declId:
            self.declId.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_space()
        signode += addnodes.desc_sig_punctuation(':', ':')
        signode += addnodes.desc_sig_space()
        self.size.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorPtr(ASTDeclarator):
    def __init__(self, next: ASTDeclarator, restrict: bool, volatile: bool, const: bool,
                 attrs: ASTAttributeList) -> None:
        assert next
        self.next = next
        self.restrict = restrict
        self.volatile = volatile
        self.const = const
        self.attrs = attrs

    @property
    def name(self) -> ASTNestedName:
        return self.next.name

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.next.function_params

    def require_space_after_declSpecs(self) -> bool:
        return self.const or self.volatile or self.restrict or \
            len(self.attrs) > 0 or \
            self.next.require_space_after_declSpecs()

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['*']
        res.append(transform(self.attrs))
        if len(self.attrs) != 0 and (self.restrict or self.volatile or self.const):
            res.append(' ')
        if self.restrict:
            res.append('restrict')
        if self.volatile:
            if self.restrict:
                res.append(' ')
            res.append('volatile')
        if self.const:
            if self.restrict or self.volatile:
                res.append(' ')
            res.append('const')
        if self.const or self.volatile or self.restrict or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs():
                res.append(' ')
        res.append(transform(self.next))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('*', '*')
        self.attrs.describe_signature(signode)
        if len(self.attrs) != 0 and (self.restrict or self.volatile or self.const):
            signode += addnodes.desc_sig_space()

        def _add_anno(signode: TextElement, text: str) -> None:
            signode += addnodes.desc_sig_keyword(text, text)

        if self.restrict:
            _add_anno(signode, 'restrict')
        if self.volatile:
            if self.restrict:
                signode += addnodes.desc_sig_space()
            _add_anno(signode, 'volatile')
        if self.const:
            if self.restrict or self.volatile:
                signode += addnodes.desc_sig_space()
            _add_anno(signode, 'const')
        if self.const or self.volatile or self.restrict or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs():
                signode += addnodes.desc_sig_space()
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorParen(ASTDeclarator):
    def __init__(self, inner: ASTDeclarator, next: ASTDeclarator) -> None:
        assert inner
        assert next
        self.inner = inner
        self.next = next
        # TODO: we assume the name and params are in inner

    @property
    def name(self) -> ASTNestedName:
        return self.inner.name

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.inner.function_params

    def require_space_after_declSpecs(self) -> bool:
        return True

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['(']
        res.append(transform(self.inner))
        res.append(')')
        res.append(transform(self.next))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.inner.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')
        self.next.describe_signature(signode, "noneIsName", env, symbol)


# Initializer
################################################################################

class ASTParenExprList(ASTBaseParenExprList):
    def __init__(self, exprs: list[ASTExpression]) -> None:
        self.exprs = exprs

    def _stringify(self, transform: StringifyTransform) -> str:
        exprs = [transform(e) for e in self.exprs]
        return '(%s)' % ', '.join(exprs)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('(', '(')
        first = True
        for e in self.exprs:
            if not first:
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            else:
                first = False
            e.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTBracedInitList(ASTBase):
    def __init__(self, exprs: list[ASTExpression], trailingComma: bool) -> None:
        self.exprs = exprs
        self.trailingComma = trailingComma

    def _stringify(self, transform: StringifyTransform) -> str:
        exprs = ', '.join(transform(e) for e in self.exprs)
        trailingComma = ',' if self.trailingComma else ''
        return f'{{{exprs}{trailingComma}}}'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('{', '{')
        first = True
        for e in self.exprs:
            if not first:
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            else:
                first = False
            e.describe_signature(signode, mode, env, symbol)
        if self.trailingComma:
            signode += addnodes.desc_sig_punctuation(',', ',')
        signode += addnodes.desc_sig_punctuation('}', '}')


class ASTInitializer(ASTBase):
    def __init__(self, value: ASTBracedInitList | ASTExpression,
                 hasAssign: bool = True) -> None:
        self.value = value
        self.hasAssign = hasAssign

    def _stringify(self, transform: StringifyTransform) -> str:
        val = transform(self.value)
        if self.hasAssign:
            return ' = ' + val
        else:
            return val

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.hasAssign:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('=', '=')
            signode += addnodes.desc_sig_space()
        self.value.describe_signature(signode, 'markType', env, symbol)


class ASTType(ASTBase):
    def __init__(self, declSpecs: ASTDeclSpecs, decl: ASTDeclarator) -> None:
        assert declSpecs
        assert decl
        self.declSpecs = declSpecs
        self.decl = decl

    @property
    def name(self) -> ASTNestedName:
        return self.decl.name

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.decl.function_params

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        declSpecs = transform(self.declSpecs)
        res.append(declSpecs)
        if self.decl.require_space_after_declSpecs() and len(declSpecs) > 0:
            res.append(' ')
        res.append(transform(self.decl))
        return ''.join(res)

    def get_type_declaration_prefix(self) -> str:
        if self.declSpecs.trailingTypeSpec:
            return 'typedef'
        else:
            return 'type'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.declSpecs.describe_signature(signode, 'markType', env, symbol)
        if (self.decl.require_space_after_declSpecs() and
                len(str(self.declSpecs)) > 0):
            signode += addnodes.desc_sig_space()
        # for parameters that don't really declare new names we get 'markType',
        # this should not be propagated, but be 'noneIsName'.
        if mode == 'markType':
            mode = 'noneIsName'
        self.decl.describe_signature(signode, mode, env, symbol)


class ASTTypeWithInit(ASTBase):
    def __init__(self, type: ASTType, init: ASTInitializer) -> None:
        self.type = type
        self.init = init

    @property
    def name(self) -> ASTNestedName:
        return self.type.name

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return self.type.get_id(version, objectType, symbol)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.type))
        if self.init:
            res.append(transform(self.init))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.type.describe_signature(signode, mode, env, symbol)
        if self.init:
            self.init.describe_signature(signode, mode, env, symbol)


class ASTMacroParameter(ASTBase):
    def __init__(self, arg: ASTNestedName | None, ellipsis: bool = False,
                 variadic: bool = False) -> None:
        self.arg = arg
        self.ellipsis = ellipsis
        self.variadic = variadic

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.ellipsis:
            return '...'
        elif self.variadic:
            return transform(self.arg) + '...'
        else:
            return transform(self.arg)

    def describe_signature(self, signode: Any, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.ellipsis:
            signode += addnodes.desc_sig_punctuation('...', '...')
        elif self.variadic:
            name = str(self)
            signode += addnodes.desc_sig_name(name, name)
        else:
            self.arg.describe_signature(signode, mode, env, symbol=symbol)


class ASTMacro(ASTBase):
    def __init__(self, ident: ASTNestedName, args: list[ASTMacroParameter] | None) -> None:
        self.ident = ident
        self.args = args

    @property
    def name(self) -> ASTNestedName:
        return self.ident

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.ident))
        if self.args is not None:
            res.append('(')
            first = True
            for arg in self.args:
                if not first:
                    res.append(', ')
                first = False
                res.append(transform(arg))
            res.append(')')
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.ident.describe_signature(signode, mode, env, symbol)
        if self.args is None:
            return
        paramlist = addnodes.desc_parameterlist()
        for arg in self.args:
            param = addnodes.desc_parameter('', '', noemph=True)
            arg.describe_signature(param, 'param', env, symbol=symbol)
            paramlist += param
        signode += paramlist


class ASTStruct(ASTBase):
    def __init__(self, name: ASTNestedName) -> None:
        self.name = name

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.name)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)


class ASTUnion(ASTBase):
    def __init__(self, name: ASTNestedName) -> None:
        self.name = name

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.name)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)


class ASTEnum(ASTBase):
    def __init__(self, name: ASTNestedName) -> None:
        self.name = name

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.name)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)


class ASTEnumerator(ASTBase):
    def __init__(self, name: ASTNestedName, init: ASTInitializer | None,
                 attrs: ASTAttributeList) -> None:
        self.name = name
        self.init = init
        self.attrs = attrs

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.name))
        if len(self.attrs) != 0:
            res.append(' ')
            res.append(transform(self.attrs))
        if self.init:
            res.append(transform(self.init))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol)
        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
            self.attrs.describe_signature(signode)
        if self.init:
            self.init.describe_signature(signode, 'markType', env, symbol)


class ASTDeclaration(ASTBaseBase):
    def __init__(self, objectType: str, directiveType: str | None,
                 declaration: DeclarationType | ASTFunctionParameter,
                 semicolon: bool = False) -> None:
        self.objectType = objectType
        self.directiveType = directiveType
        self.declaration = declaration
        self.semicolon = semicolon

        self.symbol: Symbol = None
        # set by CObject._add_enumerator_to_parent
        self.enumeratorScopedSymbol: Symbol = None

    def clone(self) -> ASTDeclaration:
        return ASTDeclaration(self.objectType, self.directiveType,
                              self.declaration.clone(), self.semicolon)

    @property
    def name(self) -> ASTNestedName:
        decl = cast(DeclarationType, self.declaration)
        return decl.name

    @property
    def function_params(self) -> list[ASTFunctionParameter] | None:
        if self.objectType != 'function':
            return None
        decl = cast(ASTType, self.declaration)
        return decl.function_params

    def get_id(self, version: int, prefixed: bool = True) -> str:
        if self.objectType == 'enumerator' and self.enumeratorScopedSymbol:
            return self.enumeratorScopedSymbol.declaration.get_id(version, prefixed)
        id_ = self.declaration.get_id(version, self.objectType, self.symbol)
        if prefixed:
            return _id_prefix[version] + id_
        else:
            return id_

    def get_newest_id(self) -> str:
        return self.get_id(_max_id, True)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.declaration)
        if self.semicolon:
            res += ';'
        return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, options: dict) -> None:
        verify_description_mode(mode)
        assert self.symbol
        # The caller of the domain added a desc_signature node.
        # Always enable multiline:
        signode['is_multiline'] = True
        # Put each line in a desc_signature_line node.
        mainDeclNode = addnodes.desc_signature_line()
        mainDeclNode.sphinx_line_type = 'declarator'
        mainDeclNode['add_permalink'] = not self.symbol.isRedeclaration
        signode += mainDeclNode

        if self.objectType in {'member', 'function', 'macro'}:
            pass
        elif self.objectType == 'struct':
            mainDeclNode += addnodes.desc_sig_keyword('struct', 'struct')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'union':
            mainDeclNode += addnodes.desc_sig_keyword('union', 'union')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'enum':
            mainDeclNode += addnodes.desc_sig_keyword('enum', 'enum')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'enumerator':
            mainDeclNode += addnodes.desc_sig_keyword('enumerator', 'enumerator')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'type':
            decl = cast(ASTType, self.declaration)
            prefix = decl.get_type_declaration_prefix()
            mainDeclNode += addnodes.desc_sig_keyword(prefix, prefix)
            mainDeclNode += addnodes.desc_sig_space()
        else:
            raise AssertionError
        self.declaration.describe_signature(mainDeclNode, mode, env, self.symbol)
        if self.semicolon:
            mainDeclNode += addnodes.desc_sig_punctuation(';', ';')


class SymbolLookupResult:
    def __init__(self, symbols: Iterator[Symbol], parentSymbol: Symbol,
                 ident: ASTIdentifier) -> None:
        self.symbols = symbols
        self.parentSymbol = parentSymbol
        self.ident = ident


class LookupKey:
    def __init__(self, data: list[tuple[ASTIdentifier, str]]) -> None:
        self.data = data

    def __str__(self) -> str:
        inner = ', '.join(f"({ident}, {id_})" for ident, id_ in self.data)
        return f'[{inner}]'


class Symbol:
    debug_indent = 0
    debug_indent_string = "  "
    debug_lookup = False
    debug_show_tree = False

    def __copy__(self):
        raise AssertionError  # shouldn't happen

    def __deepcopy__(self, memo):
        if self.parent:
            raise AssertionError  # shouldn't happen
        # the domain base class makes a copy of the initial data, which is fine
        return Symbol(None, None, None, None, None)

    @staticmethod
    def debug_print(*args: Any) -> None:
        logger.debug(Symbol.debug_indent_string * Symbol.debug_indent, end="")
        logger.debug(*args)

    def _assert_invariants(self) -> None:
        if not self.parent:
            # parent == None means global scope, so declaration means a parent
            assert not self.declaration
            assert not self.docname
        else:
            if self.declaration:
                assert self.docname

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "children":
            raise AssertionError
        return super().__setattr__(key, value)

    def __init__(
        self,
        parent: Symbol,
        ident: ASTIdentifier,
        declaration: ASTDeclaration | None,
        docname: str | None,
        line: int | None,
    ) -> None:
        self.parent = parent
        # declarations in a single directive are linked together
        self.siblingAbove: Symbol = None
        self.siblingBelow: Symbol = None
        self.ident = ident
        self.declaration = declaration
        self.docname = docname
        self.line = line
        self.isRedeclaration = False
        self._assert_invariants()

        # Remember to modify Symbol.remove if modifications to the parent change.
        self._children: list[Symbol] = []
        self._anonChildren: list[Symbol] = []
        # note: _children includes _anonChildren
        if self.parent:
            self.parent._children.append(self)
        if self.declaration:
            self.declaration.symbol = self

        # Do symbol addition after self._children has been initialised.
        self._add_function_params()

    def _fill_empty(self, declaration: ASTDeclaration, docname: str, line: int) -> None:
        self._assert_invariants()
        assert self.declaration is None
        assert self.docname is None
        assert self.line is None
        assert declaration is not None
        assert docname is not None
        assert line is not None
        self.declaration = declaration
        self.declaration.symbol = self
        self.docname = docname
        self.line = line
        self._assert_invariants()
        # and symbol addition should be done as well
        self._add_function_params()

    def _add_function_params(self) -> None:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_add_function_params:")
        # Note: we may be called from _fill_empty, so the symbols we want
        #       to add may actually already be present (as empty symbols).

        # add symbols for function parameters, if any
        if self.declaration is not None and self.declaration.function_params is not None:
            for p in self.declaration.function_params:
                if p.arg is None:
                    continue
                nn = p.arg.name
                if nn is None:
                    continue
                # (comparing to the template params: we have checked that we are a declaration)
                decl = ASTDeclaration('functionParam', None, p)
                assert not nn.rooted
                assert len(nn.names) == 1
                self._add_symbols(nn, decl, self.docname, self.line)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1

    def remove(self) -> None:
        if self.parent is None:
            return
        assert self in self.parent._children
        self.parent._children.remove(self)
        self.parent = None

    def clear_doc(self, docname: str) -> None:
        for sChild in self._children:
            sChild.clear_doc(docname)
            if sChild.declaration and sChild.docname == docname:
                sChild.declaration = None
                sChild.docname = None
                sChild.line = None
                if sChild.siblingAbove is not None:
                    sChild.siblingAbove.siblingBelow = sChild.siblingBelow
                if sChild.siblingBelow is not None:
                    sChild.siblingBelow.siblingAbove = sChild.siblingAbove
                sChild.siblingAbove = None
                sChild.siblingBelow = None

    def get_all_symbols(self) -> Iterator[Symbol]:
        yield self
        for sChild in self._children:
            yield from sChild.get_all_symbols()

    @property
    def children(self) -> Iterator[Symbol]:
        yield from self._children

    @property
    def children_recurse_anon(self) -> Iterator[Symbol]:
        for c in self._children:
            yield c
            if not c.ident.is_anon():
                continue
            yield from c.children_recurse_anon

    def get_lookup_key(self) -> LookupKey:
        # The pickle files for the environment and for each document are distinct.
        # The environment has all the symbols, but the documents has xrefs that
        # must know their scope. A lookup key is essentially a specification of
        # how to find a specific symbol.
        symbols = []
        s = self
        while s.parent:
            symbols.append(s)
            s = s.parent
        symbols.reverse()
        key = []
        for s in symbols:
            if s.declaration is not None:
                # TODO: do we need the ID?
                key.append((s.ident, s.declaration.get_newest_id()))
            else:
                key.append((s.ident, None))
        return LookupKey(key)

    def get_full_nested_name(self) -> ASTNestedName:
        symbols = []
        s = self
        while s.parent:
            symbols.append(s)
            s = s.parent
        symbols.reverse()
        names = []
        for s in symbols:
            names.append(s.ident)
        return ASTNestedName(names, rooted=False)

    def _find_first_named_symbol(self, ident: ASTIdentifier,
                                 matchSelf: bool, recurseInAnon: bool) -> Symbol | None:
        # TODO: further simplification from C++ to C
        if Symbol.debug_lookup:
            Symbol.debug_print("_find_first_named_symbol ->")
        res = self._find_named_symbols(ident, matchSelf, recurseInAnon,
                                       searchInSiblings=False)
        try:
            return next(res)
        except StopIteration:
            return None

    def _find_named_symbols(self, ident: ASTIdentifier,
                            matchSelf: bool, recurseInAnon: bool,
                            searchInSiblings: bool) -> Iterator[Symbol]:
        # TODO: further simplification from C++ to C
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_find_named_symbols:")
            Symbol.debug_indent += 1
            Symbol.debug_print("self:")
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_print("ident:            ", ident)
            Symbol.debug_print("matchSelf:        ", matchSelf)
            Symbol.debug_print("recurseInAnon:    ", recurseInAnon)
            Symbol.debug_print("searchInSiblings: ", searchInSiblings)

        def candidates() -> Generator[Symbol, None, None]:
            s = self
            if Symbol.debug_lookup:
                Symbol.debug_print("searching in self:")
                logger.debug(s.to_string(Symbol.debug_indent + 1), end="")
            while True:
                if matchSelf:
                    yield s
                if recurseInAnon:
                    yield from s.children_recurse_anon
                else:
                    yield from s._children

                if s.siblingAbove is None:
                    break
                s = s.siblingAbove
                if Symbol.debug_lookup:
                    Symbol.debug_print("searching in sibling:")
                    logger.debug(s.to_string(Symbol.debug_indent + 1), end="")

        for s in candidates():
            if Symbol.debug_lookup:
                Symbol.debug_print("candidate:")
                logger.debug(s.to_string(Symbol.debug_indent + 1), end="")
            if s.ident == ident:
                if Symbol.debug_lookup:
                    Symbol.debug_indent += 1
                    Symbol.debug_print("matches")
                    Symbol.debug_indent -= 3
                yield s
                if Symbol.debug_lookup:
                    Symbol.debug_indent += 2
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 2

    def _symbol_lookup(
        self,
        nestedName: ASTNestedName,
        onMissingQualifiedSymbol: Callable[[Symbol, ASTIdentifier], Symbol | None],
        ancestorLookupType: str | None,
        matchSelf: bool,
        recurseInAnon: bool,
        searchInSiblings: bool,
    ) -> SymbolLookupResult | None:
        # TODO: further simplification from C++ to C
        # ancestorLookupType: if not None, specifies the target type of the lookup
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_symbol_lookup:")
            Symbol.debug_indent += 1
            Symbol.debug_print("self:")
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_print("nestedName:        ", nestedName)
            Symbol.debug_print("ancestorLookupType:", ancestorLookupType)
            Symbol.debug_print("matchSelf:         ", matchSelf)
            Symbol.debug_print("recurseInAnon:     ", recurseInAnon)
            Symbol.debug_print("searchInSiblings:  ", searchInSiblings)

        names = nestedName.names

        # find the right starting point for lookup
        parentSymbol = self
        if nestedName.rooted:
            while parentSymbol.parent:
                parentSymbol = parentSymbol.parent
        if ancestorLookupType is not None:
            # walk up until we find the first identifier
            firstName = names[0]
            while parentSymbol.parent:
                if parentSymbol.find_identifier(firstName,
                                                matchSelf=matchSelf,
                                                recurseInAnon=recurseInAnon,
                                                searchInSiblings=searchInSiblings):
                    break
                parentSymbol = parentSymbol.parent

        if Symbol.debug_lookup:
            Symbol.debug_print("starting point:")
            logger.debug(parentSymbol.to_string(Symbol.debug_indent + 1), end="")

        # and now the actual lookup
        for ident in names[:-1]:
            symbol = parentSymbol._find_first_named_symbol(
                ident, matchSelf=matchSelf, recurseInAnon=recurseInAnon)
            if symbol is None:
                symbol = onMissingQualifiedSymbol(parentSymbol, ident)
                if symbol is None:
                    if Symbol.debug_lookup:
                        Symbol.debug_indent -= 2
                    return None
            # We have now matched part of a nested name, and need to match more
            # so even if we should matchSelf before, we definitely shouldn't
            # even more. (see also issue #2666)
            matchSelf = False
            parentSymbol = symbol

        if Symbol.debug_lookup:
            Symbol.debug_print("handle last name from:")
            logger.debug(parentSymbol.to_string(Symbol.debug_indent + 1), end="")

        # handle the last name
        ident = names[-1]

        symbols = parentSymbol._find_named_symbols(
            ident, matchSelf=matchSelf,
            recurseInAnon=recurseInAnon,
            searchInSiblings=searchInSiblings)
        if Symbol.debug_lookup:
            symbols = list(symbols)  # type: ignore[assignment]
            Symbol.debug_indent -= 2
        return SymbolLookupResult(symbols, parentSymbol, ident)

    def _add_symbols(
        self,
        nestedName: ASTNestedName,
        declaration: ASTDeclaration | None,
        docname: str | None,
        line: int | None,
    ) -> Symbol:
        # TODO: further simplification from C++ to C
        # Used for adding a whole path of symbols, where the last may or may not
        # be an actual declaration.

        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_add_symbols:")
            Symbol.debug_indent += 1
            Symbol.debug_print("nn:       ", nestedName)
            Symbol.debug_print("decl:     ", declaration)
            Symbol.debug_print(f"location: {docname}:{line}")

        def onMissingQualifiedSymbol(parentSymbol: Symbol, ident: ASTIdentifier) -> Symbol:
            if Symbol.debug_lookup:
                Symbol.debug_indent += 1
                Symbol.debug_print("_add_symbols, onMissingQualifiedSymbol:")
                Symbol.debug_indent += 1
                Symbol.debug_print("ident: ", ident)
                Symbol.debug_indent -= 2
            return Symbol(parent=parentSymbol, ident=ident,
                          declaration=None, docname=None, line=None)

        lookupResult = self._symbol_lookup(nestedName,
                                           onMissingQualifiedSymbol,
                                           ancestorLookupType=None,
                                           matchSelf=False,
                                           recurseInAnon=False,
                                           searchInSiblings=False)
        assert lookupResult is not None  # we create symbols all the way, so that can't happen
        symbols = list(lookupResult.symbols)
        if len(symbols) == 0:
            if Symbol.debug_lookup:
                Symbol.debug_print("_add_symbols, result, no symbol:")
                Symbol.debug_indent += 1
                Symbol.debug_print("ident:       ", lookupResult.ident)
                Symbol.debug_print("declaration: ", declaration)
                Symbol.debug_print(f"location:    {docname}:{line}")
                Symbol.debug_indent -= 1
            symbol = Symbol(parent=lookupResult.parentSymbol,
                            ident=lookupResult.ident,
                            declaration=declaration,
                            docname=docname, line=line)
            if Symbol.debug_lookup:
                Symbol.debug_indent -= 2
            return symbol

        if Symbol.debug_lookup:
            Symbol.debug_print("_add_symbols, result, symbols:")
            Symbol.debug_indent += 1
            Symbol.debug_print("number symbols:", len(symbols))
            Symbol.debug_indent -= 1

        if not declaration:
            if Symbol.debug_lookup:
                Symbol.debug_print("no declaration")
                Symbol.debug_indent -= 2
            # good, just a scope creation
            # TODO: what if we have more than one symbol?
            return symbols[0]

        noDecl = []
        withDecl = []
        dupDecl = []
        for s in symbols:
            if s.declaration is None:
                noDecl.append(s)
            elif s.isRedeclaration:
                dupDecl.append(s)
            else:
                withDecl.append(s)
        if Symbol.debug_lookup:
            Symbol.debug_print("#noDecl:  ", len(noDecl))
            Symbol.debug_print("#withDecl:", len(withDecl))
            Symbol.debug_print("#dupDecl: ", len(dupDecl))

        # With partial builds we may start with a large symbol tree stripped of declarations.
        # Essentially any combination of noDecl, withDecl, and dupDecls seems possible.
        # TODO: make partial builds fully work. What should happen when the primary symbol gets
        #  deleted, and other duplicates exist? The full document should probably be rebuild.

        # First check if one of those with a declaration matches.
        # If it's a function, we need to compare IDs,
        # otherwise there should be only one symbol with a declaration.
        def makeCandSymbol() -> Symbol:
            if Symbol.debug_lookup:
                Symbol.debug_print("begin: creating candidate symbol")
            symbol = Symbol(parent=lookupResult.parentSymbol,
                            ident=lookupResult.ident,
                            declaration=declaration,
                            docname=docname, line=line)
            if Symbol.debug_lookup:
                Symbol.debug_print("end:   creating candidate symbol")
            return symbol

        if len(withDecl) == 0:
            candSymbol = None
        else:
            candSymbol = makeCandSymbol()

            def handleDuplicateDeclaration(symbol: Symbol, candSymbol: Symbol) -> None:
                if Symbol.debug_lookup:
                    Symbol.debug_indent += 1
                    Symbol.debug_print("redeclaration")
                    Symbol.debug_indent -= 1
                    Symbol.debug_indent -= 2
                # Redeclaration of the same symbol.
                # Let the new one be there, but raise an error to the client
                # so it can use the real symbol as subscope.
                # This will probably result in a duplicate id warning.
                candSymbol.isRedeclaration = True
                raise _DuplicateSymbolError(symbol, declaration)

            if declaration.objectType != "function":
                assert len(withDecl) <= 1
                handleDuplicateDeclaration(withDecl[0], candSymbol)
                # (not reachable)

            # a function, so compare IDs
            candId = declaration.get_newest_id()
            if Symbol.debug_lookup:
                Symbol.debug_print("candId:", candId)
            for symbol in withDecl:
                oldId = symbol.declaration.get_newest_id()
                if Symbol.debug_lookup:
                    Symbol.debug_print("oldId: ", oldId)
                if candId == oldId:
                    handleDuplicateDeclaration(symbol, candSymbol)
                    # (not reachable)
            # no candidate symbol found with matching ID
        # if there is an empty symbol, fill that one
        if len(noDecl) == 0:
            if Symbol.debug_lookup:
                Symbol.debug_print(
                    "no match, no empty, candSybmol is not None?:", candSymbol is not None,
                )
                Symbol.debug_indent -= 2
            if candSymbol is not None:
                return candSymbol
            else:
                return makeCandSymbol()
        else:
            if Symbol.debug_lookup:
                Symbol.debug_print(
                    "no match, but fill an empty declaration, candSybmol is not None?:",
                    candSymbol is not None)
                Symbol.debug_indent -= 2
            if candSymbol is not None:
                candSymbol.remove()
            # assert len(noDecl) == 1
            # TODO: enable assertion when we at some point find out how to do cleanup
            # for now, just take the first one, it should work fine ... right?
            symbol = noDecl[0]
            # If someone first opened the scope, and then later
            # declares it, e.g,
            # .. namespace:: Test
            # .. namespace:: nullptr
            # .. class:: Test
            symbol._fill_empty(declaration, docname, line)
            return symbol

    def merge_with(self, other: Symbol, docnames: list[str],
                   env: BuildEnvironment) -> None:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("merge_with:")
        assert other is not None
        for otherChild in other._children:
            ourChild = self._find_first_named_symbol(
                ident=otherChild.ident, matchSelf=False,
                recurseInAnon=False)
            if ourChild is None:
                # TODO: hmm, should we prune by docnames?
                self._children.append(otherChild)
                otherChild.parent = self
                otherChild._assert_invariants()
                continue
            if otherChild.declaration and otherChild.docname in docnames:
                if not ourChild.declaration:
                    ourChild._fill_empty(otherChild.declaration,
                                         otherChild.docname, otherChild.line)
                elif ourChild.docname != otherChild.docname:
                    name = str(ourChild.declaration)
                    msg = __("Duplicate C declaration, also defined at %s:%s.\n"
                             "Declaration is '.. c:%s:: %s'.")
                    msg = msg % (ourChild.docname, ourChild.line,
                                 ourChild.declaration.directiveType, name)
                    logger.warning(msg, location=(otherChild.docname, otherChild.line))
                else:
                    # Both have declarations, and in the same docname.
                    # This can apparently happen, it should be safe to
                    # just ignore it, right?
                    pass
            ourChild.merge_with(otherChild, docnames, env)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1

    def add_name(self, nestedName: ASTNestedName) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("add_name:")
        res = self._add_symbols(nestedName, declaration=None, docname=None, line=None)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1
        return res

    def add_declaration(self, declaration: ASTDeclaration,
                        docname: str, line: int) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("add_declaration:")
        assert declaration is not None
        assert docname is not None
        assert line is not None
        nestedName = declaration.name
        res = self._add_symbols(nestedName, declaration, docname, line)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1
        return res

    def find_identifier(self, ident: ASTIdentifier,
                        matchSelf: bool, recurseInAnon: bool, searchInSiblings: bool,
                        ) -> Symbol | None:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("find_identifier:")
            Symbol.debug_indent += 1
            Symbol.debug_print("ident:           ", ident)
            Symbol.debug_print("matchSelf:       ", matchSelf)
            Symbol.debug_print("recurseInAnon:   ", recurseInAnon)
            Symbol.debug_print("searchInSiblings:", searchInSiblings)
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_indent -= 2
        current = self
        while current is not None:
            if Symbol.debug_lookup:
                Symbol.debug_indent += 2
                Symbol.debug_print("trying:")
                logger.debug(current.to_string(Symbol.debug_indent + 1), end="")
                Symbol.debug_indent -= 2
            if matchSelf and current.ident == ident:
                return current
            children = current.children_recurse_anon if recurseInAnon else current._children
            for s in children:
                if s.ident == ident:
                    return s
            if not searchInSiblings:
                break
            current = current.siblingAbove
        return None

    def direct_lookup(self, key: LookupKey) -> Symbol | None:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("direct_lookup:")
            Symbol.debug_indent += 1
        s = self
        for name, id_ in key.data:
            res = None
            for cand in s._children:
                if cand.ident == name:
                    res = cand
                    break
            s = res
            if Symbol.debug_lookup:
                Symbol.debug_print("name:          ", name)
                Symbol.debug_print("id:            ", id_)
                if s is not None:
                    logger.debug(s.to_string(Symbol.debug_indent + 1), end="")
                else:
                    Symbol.debug_print("not found")
            if s is None:
                if Symbol.debug_lookup:
                    Symbol.debug_indent -= 2
                return None
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 2
        return s

    def find_declaration(self, nestedName: ASTNestedName, typ: str,
                         matchSelf: bool, recurseInAnon: bool) -> Symbol | None:
        # templateShorthand: missing template parameter lists for templates is ok
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("find_declaration:")

        def onMissingQualifiedSymbol(
            parentSymbol: Symbol,
            ident: ASTIdentifier,
        ) -> Symbol | None:
            return None

        lookupResult = self._symbol_lookup(nestedName,
                                           onMissingQualifiedSymbol,
                                           ancestorLookupType=typ,
                                           matchSelf=matchSelf,
                                           recurseInAnon=recurseInAnon,
                                           searchInSiblings=False)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1
        if lookupResult is None:
            return None

        symbols = list(lookupResult.symbols)
        if len(symbols) == 0:
            return None
        return symbols[0]

    def to_string(self, indent: int) -> str:
        res = [Symbol.debug_indent_string * indent]
        if not self.parent:
            res.append('::')
        else:
            if self.ident:
                res.append(str(self.ident))
            else:
                res.append(str(self.declaration))
            if self.declaration:
                res.append(": ")
                if self.isRedeclaration:
                    res.append('!!duplicate!! ')
                res.append(str(self.declaration))
        if self.docname:
            res.append('\t(')
            res.append(self.docname)
            res.append(')')
        res.append('\n')
        return ''.join(res)

    def dump(self, indent: int) -> str:
        res = [self.to_string(indent)]
        for c in self._children:
            res.append(c.dump(indent + 1))
        return ''.join(res)


class DefinitionParser(BaseParser):
    @property
    def language(self) -> str:
        return 'C'

    @property
    def id_attributes(self):
        return self.config.c_id_attributes

    @property
    def paren_attributes(self):
        return self.config.c_paren_attributes

    def _parse_string(self) -> str | None:
        if self.current_char != '"':
            return None
        startPos = self.pos
        self.pos += 1
        escape = False
        while True:
            if self.eof:
                self.fail("Unexpected end during inside string.")
            elif self.current_char == '"' and not escape:
                self.pos += 1
                break
            elif self.current_char == '\\':
                escape = True
            else:
                escape = False
            self.pos += 1
        return self.definition[startPos:self.pos]

    def _parse_literal(self) -> ASTLiteral | None:
        # -> integer-literal
        #  | character-literal
        #  | floating-literal
        #  | string-literal
        #  | boolean-literal -> "false" | "true"
        self.skip_ws()
        if self.skip_word('true'):
            return ASTBooleanLiteral(True)
        if self.skip_word('false'):
            return ASTBooleanLiteral(False)
        pos = self.pos
        if self.match(float_literal_re):
            self.match(float_literal_suffix_re)
            return ASTNumberLiteral(self.definition[pos:self.pos])
        for regex in [binary_literal_re, hex_literal_re,
                      integer_literal_re, octal_literal_re]:
            if self.match(regex):
                self.match(integers_literal_suffix_re)
                return ASTNumberLiteral(self.definition[pos:self.pos])

        string = self._parse_string()
        if string is not None:
            return ASTStringLiteral(string)

        # character-literal
        if self.match(char_literal_re):
            prefix = self.last_match.group(1)  # may be None when no prefix
            data = self.last_match.group(2)
            try:
                return ASTCharLiteral(prefix, data)
            except UnicodeDecodeError as e:
                self.fail("Can not handle character literal. Internal error was: %s" % e)
            except UnsupportedMultiCharacterCharLiteral:
                self.fail("Can not handle character literal"
                          " resulting in multiple decoded characters.")
        return None

    def _parse_paren_expression(self) -> ASTExpression | None:
        # "(" expression ")"
        if self.current_char != '(':
            return None
        self.pos += 1
        res = self._parse_expression()
        self.skip_ws()
        if not self.skip_string(')'):
            self.fail("Expected ')' in end of parenthesized expression.")
        return ASTParenExpr(res)

    def _parse_primary_expression(self) -> ASTExpression | None:
        # literal
        # "(" expression ")"
        # id-expression -> we parse this with _parse_nested_name
        self.skip_ws()
        res: ASTExpression | None = self._parse_literal()
        if res is not None:
            return res
        res = self._parse_paren_expression()
        if res is not None:
            return res
        nn = self._parse_nested_name()
        if nn is not None:
            return ASTIdExpression(nn)
        return None

    def _parse_initializer_list(self, name: str, open: str, close: str,
                                ) -> tuple[list[ASTExpression], bool]:
        # Parse open and close with the actual initializer-list in between
        # -> initializer-clause '...'[opt]
        #  | initializer-list ',' initializer-clause '...'[opt]
        # TODO: designators
        self.skip_ws()
        if not self.skip_string_and_ws(open):
            return None, None
        if self.skip_string(close):
            return [], False

        exprs = []
        trailingComma = False
        while True:
            self.skip_ws()
            expr = self._parse_expression()
            self.skip_ws()
            exprs.append(expr)
            self.skip_ws()
            if self.skip_string(close):
                break
            if not self.skip_string_and_ws(','):
                self.fail(f"Error in {name}, expected ',' or '{close}'.")
            if self.current_char == close and close == '}':
                self.pos += 1
                trailingComma = True
                break
        return exprs, trailingComma

    def _parse_paren_expression_list(self) -> ASTParenExprList | None:
        # -> '(' expression-list ')'
        # though, we relax it to also allow empty parens
        # as it's needed in some cases
        #
        # expression-list
        # -> initializer-list
        exprs, trailingComma = self._parse_initializer_list("parenthesized expression-list",
                                                            '(', ')')
        if exprs is None:
            return None
        return ASTParenExprList(exprs)

    def _parse_braced_init_list(self) -> ASTBracedInitList | None:
        # -> '{' initializer-list ','[opt] '}'
        #  | '{' '}'
        exprs, trailingComma = self._parse_initializer_list("braced-init-list", '{', '}')
        if exprs is None:
            return None
        return ASTBracedInitList(exprs, trailingComma)

    def _parse_postfix_expression(self) -> ASTPostfixExpr:
        # -> primary
        #  | postfix "[" expression "]"
        #  | postfix "[" braced-init-list [opt] "]"
        #  | postfix "(" expression-list [opt] ")"
        #  | postfix "." id-expression  // taken care of in primary by nested name
        #  | postfix "->" id-expression
        #  | postfix "++"
        #  | postfix "--"

        prefix = self._parse_primary_expression()

        # and now parse postfixes
        postFixes: list[ASTPostfixOp] = []
        while True:
            self.skip_ws()
            if self.skip_string_and_ws('['):
                expr = self._parse_expression()
                self.skip_ws()
                if not self.skip_string(']'):
                    self.fail("Expected ']' in end of postfix expression.")
                postFixes.append(ASTPostfixArray(expr))
                continue
            if self.skip_string('->'):
                if self.skip_string('*'):
                    # don't steal the arrow
                    self.pos -= 3
                else:
                    name = self._parse_nested_name()
                    postFixes.append(ASTPostfixMemberOfPointer(name))
                    continue
            if self.skip_string('++'):
                postFixes.append(ASTPostfixInc())
                continue
            if self.skip_string('--'):
                postFixes.append(ASTPostfixDec())
                continue
            lst = self._parse_paren_expression_list()
            if lst is not None:
                postFixes.append(ASTPostfixCallExpr(lst))
                continue
            break
        return ASTPostfixExpr(prefix, postFixes)

    def _parse_unary_expression(self) -> ASTExpression:
        # -> postfix
        #  | "++" cast
        #  | "--" cast
        #  | unary-operator cast -> (* | & | + | - | ! | ~) cast
        # The rest:
        #  | "sizeof" unary
        #  | "sizeof" "(" type-id ")"
        #  | "alignof" "(" type-id ")"
        self.skip_ws()
        for op in _expression_unary_ops:
            # TODO: hmm, should we be able to backtrack here?
            if op[0] in 'cn':
                res = self.skip_word(op)
            else:
                res = self.skip_string(op)
            if res:
                expr = self._parse_cast_expression()
                return ASTUnaryOpExpr(op, expr)
        if self.skip_word_and_ws('sizeof'):
            if self.skip_string_and_ws('('):
                typ = self._parse_type(named=False)
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail("Expecting ')' to end 'sizeof'.")
                return ASTSizeofType(typ)
            expr = self._parse_unary_expression()
            return ASTSizeofExpr(expr)
        if self.skip_word_and_ws('alignof'):
            if not self.skip_string_and_ws('('):
                self.fail("Expecting '(' after 'alignof'.")
            typ = self._parse_type(named=False)
            self.skip_ws()
            if not self.skip_string(')'):
                self.fail("Expecting ')' to end 'alignof'.")
            return ASTAlignofExpr(typ)
        return self._parse_postfix_expression()

    def _parse_cast_expression(self) -> ASTExpression:
        # -> unary  | "(" type-id ")" cast
        pos = self.pos
        self.skip_ws()
        if self.skip_string('('):
            try:
                typ = self._parse_type(False)
                if not self.skip_string(')'):
                    self.fail("Expected ')' in cast expression.")
                expr = self._parse_cast_expression()
                return ASTCastExpr(typ, expr)
            except DefinitionError as exCast:
                self.pos = pos
                try:
                    return self._parse_unary_expression()
                except DefinitionError as exUnary:
                    errs = []
                    errs.append((exCast, "If type cast expression"))
                    errs.append((exUnary, "If unary expression"))
                    raise self._make_multi_error(errs,
                                                 "Error in cast expression.") from exUnary
        else:
            return self._parse_unary_expression()

    def _parse_logical_or_expression(self) -> ASTExpression:
        # logical-or     = logical-and      ||
        # logical-and    = inclusive-or     &&
        # inclusive-or   = exclusive-or     |
        # exclusive-or   = and              ^
        # and            = equality         &
        # equality       = relational       ==, !=
        # relational     = shift            <, >, <=, >=
        # shift          = additive         <<, >>
        # additive       = multiplicative   +, -
        # multiplicative = pm               *, /, %
        # pm             = cast             .*, ->*
        def _parse_bin_op_expr(self, opId):
            if opId + 1 == len(_expression_bin_ops):
                def parser() -> ASTExpression:
                    return self._parse_cast_expression()
            else:
                def parser() -> ASTExpression:
                    return _parse_bin_op_expr(self, opId + 1)
            exprs = []
            ops = []
            exprs.append(parser())
            while True:
                self.skip_ws()
                pos = self.pos
                oneMore = False
                for op in _expression_bin_ops[opId]:
                    if op[0] in 'abcnox':
                        if not self.skip_word(op):
                            continue
                    else:
                        if not self.skip_string(op):
                            continue
                    if op == '&' and self.current_char == '&':
                        # don't split the && 'token'
                        self.pos -= 1
                        # and btw. && has lower precedence, so we are done
                        break
                    try:
                        expr = parser()
                        exprs.append(expr)
                        ops.append(op)
                        oneMore = True
                        break
                    except DefinitionError:
                        self.pos = pos
                if not oneMore:
                    break
            return ASTBinOpExpr(exprs, ops)
        return _parse_bin_op_expr(self, 0)

    def _parse_conditional_expression_tail(self, orExprHead: Any) -> ASTExpression | None:
        # -> "?" expression ":" assignment-expression
        return None

    def _parse_assignment_expression(self) -> ASTExpression:
        # -> conditional-expression
        #  | logical-or-expression assignment-operator initializer-clause
        # -> conditional-expression ->
        #     logical-or-expression
        #   | logical-or-expression "?" expression ":" assignment-expression
        #   | logical-or-expression assignment-operator initializer-clause
        exprs = []
        ops = []
        orExpr = self._parse_logical_or_expression()
        exprs.append(orExpr)
        # TODO: handle ternary with _parse_conditional_expression_tail
        while True:
            oneMore = False
            self.skip_ws()
            for op in _expression_assignment_ops:
                if op[0] in 'abcnox':
                    if not self.skip_word(op):
                        continue
                else:
                    if not self.skip_string(op):
                        continue
                expr = self._parse_logical_or_expression()
                exprs.append(expr)
                ops.append(op)
                oneMore = True
            if not oneMore:
                break
        return ASTAssignmentExpr(exprs, ops)

    def _parse_constant_expression(self) -> ASTExpression:
        # -> conditional-expression
        orExpr = self._parse_logical_or_expression()
        # TODO: use _parse_conditional_expression_tail
        return orExpr

    def _parse_expression(self) -> ASTExpression:
        # -> assignment-expression
        #  | expression "," assignment-expression
        # TODO: actually parse the second production
        return self._parse_assignment_expression()

    def _parse_expression_fallback(
            self, end: list[str],
            parser: Callable[[], ASTExpression],
            allow: bool = True) -> ASTExpression:
        # Stupidly "parse" an expression.
        # 'end' should be a list of characters which ends the expression.

        # first try to use the provided parser
        prevPos = self.pos
        try:
            return parser()
        except DefinitionError as e:
            # some places (e.g., template parameters) we really don't want to use fallback,
            # and for testing we may want to globally disable it
            if not allow or not self.allowFallbackExpressionParsing:
                raise
            self.warn("Parsing of expression failed. Using fallback parser."
                      " Error was:\n%s" % e)
            self.pos = prevPos
        # and then the fallback scanning
        assert end is not None
        self.skip_ws()
        startPos = self.pos
        if self.match(_string_re):
            value = self.matched_text
        else:
            # TODO: add handling of more bracket-like things, and quote handling
            brackets = {'(': ')', '{': '}', '[': ']'}
            symbols: list[str] = []
            while not self.eof:
                if (len(symbols) == 0 and self.current_char in end):
                    break
                if self.current_char in brackets:
                    symbols.append(brackets[self.current_char])
                elif len(symbols) > 0 and self.current_char == symbols[-1]:
                    symbols.pop()
                self.pos += 1
            if len(end) > 0 and self.eof:
                self.fail("Could not find end of expression starting at %d."
                          % startPos)
            value = self.definition[startPos:self.pos].strip()
        return ASTFallbackExpr(value.strip())

    def _parse_nested_name(self) -> ASTNestedName:
        names: list[Any] = []

        self.skip_ws()
        rooted = False
        if self.skip_string('.'):
            rooted = True
        while 1:
            self.skip_ws()
            if not self.match(identifier_re):
                self.fail("Expected identifier in nested name.")
            identifier = self.matched_text
            # make sure there isn't a keyword
            if identifier in _keywords:
                self.fail("Expected identifier in nested name, "
                          "got keyword: %s" % identifier)
            if self.matched_text in self.config.c_extra_keywords:
                msg = "Expected identifier, got user-defined keyword: %s." \
                      + " Remove it from c_extra_keywords to allow it as identifier.\n" \
                      + "Currently c_extra_keywords is %s."
                self.fail(msg % (self.matched_text,
                                 str(self.config.c_extra_keywords)))
            ident = ASTIdentifier(identifier)
            names.append(ident)

            self.skip_ws()
            if not self.skip_string('.'):
                break
        return ASTNestedName(names, rooted)

    def _parse_simple_type_specifier(self) -> str | None:
        if self.match(_simple_type_specifiers_re):
            return self.matched_text
        for t in ('bool', 'complex', 'imaginary'):
            if t in self.config.c_extra_keywords:
                if self.skip_word(t):
                    return t
        return None

    def _parse_simple_type_specifiers(self) -> ASTTrailingTypeSpecFundamental | None:
        names: list[str] = []

        self.skip_ws()
        while True:
            t = self._parse_simple_type_specifier()
            if t is None:
                break
            names.append(t)
            self.skip_ws()
        if len(names) == 0:
            return None
        return ASTTrailingTypeSpecFundamental(names)

    def _parse_trailing_type_spec(self) -> ASTTrailingTypeSpec:
        # fundamental types, https://en.cppreference.com/w/c/language/type
        # and extensions
        self.skip_ws()
        res = self._parse_simple_type_specifiers()
        if res is not None:
            return res

        # prefixed
        prefix = None
        self.skip_ws()
        for k in ('struct', 'enum', 'union'):
            if self.skip_word_and_ws(k):
                prefix = k
                break

        nestedName = self._parse_nested_name()
        return ASTTrailingTypeSpecName(prefix, nestedName)

    def _parse_parameters(self, paramMode: str) -> ASTParameters | None:
        self.skip_ws()
        if not self.skip_string('('):
            if paramMode == 'function':
                self.fail('Expecting "(" in parameters.')
            else:
                return None

        args = []
        self.skip_ws()
        if not self.skip_string(')'):
            while 1:
                self.skip_ws()
                if self.skip_string('...'):
                    args.append(ASTFunctionParameter(None, True))
                    self.skip_ws()
                    if not self.skip_string(')'):
                        self.fail('Expected ")" after "..." in parameters.')
                    break
                # note: it seems that function arguments can always be named,
                # even in function pointers and similar.
                arg = self._parse_type_with_init(outer=None, named='single')
                # TODO: parse default parameters # TODO: didn't we just do that?
                args.append(ASTFunctionParameter(arg))

                self.skip_ws()
                if self.skip_string(','):
                    continue
                if self.skip_string(')'):
                    break
                self.fail(f'Expecting "," or ")" in parameters, got "{self.current_char}".')

        attrs = self._parse_attribute_list()
        return ASTParameters(args, attrs)

    def _parse_decl_specs_simple(
        self, outer: str | None, typed: bool,
    ) -> ASTDeclSpecsSimple:
        """Just parse the simple ones."""
        storage = None
        threadLocal = None
        inline = None
        restrict = None
        volatile = None
        const = None
        attrs = []
        while 1:  # accept any permutation of a subset of some decl-specs
            self.skip_ws()
            if not storage:
                if outer == 'member':
                    if self.skip_word('auto'):
                        storage = 'auto'
                        continue
                    if self.skip_word('register'):
                        storage = 'register'
                        continue
                if outer in ('member', 'function'):
                    if self.skip_word('static'):
                        storage = 'static'
                        continue
                    if self.skip_word('extern'):
                        storage = 'extern'
                        continue
            if outer == 'member' and not threadLocal:
                if self.skip_word('thread_local'):
                    threadLocal = 'thread_local'
                    continue
                if self.skip_word('_Thread_local'):
                    threadLocal = '_Thread_local'
                    continue
            if outer == 'function' and not inline:
                inline = self.skip_word('inline')
                if inline:
                    continue

            if not restrict and typed:
                restrict = self.skip_word('restrict')
                if restrict:
                    continue
            if not volatile and typed:
                volatile = self.skip_word('volatile')
                if volatile:
                    continue
            if not const and typed:
                const = self.skip_word('const')
                if const:
                    continue
            attr = self._parse_attribute()
            if attr:
                attrs.append(attr)
                continue
            break
        return ASTDeclSpecsSimple(storage, threadLocal, inline,
                                  restrict, volatile, const, ASTAttributeList(attrs))

    def _parse_decl_specs(self, outer: str | None, typed: bool = True) -> ASTDeclSpecs:
        if outer:
            if outer not in ('type', 'member', 'function'):
                raise Exception('Internal error, unknown outer "%s".' % outer)
        leftSpecs = self._parse_decl_specs_simple(outer, typed)
        rightSpecs = None

        if typed:
            trailing = self._parse_trailing_type_spec()
            rightSpecs = self._parse_decl_specs_simple(outer, typed)
        else:
            trailing = None
        return ASTDeclSpecs(outer, leftSpecs, rightSpecs, trailing)

    def _parse_declarator_name_suffix(
            self, named: bool | str, paramMode: str, typed: bool,
    ) -> ASTDeclarator:
        assert named in (True, False, 'single')
        # now we should parse the name, and then suffixes
        if named == 'single':
            if self.match(identifier_re):
                if self.matched_text in _keywords:
                    self.fail("Expected identifier, "
                              "got keyword: %s" % self.matched_text)
                if self.matched_text in self.config.c_extra_keywords:
                    msg = "Expected identifier, got user-defined keyword: %s." \
                          + " Remove it from c_extra_keywords to allow it as identifier.\n" \
                          + "Currently c_extra_keywords is %s."
                    self.fail(msg % (self.matched_text,
                                     str(self.config.c_extra_keywords)))
                identifier = ASTIdentifier(self.matched_text)
                declId = ASTNestedName([identifier], rooted=False)
            else:
                declId = None
        elif named:
            declId = self._parse_nested_name()
        else:
            declId = None
        arrayOps = []
        while 1:
            self.skip_ws()
            if typed and self.skip_string('['):
                self.skip_ws()
                static = False
                const = False
                volatile = False
                restrict = False
                while True:
                    if not static:
                        if self.skip_word_and_ws('static'):
                            static = True
                            continue
                    if not const:
                        if self.skip_word_and_ws('const'):
                            const = True
                            continue
                    if not volatile:
                        if self.skip_word_and_ws('volatile'):
                            volatile = True
                            continue
                    if not restrict:
                        if self.skip_word_and_ws('restrict'):
                            restrict = True
                            continue
                    break
                vla = False if static else self.skip_string_and_ws('*')
                if vla:
                    if not self.skip_string(']'):
                        self.fail("Expected ']' in end of array operator.")
                    size = None
                else:
                    if self.skip_string(']'):
                        size = None
                    else:

                        def parser():
                            return self._parse_expression()
                        size = self._parse_expression_fallback([']'], parser)
                        self.skip_ws()
                        if not self.skip_string(']'):
                            self.fail("Expected ']' in end of array operator.")
                arrayOps.append(ASTArray(static, const, volatile, restrict, vla, size))
            else:
                break
        param = self._parse_parameters(paramMode)
        if param is None and len(arrayOps) == 0:
            # perhaps a bit-field
            if named and paramMode == 'type' and typed:
                self.skip_ws()
                if self.skip_string(':'):
                    size = self._parse_constant_expression()
                    return ASTDeclaratorNameBitField(declId=declId, size=size)
        return ASTDeclaratorNameParam(declId=declId, arrayOps=arrayOps,
                                      param=param)

    def _parse_declarator(self, named: bool | str, paramMode: str,
                          typed: bool = True) -> ASTDeclarator:
        # 'typed' here means 'parse return type stuff'
        if paramMode not in ('type', 'function'):
            raise Exception(
                "Internal error, unknown paramMode '%s'." % paramMode)
        prevErrors = []
        self.skip_ws()
        if typed and self.skip_string('*'):
            self.skip_ws()
            restrict = False
            volatile = False
            const = False
            attrs = []
            while 1:
                if not restrict:
                    restrict = self.skip_word_and_ws('restrict')
                    if restrict:
                        continue
                if not volatile:
                    volatile = self.skip_word_and_ws('volatile')
                    if volatile:
                        continue
                if not const:
                    const = self.skip_word_and_ws('const')
                    if const:
                        continue
                attr = self._parse_attribute()
                if attr is not None:
                    attrs.append(attr)
                    continue
                break
            next = self._parse_declarator(named, paramMode, typed)
            return ASTDeclaratorPtr(next=next,
                                    restrict=restrict, volatile=volatile, const=const,
                                    attrs=ASTAttributeList(attrs))
        if typed and self.current_char == '(':  # note: peeking, not skipping
            # maybe this is the beginning of params, try that first,
            # otherwise assume it's noptr->declarator > ( ptr-declarator )
            pos = self.pos
            try:
                # assume this is params
                res = self._parse_declarator_name_suffix(named, paramMode,
                                                         typed)
                return res
            except DefinitionError as exParamQual:
                msg = "If declarator-id with parameters"
                if paramMode == 'function':
                    msg += " (e.g., 'void f(int arg)')"
                prevErrors.append((exParamQual, msg))
                self.pos = pos
                try:
                    assert self.current_char == '('
                    self.skip_string('(')
                    # TODO: hmm, if there is a name, it must be in inner, right?
                    # TODO: hmm, if there must be parameters, they must b
                    # inside, right?
                    inner = self._parse_declarator(named, paramMode, typed)
                    if not self.skip_string(')'):
                        self.fail("Expected ')' in \"( ptr-declarator )\"")
                    next = self._parse_declarator(named=False,
                                                  paramMode="type",
                                                  typed=typed)
                    return ASTDeclaratorParen(inner=inner, next=next)
                except DefinitionError as exNoPtrParen:
                    self.pos = pos
                    msg = "If parenthesis in noptr-declarator"
                    if paramMode == 'function':
                        msg += " (e.g., 'void (*f(int arg))(double)')"
                    prevErrors.append((exNoPtrParen, msg))
                    header = "Error in declarator"
                    raise self._make_multi_error(prevErrors, header) from exNoPtrParen
        pos = self.pos
        try:
            return self._parse_declarator_name_suffix(named, paramMode, typed)
        except DefinitionError as e:
            self.pos = pos
            prevErrors.append((e, "If declarator-id"))
            header = "Error in declarator or parameters"
            raise self._make_multi_error(prevErrors, header) from e

    def _parse_initializer(self, outer: str | None = None, allowFallback: bool = True,
                           ) -> ASTInitializer | None:
        self.skip_ws()
        if outer == 'member' and False:  # NoQA: SIM223  # TODO
            bracedInit = self._parse_braced_init_list()
            if bracedInit is not None:
                return ASTInitializer(bracedInit, hasAssign=False)

        if not self.skip_string('='):
            return None

        bracedInit = self._parse_braced_init_list()
        if bracedInit is not None:
            return ASTInitializer(bracedInit)

        if outer == 'member':
            fallbackEnd: list[str] = []
        elif outer is None:  # function parameter
            fallbackEnd = [',', ')']
        else:
            self.fail("Internal error, initializer for outer '%s' not "
                      "implemented." % outer)

        def parser():
            return self._parse_assignment_expression()

        value = self._parse_expression_fallback(fallbackEnd, parser, allow=allowFallback)
        return ASTInitializer(value)

    def _parse_type(self, named: bool | str, outer: str | None = None) -> ASTType:
        """
        named=False|'single'|True: 'single' is e.g., for function objects which
        doesn't need to name the arguments, but otherwise is a single name
        """
        if outer:  # always named
            if outer not in ('type', 'member', 'function'):
                raise Exception('Internal error, unknown outer "%s".' % outer)
            assert named

        if outer == 'type':
            # We allow type objects to just be a name.
            prevErrors = []
            startPos = self.pos
            # first try without the type
            try:
                declSpecs = self._parse_decl_specs(outer=outer, typed=False)
                decl = self._parse_declarator(named=True, paramMode=outer,
                                              typed=False)
                self.assert_end(allowSemicolon=True)
            except DefinitionError as exUntyped:
                desc = "If just a name"
                prevErrors.append((exUntyped, desc))
                self.pos = startPos
                try:
                    declSpecs = self._parse_decl_specs(outer=outer)
                    decl = self._parse_declarator(named=True, paramMode=outer)
                except DefinitionError as exTyped:
                    self.pos = startPos
                    desc = "If typedef-like declaration"
                    prevErrors.append((exTyped, desc))
                    # Retain the else branch for easier debugging.
                    # TODO: it would be nice to save the previous stacktrace
                    #       and output it here.
                    if True:
                        header = "Type must be either just a name or a "
                        header += "typedef-like declaration."
                        raise self._make_multi_error(prevErrors, header) from exTyped
                    else:  # NoQA: RET506
                        # For testing purposes.
                        # do it again to get the proper traceback (how do you
                        # reliably save a traceback when an exception is
                        # constructed?)
                        self.pos = startPos
                        typed = True
                        declSpecs = self._parse_decl_specs(outer=outer, typed=typed)
                        decl = self._parse_declarator(named=True, paramMode=outer,
                                                      typed=typed)
        elif outer == 'function':
            declSpecs = self._parse_decl_specs(outer=outer)
            decl = self._parse_declarator(named=True, paramMode=outer)
        else:
            paramMode = 'type'
            if outer == 'member':  # i.e., member
                named = True
            declSpecs = self._parse_decl_specs(outer=outer)
            decl = self._parse_declarator(named=named, paramMode=paramMode)
        return ASTType(declSpecs, decl)

    def _parse_type_with_init(self, named: bool | str, outer: str | None) -> ASTTypeWithInit:
        if outer:
            assert outer in ('type', 'member', 'function')
        type = self._parse_type(outer=outer, named=named)
        init = self._parse_initializer(outer=outer)
        return ASTTypeWithInit(type, init)

    def _parse_macro(self) -> ASTMacro:
        self.skip_ws()
        ident = self._parse_nested_name()
        if ident is None:
            self.fail("Expected identifier in macro definition.")
        self.skip_ws()
        if not self.skip_string_and_ws('('):
            return ASTMacro(ident, None)
        if self.skip_string(')'):
            return ASTMacro(ident, [])
        args = []
        while 1:
            self.skip_ws()
            if self.skip_string('...'):
                args.append(ASTMacroParameter(None, True))
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail('Expected ")" after "..." in macro parameters.')
                break
            if not self.match(identifier_re):
                self.fail("Expected identifier in macro parameters.")
            nn = ASTNestedName([ASTIdentifier(self.matched_text)], rooted=False)
            # Allow named variadic args:
            # https://gcc.gnu.org/onlinedocs/cpp/Variadic-Macros.html
            self.skip_ws()
            if self.skip_string_and_ws('...'):
                args.append(ASTMacroParameter(nn, False, True))
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail('Expected ")" after "..." in macro parameters.')
                break
            args.append(ASTMacroParameter(nn))
            if self.skip_string_and_ws(','):
                continue
            if self.skip_string_and_ws(')'):
                break
            self.fail("Expected identifier, ')', or ',' in macro parameter list.")
        return ASTMacro(ident, args)

    def _parse_struct(self) -> ASTStruct:
        name = self._parse_nested_name()
        return ASTStruct(name)

    def _parse_union(self) -> ASTUnion:
        name = self._parse_nested_name()
        return ASTUnion(name)

    def _parse_enum(self) -> ASTEnum:
        name = self._parse_nested_name()
        return ASTEnum(name)

    def _parse_enumerator(self) -> ASTEnumerator:
        name = self._parse_nested_name()
        attrs = self._parse_attribute_list()
        self.skip_ws()
        init = None
        if self.skip_string('='):
            self.skip_ws()

            def parser() -> ASTExpression:
                return self._parse_constant_expression()

            initVal = self._parse_expression_fallback([], parser)
            init = ASTInitializer(initVal)
        return ASTEnumerator(name, init, attrs)

    def parse_declaration(self, objectType: str, directiveType: str) -> ASTDeclaration:
        if objectType not in ('function', 'member',
                              'macro', 'struct', 'union', 'enum', 'enumerator', 'type'):
            raise Exception('Internal error, unknown objectType "%s".' % objectType)
        if directiveType not in ('function', 'member', 'var',
                                 'macro', 'struct', 'union', 'enum', 'enumerator', 'type'):
            raise Exception('Internal error, unknown directiveType "%s".' % directiveType)

        declaration: DeclarationType = None
        if objectType == 'member':
            declaration = self._parse_type_with_init(named=True, outer='member')
        elif objectType == 'function':
            declaration = self._parse_type(named=True, outer='function')
        elif objectType == 'macro':
            declaration = self._parse_macro()
        elif objectType == 'struct':
            declaration = self._parse_struct()
        elif objectType == 'union':
            declaration = self._parse_union()
        elif objectType == 'enum':
            declaration = self._parse_enum()
        elif objectType == 'enumerator':
            declaration = self._parse_enumerator()
        elif objectType == 'type':
            declaration = self._parse_type(named=True, outer='type')
        else:
            raise AssertionError
        if objectType != 'macro':
            self.skip_ws()
            semicolon = self.skip_string(';')
        else:
            semicolon = False
        return ASTDeclaration(objectType, directiveType, declaration, semicolon)

    def parse_namespace_object(self) -> ASTNestedName:
        return self._parse_nested_name()

    def parse_xref_object(self) -> ASTNestedName:
        name = self._parse_nested_name()
        # if there are '()' left, just skip them
        self.skip_ws()
        self.skip_string('()')
        self.assert_end()
        return name

    def parse_expression(self) -> ASTExpression | ASTType:
        pos = self.pos
        res: ASTExpression | ASTType = None
        try:
            res = self._parse_expression()
            self.skip_ws()
            self.assert_end()
        except DefinitionError as exExpr:
            self.pos = pos
            try:
                res = self._parse_type(False)
                self.skip_ws()
                self.assert_end()
            except DefinitionError as exType:
                header = "Error when parsing (type) expression."
                errs = []
                errs.append((exExpr, "If expression"))
                errs.append((exType, "If type"))
                raise self._make_multi_error(errs, header) from exType
        return res


def _make_phony_error_name() -> ASTNestedName:
    return ASTNestedName([ASTIdentifier("PhonyNameDueToError")], rooted=False)


class CObject(ObjectDescription[ASTDeclaration]):
    """
    Description of a C language object.
    """

    option_spec: OptionSpec = {
        'no-index-entry': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindexentry': directives.flag,
        'nocontentsentry': directives.flag,
        'single-line-parameter-list': directives.flag,
    }

    def _add_enumerator_to_parent(self, ast: ASTDeclaration) -> None:
        assert ast.objectType == 'enumerator'
        # find the parent, if it exists && is an enum
        #                  then add the name to the parent scope
        symbol = ast.symbol
        assert symbol
        assert symbol.ident is not None
        parentSymbol = symbol.parent
        assert parentSymbol
        if parentSymbol.parent is None:
            # TODO: we could warn, but it is somewhat equivalent to
            # enumeratorss, without the enum
            return  # no parent
        parentDecl = parentSymbol.declaration
        if parentDecl is None:
            # the parent is not explicitly declared
            # TODO: we could warn, but?
            return
        if parentDecl.objectType != 'enum':
            # TODO: maybe issue a warning, enumerators in non-enums is weird,
            # but it is somewhat equivalent to enumeratorss, without the enum
            return
        if parentDecl.directiveType != 'enum':
            return

        targetSymbol = parentSymbol.parent
        s = targetSymbol.find_identifier(symbol.ident, matchSelf=False, recurseInAnon=True,
                                         searchInSiblings=False)
        if s is not None:
            # something is already declared with that name
            return
        declClone = symbol.declaration.clone()
        declClone.enumeratorScopedSymbol = symbol
        Symbol(parent=targetSymbol, ident=symbol.ident,
               declaration=declClone,
               docname=self.env.docname, line=self.get_source_info()[1])

    def add_target_and_index(self, ast: ASTDeclaration, sig: str,
                             signode: TextElement) -> None:
        ids = []
        for i in range(1, _max_id + 1):
            try:
                id = ast.get_id(version=i)
                ids.append(id)
            except NoOldIdError:
                assert i < _max_id
        # let's keep the newest first
        ids = list(reversed(ids))
        newestId = ids[0]
        assert newestId  # shouldn't be None

        name = ast.symbol.get_full_nested_name().get_display_string().lstrip('.')
        if newestId not in self.state.document.ids:
            # always add the newest id
            assert newestId
            signode['ids'].append(newestId)
            # only add compatibility ids when there are no conflicts
            for id in ids[1:]:
                if not id:  # is None when the element didn't exist in that version
                    continue
                if id not in self.state.document.ids:
                    signode['ids'].append(id)

            self.state.document.note_explicit_target(signode)

        if 'no-index-entry' not in self.options:
            indexText = self.get_index_text(name)
            self.indexnode['entries'].append(('single', indexText, newestId, '', None))

    @property
    def object_type(self) -> str:
        raise NotImplementedError

    @property
    def display_object_type(self) -> str:
        return self.object_type

    def get_index_text(self, name: str) -> str:
        return _('%s (C %s)') % (name, self.display_object_type)

    def parse_definition(self, parser: DefinitionParser) -> ASTDeclaration:
        return parser.parse_declaration(self.object_type, self.objtype)

    def describe_signature(self, signode: TextElement, ast: ASTDeclaration,
                           options: dict) -> None:
        ast.describe_signature(signode, 'lastIsName', self.env, options)

    def run(self) -> list[Node]:
        env = self.state.document.settings.env  # from ObjectDescription.run
        if 'c:parent_symbol' not in env.temp_data:
            root = env.domaindata['c']['root_symbol']
            env.temp_data['c:parent_symbol'] = root
            env.ref_context['c:parent_key'] = root.get_lookup_key()

        # When multiple declarations are made in the same directive
        # they need to know about each other to provide symbol lookup for function parameters.
        # We use last_symbol to store the latest added declaration in a directive.
        env.temp_data['c:last_symbol'] = None
        return super().run()

    def handle_signature(self, sig: str, signode: TextElement) -> ASTDeclaration:
        parentSymbol: Symbol = self.env.temp_data['c:parent_symbol']

        max_len = (self.env.config.c_maximum_signature_line_length
                   or self.env.config.maximum_signature_line_length
                   or 0)
        signode['multi_line_parameter_list'] = (
            'single-line-parameter-list' not in self.options
            and (len(sig) > max_len > 0)
        )

        parser = DefinitionParser(sig, location=signode, config=self.env.config)
        try:
            ast = self.parse_definition(parser)
            parser.assert_end()
        except DefinitionError as e:
            logger.warning(e, location=signode)
            # It is easier to assume some phony name than handling the error in
            # the possibly inner declarations.
            name = _make_phony_error_name()
            symbol = parentSymbol.add_name(name)
            self.env.temp_data['c:last_symbol'] = symbol
            raise ValueError from e

        try:
            symbol = parentSymbol.add_declaration(
                ast, docname=self.env.docname, line=self.get_source_info()[1])
            # append the new declaration to the sibling list
            assert symbol.siblingAbove is None
            assert symbol.siblingBelow is None
            symbol.siblingAbove = self.env.temp_data['c:last_symbol']
            if symbol.siblingAbove is not None:
                assert symbol.siblingAbove.siblingBelow is None
                symbol.siblingAbove.siblingBelow = symbol
            self.env.temp_data['c:last_symbol'] = symbol
        except _DuplicateSymbolError as e:
            # Assume we are actually in the old symbol,
            # instead of the newly created duplicate.
            self.env.temp_data['c:last_symbol'] = e.symbol
            msg = __("Duplicate C declaration, also defined at %s:%s.\n"
                     "Declaration is '.. c:%s:: %s'.")
            msg = msg % (e.symbol.docname, e.symbol.line, self.display_object_type, sig)
            logger.warning(msg, location=signode)

        if ast.objectType == 'enumerator':
            self._add_enumerator_to_parent(ast)

        # note: handle_signature may be called multiple time per directive,
        # if it has multiple signatures, so don't mess with the original options.
        options = dict(self.options)
        self.describe_signature(signode, ast, options)
        return ast

    def before_content(self) -> None:
        lastSymbol: Symbol = self.env.temp_data['c:last_symbol']
        assert lastSymbol
        self.oldParentSymbol = self.env.temp_data['c:parent_symbol']
        self.oldParentKey: LookupKey = self.env.ref_context['c:parent_key']
        self.env.temp_data['c:parent_symbol'] = lastSymbol
        self.env.ref_context['c:parent_key'] = lastSymbol.get_lookup_key()

    def after_content(self) -> None:
        self.env.temp_data['c:parent_symbol'] = self.oldParentSymbol
        self.env.ref_context['c:parent_key'] = self.oldParentKey


class CMemberObject(CObject):
    object_type = 'member'

    @property
    def display_object_type(self) -> str:
        # the distinction between var and member is only cosmetic
        assert self.objtype in ('member', 'var')
        return self.objtype


_function_doc_field_types = [
    TypedField('parameter', label=_('Parameters'),
               names=('param', 'parameter', 'arg', 'argument'),
               typerolename='expr', typenames=('type',)),
    GroupedField('retval', label=_('Return values'),
                 names=('retvals', 'retval'),
                 can_collapse=True),
    Field('returnvalue', label=_('Returns'), has_arg=False,
          names=('returns', 'return')),
    Field('returntype', label=_('Return type'), has_arg=False,
          names=('rtype',)),
]


class CFunctionObject(CObject):
    object_type = 'function'

    doc_field_types = _function_doc_field_types.copy()


class CMacroObject(CObject):
    object_type = 'macro'

    doc_field_types = _function_doc_field_types.copy()


class CStructObject(CObject):
    object_type = 'struct'


class CUnionObject(CObject):
    object_type = 'union'


class CEnumObject(CObject):
    object_type = 'enum'


class CEnumeratorObject(CObject):
    object_type = 'enumerator'


class CTypeObject(CObject):
    object_type = 'type'


class CNamespaceObject(SphinxDirective):
    """
    This directive is just to tell Sphinx that we're documenting stuff in
    namespace foo.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        rootSymbol = self.env.domaindata['c']['root_symbol']
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            symbol = rootSymbol
            stack: list[Symbol] = []
        else:
            parser = DefinitionParser(self.arguments[0],
                                      location=self.get_location(),
                                      config=self.env.config)
            try:
                name = parser.parse_namespace_object()
                parser.assert_end()
            except DefinitionError as e:
                logger.warning(e, location=self.get_location())
                name = _make_phony_error_name()
            symbol = rootSymbol.add_name(name)
            stack = [symbol]
        self.env.temp_data['c:parent_symbol'] = symbol
        self.env.temp_data['c:namespace_stack'] = stack
        self.env.ref_context['c:parent_key'] = symbol.get_lookup_key()
        return []


class CNamespacePushObject(SphinxDirective):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            return []
        parser = DefinitionParser(self.arguments[0],
                                  location=self.get_location(),
                                  config=self.env.config)
        try:
            name = parser.parse_namespace_object()
            parser.assert_end()
        except DefinitionError as e:
            logger.warning(e, location=self.get_location())
            name = _make_phony_error_name()
        oldParent = self.env.temp_data.get('c:parent_symbol', None)
        if not oldParent:
            oldParent = self.env.domaindata['c']['root_symbol']
        symbol = oldParent.add_name(name)
        stack = self.env.temp_data.get('c:namespace_stack', [])
        stack.append(symbol)
        self.env.temp_data['c:parent_symbol'] = symbol
        self.env.temp_data['c:namespace_stack'] = stack
        self.env.ref_context['c:parent_key'] = symbol.get_lookup_key()
        return []


class CNamespacePopObject(SphinxDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        stack = self.env.temp_data.get('c:namespace_stack', None)
        if not stack or len(stack) == 0:
            logger.warning("C namespace pop on empty stack. Defaulting to global scope.",
                           location=self.get_location())
            stack = []
        else:
            stack.pop()
        if len(stack) > 0:
            symbol = stack[-1]
        else:
            symbol = self.env.domaindata['c']['root_symbol']
        self.env.temp_data['c:parent_symbol'] = symbol
        self.env.temp_data['c:namespace_stack'] = stack
        self.env.ref_context['cp:parent_key'] = symbol.get_lookup_key()
        return []


class AliasNode(nodes.Element):
    def __init__(
        self,
        sig: str,
        aliasOptions: dict,
        document: Any,
        env: BuildEnvironment | None = None,
        parentKey: LookupKey | None = None,
    ) -> None:
        super().__init__()
        self.sig = sig
        self.aliasOptions = aliasOptions
        self.document = document
        if env is not None:
            if 'c:parent_symbol' not in env.temp_data:
                root = env.domaindata['c']['root_symbol']
                env.temp_data['c:parent_symbol'] = root
                env.ref_context['c:parent_key'] = root.get_lookup_key()
            self.parentKey = env.ref_context['c:parent_key']
        else:
            assert parentKey is not None
            self.parentKey = parentKey

    def copy(self) -> AliasNode:
        return self.__class__(self.sig, self.aliasOptions, self.document,
                              env=None, parentKey=self.parentKey)


class AliasTransform(SphinxTransform):
    default_priority = ReferencesResolver.default_priority - 1

    def _render_symbol(self, s: Symbol, maxdepth: int, skipThis: bool,
                       aliasOptions: dict, renderOptions: dict,
                       document: Any) -> list[Node]:
        if maxdepth == 0:
            recurse = True
        elif maxdepth == 1:
            recurse = False
        else:
            maxdepth -= 1
            recurse = True

        nodes: list[Node] = []
        if not skipThis:
            signode = addnodes.desc_signature('', '')
            nodes.append(signode)
            s.declaration.describe_signature(signode, 'markName', self.env, renderOptions)

        if recurse:
            if skipThis:
                childContainer: list[Node] | addnodes.desc = nodes
            else:
                content = addnodes.desc_content()
                desc = addnodes.desc()
                content.append(desc)
                desc.document = document
                desc['domain'] = 'c'
                # 'desctype' is a backwards compatible attribute
                desc['objtype'] = desc['desctype'] = 'alias'
                desc['no-index'] = True
                childContainer = desc

            for sChild in s.children:
                if sChild.declaration is None:
                    continue
                childNodes = self._render_symbol(
                    sChild, maxdepth=maxdepth, skipThis=False,
                    aliasOptions=aliasOptions, renderOptions=renderOptions,
                    document=document)
                childContainer.extend(childNodes)

            if not skipThis and len(desc.children) != 0:
                nodes.append(content)
        return nodes

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(AliasNode):
            sig = node.sig
            parentKey = node.parentKey
            try:
                parser = DefinitionParser(sig, location=node,
                                          config=self.env.config)
                name = parser.parse_xref_object()
            except DefinitionError as e:
                logger.warning(e, location=node)
                name = None

            if name is None:
                # could not be parsed, so stop here
                signode = addnodes.desc_signature(sig, '')
                signode.clear()
                signode += addnodes.desc_name(sig, sig)
                node.replace_self(signode)
                continue

            rootSymbol: Symbol = self.env.domains['c'].data['root_symbol']
            parentSymbol: Symbol = rootSymbol.direct_lookup(parentKey)
            if not parentSymbol:
                logger.debug("Target: %s", sig)
                logger.debug("ParentKey: %s", parentKey)
                logger.debug(rootSymbol.dump(1))
            assert parentSymbol  # should be there

            s = parentSymbol.find_declaration(
                name, 'any',
                matchSelf=True, recurseInAnon=True)
            if s is None:
                signode = addnodes.desc_signature(sig, '')
                node.append(signode)
                signode.clear()
                signode += addnodes.desc_name(sig, sig)

                logger.warning("Could not find C declaration for alias '%s'." % name,
                               location=node)
                node.replace_self(signode)
                continue
            # Declarations like .. var:: int Missing::var
            # may introduce symbols without declarations.
            # But if we skip the root then it is ok to start recursion from it.
            if not node.aliasOptions['noroot'] and s.declaration is None:
                signode = addnodes.desc_signature(sig, '')
                node.append(signode)
                signode.clear()
                signode += addnodes.desc_name(sig, sig)

                logger.warning(
                    "Can not render C declaration for alias '%s'. No such declaration." % name,
                    location=node)
                node.replace_self(signode)
                continue

            nodes = self._render_symbol(s, maxdepth=node.aliasOptions['maxdepth'],
                                        skipThis=node.aliasOptions['noroot'],
                                        aliasOptions=node.aliasOptions,
                                        renderOptions={}, document=node.document)
            node.replace_self(nodes)


class CAliasObject(ObjectDescription):
    option_spec: OptionSpec = {
        'maxdepth': directives.nonnegative_int,
        'noroot': directives.flag,
    }

    def run(self) -> list[Node]:
        """
        On purpose this doesn't call the ObjectDescription version, but is based on it.
        Each alias signature may expand into multiple real signatures if 'noroot'.
        The code is therefore based on the ObjectDescription version.
        """
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name

        node = addnodes.desc()
        node.document = self.state.document
        node['domain'] = self.domain
        # 'desctype' is a backwards compatible attribute
        node['objtype'] = node['desctype'] = self.objtype
        node['no-index'] = True

        self.names: list[str] = []
        aliasOptions = {
            'maxdepth': self.options.get('maxdepth', 1),
            'noroot': 'noroot' in self.options,
        }
        if aliasOptions['noroot'] and aliasOptions['maxdepth'] == 1:
            logger.warning("Error in C alias declaration."
                           " Requested 'noroot' but 'maxdepth' 1."
                           " When skipping the root declaration,"
                           " need 'maxdepth' 0 for infinite or at least 2.",
                           location=self.get_location())
        for sig in self.get_signatures():
            node.append(AliasNode(sig, aliasOptions, self.state.document, env=self.env))
        return [node]


class CXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element,
                     has_explicit_title: bool, title: str, target: str) -> tuple[str, str]:
        refnode.attributes.update(env.ref_context)

        if not has_explicit_title:
            # major hax: replace anon names via simple string manipulation.
            # Can this actually fail?
            title = anon_identifier_re.sub("[anonymous]", str(title))

        if not has_explicit_title:
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        return title, target


class CExprRole(SphinxRole):
    def __init__(self, asCode: bool) -> None:
        super().__init__()
        if asCode:
            # render the expression as inline code
            self.class_type = 'c-expr'
        else:
            # render the expression as inline text
            self.class_type = 'c-texpr'

    def run(self) -> tuple[list[Node], list[system_message]]:
        text = self.text.replace('\n', ' ')
        parser = DefinitionParser(text, location=self.get_location(),
                                  config=self.env.config)
        # attempt to mimic XRefRole classes, except that...
        try:
            ast = parser.parse_expression()
        except DefinitionError as ex:
            logger.warning('Unparseable C expression: %r\n%s', text, ex,
                           location=self.get_location())
            # see below
            return [addnodes.desc_inline('c', text, text, classes=[self.class_type])], []
        parentSymbol = self.env.temp_data.get('c:parent_symbol', None)
        if parentSymbol is None:
            parentSymbol = self.env.domaindata['c']['root_symbol']
        # ...most if not all of these classes should really apply to the individual references,
        # not the container node
        signode = addnodes.desc_inline('c', classes=[self.class_type])
        ast.describe_signature(signode, 'markType', self.env, parentSymbol)
        return [signode], []


class CDomain(Domain):
    """C language domain."""
    name = 'c'
    label = 'C'
    object_types = {
        # 'identifier' is the one used for xrefs generated in signatures, not in roles
        'member': ObjType(_('member'), 'var', 'member', 'data', 'identifier'),
        'var': ObjType(_('variable'),  'var', 'member', 'data', 'identifier'),
        'function': ObjType(_('function'),     'func',          'identifier', 'type'),
        'macro': ObjType(_('macro'),           'macro',         'identifier'),
        'struct': ObjType(_('struct'),         'struct',        'identifier', 'type'),
        'union': ObjType(_('union'),           'union',         'identifier', 'type'),
        'enum': ObjType(_('enum'),             'enum',          'identifier', 'type'),
        'enumerator': ObjType(_('enumerator'), 'enumerator',    'identifier'),
        'type': ObjType(_('type'),                              'identifier', 'type'),
        # generated object types
        'functionParam': ObjType(_('function parameter'),       'identifier', 'var', 'member', 'data'),  # noqa: E501
    }

    directives = {
        'member': CMemberObject,
        'var': CMemberObject,
        'function': CFunctionObject,
        'macro': CMacroObject,
        'struct': CStructObject,
        'union': CUnionObject,
        'enum': CEnumObject,
        'enumerator': CEnumeratorObject,
        'type': CTypeObject,
        # scope control
        'namespace': CNamespaceObject,
        'namespace-push': CNamespacePushObject,
        'namespace-pop': CNamespacePopObject,
        # other
        'alias': CAliasObject,
    }
    roles = {
        'member': CXRefRole(),
        'data': CXRefRole(),
        'var': CXRefRole(),
        'func': CXRefRole(fix_parens=True),
        'macro': CXRefRole(),
        'struct': CXRefRole(),
        'union': CXRefRole(),
        'enum': CXRefRole(),
        'enumerator': CXRefRole(),
        'type': CXRefRole(),
        'expr': CExprRole(asCode=True),
        'texpr': CExprRole(asCode=False),
    }
    initial_data: dict[str, Symbol | dict[str, tuple[str, str, str]]] = {
        'root_symbol': Symbol(None, None, None, None, None),
        'objects': {},  # fullname -> docname, node_id, objtype
    }

    def clear_doc(self, docname: str) -> None:
        if Symbol.debug_show_tree:
            logger.debug("clear_doc: %s", docname)
            logger.debug("\tbefore:")
            logger.debug(self.data['root_symbol'].dump(1))
            logger.debug("\tbefore end")

        rootSymbol = self.data['root_symbol']
        rootSymbol.clear_doc(docname)

        if Symbol.debug_show_tree:
            logger.debug("\tafter:")
            logger.debug(self.data['root_symbol'].dump(1))
            logger.debug("\tafter end")
            logger.debug("clear_doc end: %s", docname)

    def process_doc(self, env: BuildEnvironment, docname: str,
                    document: nodes.document) -> None:
        if Symbol.debug_show_tree:
            logger.debug("process_doc: %s", docname)
            logger.debug(self.data['root_symbol'].dump(0))
            logger.debug("process_doc end: %s", docname)

    def process_field_xref(self, pnode: pending_xref) -> None:
        pnode.attributes.update(self.env.ref_context)

    def merge_domaindata(self, docnames: list[str], otherdata: dict) -> None:
        if Symbol.debug_show_tree:
            logger.debug("merge_domaindata:")
            logger.debug("\tself:")
            logger.debug(self.data['root_symbol'].dump(1))
            logger.debug("\tself end")
            logger.debug("\tother:")
            logger.debug(otherdata['root_symbol'].dump(1))
            logger.debug("\tother end")
            logger.debug("merge_domaindata end")

        self.data['root_symbol'].merge_with(otherdata['root_symbol'],
                                            docnames, self.env)
        ourObjects = self.data['objects']
        for fullname, (fn, id_, objtype) in otherdata['objects'].items():
            if fn in docnames:
                if fullname not in ourObjects:
                    ourObjects[fullname] = (fn, id_, objtype)
                # no need to warn on duplicates, the symbol merge already does that

    def _resolve_xref_inner(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                            typ: str, target: str, node: pending_xref,
                            contnode: Element) -> tuple[Element | None, str | None]:
        parser = DefinitionParser(target, location=node, config=env.config)
        try:
            name = parser.parse_xref_object()
        except DefinitionError as e:
            logger.warning('Unparseable C cross-reference: %r\n%s', target, e,
                           location=node)
            return None, None
        parentKey: LookupKey = node.get("c:parent_key", None)
        rootSymbol = self.data['root_symbol']
        if parentKey:
            parentSymbol: Symbol = rootSymbol.direct_lookup(parentKey)
            if not parentSymbol:
                logger.debug("Target: %s", target)
                logger.debug("ParentKey: %s", parentKey)
                logger.debug(rootSymbol.dump(1))
            assert parentSymbol  # should be there
        else:
            parentSymbol = rootSymbol
        s = parentSymbol.find_declaration(name, typ,
                                          matchSelf=True, recurseInAnon=True)
        if s is None or s.declaration is None:
            return None, None

        # TODO: check role type vs. object type

        declaration = s.declaration
        displayName = name.get_display_string()
        docname = s.docname
        assert docname

        return make_refnode(builder, fromdocname, docname,
                            declaration.get_newest_id(), contnode, displayName,
                            ), declaration.objectType

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref,
                     contnode: Element) -> Element | None:
        return self._resolve_xref_inner(env, fromdocname, builder, typ,
                                        target, node, contnode)[0]

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        with logging.suppress_logging():
            retnode, objtype = self._resolve_xref_inner(env, fromdocname, builder,
                                                        'any', target, node, contnode)
        if retnode:
            return [('c:' + self.role_for_objtype(objtype), retnode)]
        return []

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        rootSymbol = self.data['root_symbol']
        for symbol in rootSymbol.get_all_symbols():
            if symbol.declaration is None:
                continue
            assert symbol.docname
            fullNestedName = symbol.get_full_nested_name()
            name = str(fullNestedName).lstrip('.')
            dispname = fullNestedName.get_display_string().lstrip('.')
            objectType = symbol.declaration.objectType
            docname = symbol.docname
            newestId = symbol.declaration.get_newest_id()
            yield (name, dispname, objectType, docname, newestId, 1)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(CDomain)
    app.add_config_value("c_id_attributes", [], 'env')
    app.add_config_value("c_paren_attributes", [], 'env')
    app.add_config_value("c_extra_keywords", _macroKeywords, 'env')
    app.add_config_value("c_maximum_signature_line_length", None, 'env', types={int, None})
    app.add_post_transform(AliasTransform)

    return {
        'version': 'builtin',
        'env_version': 3,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
