# -*- coding: utf-8 -*-
"""
    sphinx.domains.cpp
    ~~~~~~~~~~~~~~~~~~

    The C++ language domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from copy import deepcopy

from docutils import nodes, utils
from docutils.parsers.rst import directives
from six import iteritems, text_type

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.environment import NoUri
from sphinx.locale import _, __
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode
from sphinx.util.pycompat import UnicodeMixin


if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Match, Pattern, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)

"""
    Important note on ids
    ----------------------------------------------------------------------------

    Multiple id generation schemes are used due to backwards compatibility.
    - v1: 1.2.3 <= version < 1.3
          The style used before the rewrite.
          It is not the actual old code, but a replication of the behaviour.
    - v2: 1.3 <= version < now
          Standardised mangling scheme from
          https://itanium-cxx-abi.github.io/cxx-abi/abi.html#mangling
          though not completely implemented.
    All versions are generated and attached to elements. The newest is used for
    the index. All of the versions should work as permalinks.


    Signature Nodes and Tagnames
    ----------------------------------------------------------------------------

    Each signature is in a desc_signature node, where all children are
    desc_signature_line nodes. Each of these lines will have the attribute
    'sphinx_cpp_tagname' set to one of the following (prioritized):
    - 'declarator', if the line contains the name of the declared object.
    - 'templateParams', if the line starts a template parameter list,
    - 'templateParams', if the line has template parameters
      Note: such lines might get a new tag in the future.
    - 'templateIntroduction, if the line is on the form 'conceptName{...}'
    No other desc_signature nodes should exist (so far).


    Grammar
    ----------------------------------------------------------------------------

    See http://www.nongnu.org/hcb/ for the grammar,
    and https://github.com/cplusplus/draft/blob/master/source/grammar.tex,
    and https://github.com/cplusplus/concepts-ts
    for the newest grammar.

    common grammar things:
        template-declaration ->
            "template" "<" template-parameter-list ">" declaration
        template-parameter-list ->
              template-parameter
            | template-parameter-list "," template-parameter
        template-parameter ->
              type-parameter
            | parameter-declaration # i.e., same as a function argument

        type-parameter ->
              "class"    "..."[opt] identifier[opt]
            | "class"               identifier[opt] "=" type-id
            | "typename" "..."[opt] identifier[opt]
            | "typename"            identifier[opt] "=" type-id
            | "template" "<" template-parameter-list ">"
                "class"  "..."[opt] identifier[opt]
            | "template" "<" template-parameter-list ">"
                "class"             identifier[opt] "=" id-expression
            # also, from C++17 we can have "typename" in template templates
        templateDeclPrefix ->
            "template" "<" template-parameter-list ">"

        simple-declaration ->
            attribute-specifier-seq[opt] decl-specifier-seq[opt]
                init-declarator-list[opt] ;
        # Drop the semi-colon. For now: drop the attributes (TODO).
        # Use at most 1 init-declarator.
        -> decl-specifier-seq init-declarator
        -> decl-specifier-seq declarator initializer

        decl-specifier ->
              storage-class-specifier ->
                 (  "static" (only for member_object and function_object)
                  | "extern" (only for member_object and function_object)
                  | "register"
                 )
                 thread_local[opt] (only for member_object)
                                   (it can also appear before the others)

            | type-specifier -> trailing-type-specifier
            | function-specifier -> "inline" | "virtual" | "explicit" (only
              for function_object)
            | "friend" (only for function_object)
            | "constexpr" (only for member_object and function_object)
        trailing-type-specifier ->
              simple-type-specifier
            | elaborated-type-specifier
            | typename-specifier
            | cv-qualifier -> "const" | "volatile"
        stricter grammar for decl-specifier-seq (with everything, each object
        uses a subset):
            visibility storage-class-specifier function-specifier "friend"
            "constexpr" "volatile" "const" trailing-type-specifier
            # where trailing-type-specifier can no be cv-qualifier
        # Inside e.g., template paramters a strict subset is used
        # (see type-specifier-seq)
        trailing-type-specifier ->
              simple-type-specifier ->
                ::[opt] nested-name-specifier[opt] type-name
              | ::[opt] nested-name-specifier "template" simple-template-id
              | "char" | "bool" | ect.
              | decltype-specifier
            | elaborated-type-specifier ->
                class-key attribute-specifier-seq[opt] ::[opt]
                nested-name-specifier[opt] identifier
              | class-key ::[opt] nested-name-specifier[opt] template[opt]
                simple-template-id
              | "enum" ::[opt] nested-name-specifier[opt] identifier
            | typename-specifier ->
                "typename" ::[opt] nested-name-specifier identifier
              | "typename" ::[opt] nested-name-specifier template[opt]
                simple-template-id
        class-key -> "class" | "struct" | "union"
        type-name ->* identifier | simple-template-id
        # ignoring attributes and decltype, and then some left-factoring
        trailing-type-specifier ->
            rest-of-trailing
            ("class" | "struct" | "union" | "typename") rest-of-trailing
            build-in -> "char" | "bool" | ect.
            decltype-specifier
        rest-of-trailing -> (with some simplification)
            "::"[opt] list-of-elements-separated-by-::
        element ->
            "template"[opt] identifier ("<" template-argument-list ">")[opt]
        template-argument-list ->
              template-argument "..."[opt]
            | template-argument-list "," template-argument "..."[opt]
        template-argument ->
              constant-expression
            | type-specifier-seq abstract-declarator
            | id-expression


        declarator ->
              ptr-declarator
            | noptr-declarator parameters-and-qualifiers trailing-return-type
              (TODO: for now we don't support trailing-eturn-type)
        ptr-declarator ->
              noptr-declarator
            | ptr-operator ptr-declarator
        noptr-declarator ->
              declarator-id attribute-specifier-seq[opt] ->
                    "..."[opt] id-expression
                  | rest-of-trailing
            | noptr-declarator parameters-and-qualifiers
            | noptr-declarator "[" constant-expression[opt] "]"
              attribute-specifier-seq[opt]
            | "(" ptr-declarator ")"
        ptr-operator ->
              "*"  attribute-specifier-seq[opt] cv-qualifier-seq[opt]
            | "&   attribute-specifier-seq[opt]
            | "&&" attribute-specifier-seq[opt]
            | "::"[opt] nested-name-specifier "*" attribute-specifier-seq[opt]
                cv-qualifier-seq[opt]
        # function_object must use a parameters-and-qualifiers, the others may
        # use it (e.g., function poitners)
        parameters-and-qualifiers ->
            "(" parameter-clause ")" attribute-specifier-seq[opt]
            cv-qualifier-seq[opt] ref-qualifier[opt]
            exception-specification[opt]
        ref-qualifier -> "&" | "&&"
        exception-specification ->
            "noexcept" ("(" constant-expression ")")[opt]
            "throw" ("(" type-id-list ")")[opt]
        # TODO: we don't implement attributes
        # member functions can have initializers, but we fold them into here
        memberFunctionInit -> "=" "0"
        # (note: only "0" is allowed as the value, according to the standard,
        # right?)

        enum-head ->
            enum-key attribute-specifier-seq[opt] nested-name-specifier[opt]
                identifier enum-base[opt]
        enum-key -> "enum" | "enum struct" | "enum class"
        enum-base ->
            ":" type
        enumerator-definition ->
              identifier
            | identifier "=" constant-expression

    We additionally add the possibility for specifying the visibility as the
    first thing.

    concept_object:
        goal:
            just a declaration of the name (for now)

        grammar: only a single template parameter list, and the nested name
            may not have any template argument lists

            "template" "<" template-parameter-list ">"
            nested-name-specifier

    type_object:
        goal:
            either a single type (e.g., "MyClass:Something_T" or a typedef-like
            thing (e.g. "Something Something_T" or "int I_arr[]"
        grammar, single type: based on a type in a function parameter, but
        without a name:
               parameter-declaration
            -> attribute-specifier-seq[opt] decl-specifier-seq
               abstract-declarator[opt]
            # Drop the attributes
            -> decl-specifier-seq abstract-declarator[opt]
        grammar, typedef-like: no initilizer
            decl-specifier-seq declarator
        Can start with a templateDeclPrefix.

    member_object:
        goal: as a type_object which must have a declarator, and optionally
        with a initializer
        grammar:
            decl-specifier-seq declarator initializer
        Can start with a templateDeclPrefix.

    function_object:
        goal: a function declaration, TODO: what about templates? for now: skip
        grammar: no initializer
           decl-specifier-seq declarator
        Can start with a templateDeclPrefix.

    class_object:
        goal: a class declaration, but with specification of a base class
        grammar:
              nested-name "final"[opt] (":" base-specifier-list)[opt]
            base-specifier-list ->
              base-specifier "..."[opt]
            | base-specifier-list, base-specifier "..."[opt]
            base-specifier ->
              base-type-specifier
            | "virtual" access-spe"cifier[opt]    base-type-specifier
            | access-specifier[opt] "virtual"[opt] base-type-specifier
        Can start with a templateDeclPrefix.

    enum_object:
        goal: an unscoped enum or a scoped enum, optionally with the underlying
              type specified
        grammar:
            ("class" | "struct")[opt] visibility[opt] nested-name (":" type)[opt]
    enumerator_object:
        goal: an element in a scoped or unscoped enum. The name should be
              injected according to the scopedness.
        grammar:
            nested-name ("=" constant-expression)

    namespace_object:
        goal: a directive to put all following declarations in a specific scope
        grammar:
            nested-name
"""

_integer_literal_re = re.compile(r'[1-9][0-9]*')
_octal_literal_re = re.compile(r'0[0-7]*')
_hex_literal_re = re.compile(r'0[xX][0-7a-fA-F][0-7a-fA-F]*')
_binary_literal_re = re.compile(r'0[bB][01][01]*')
_integer_suffix_re = re.compile(r'')
_float_literal_re = re.compile(r'''(?x)
    [+-]?(
    # decimal
      ([0-9]+[eE][+-]?[0-9]+)
    | ([0-9]*\.[0-9]+([eE][+-]?[0-9]+)?)
    | ([0-9]+\.([eE][+-]?[0-9]+)?)
    # hex
    | (0[xX][0-9a-fA-F]+[pP][+-]?[0-9a-fA-F]+)
    | (0[xX][0-9a-fA-F]*\.[0-9a-fA-F]+([pP][+-]?[0-9a-fA-F]+)?)
    | (0[xX][0-9a-fA-F]+\.([pP][+-]?[0-9a-fA-F]+)?)
    )
''')
_char_literal_re = re.compile(r'''(?x)
    ((?:u8)|u|U|L)?
    '(
      (?:[^\\'])
    | (\\(
        (?:['"?\\abfnrtv])
      | (?:[0-7]{1,3})
      | (?:x[0-9a-fA-F]{2})
      | (?:u[0-9a-fA-F]{4})
      | (?:U[0-9a-fA-F]{8})
      ))
    )'
''')

_anon_identifier_re = re.compile(r'(@[a-zA-Z0-9_])[a-zA-Z0-9_]*\b')
_identifier_re = re.compile(r'''(?x)
    (   # This 'extends' _anon_identifier_re with the ordinary identifiers,
        # make sure they are in sync.
        (~?\b[a-zA-Z_])  # ordinary identifiers
    |   (@[a-zA-Z0-9_])  # our extension for names of anonymous entities
    )
    [a-zA-Z0-9_]*\b
''')
_whitespace_re = re.compile(r'(?u)\s+')
_string_re = re.compile(r"[LuU8]?('([^'\\]*(?:\\.[^'\\]*)*)'"
                        r'|"([^"\\]*(?:\\.[^"\\]*)*)")', re.S)
_visibility_re = re.compile(r'\b(public|private|protected)\b')
_operator_re = re.compile(r'''(?x)
        \[\s*\]
    |   \(\s*\)
    |   \+\+ | --
    |   ->\*? | \,
    |   (<<|>>)=? | && | \|\|
    |   [!<>=/*%+|&^~-]=?
''')
_fold_operator_re = re.compile(r'''(?x)
        ->\*    |    \.\*    |    \,
    |   (<<|>>)=?    |    &&    |    \|\|
    |   !=
    |   [<>=/*%+|&^~-]=?
''')
# see http://en.cppreference.com/w/cpp/keyword
_keywords = [
    'alignas', 'alignof', 'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor',
    'bool', 'break', 'case', 'catch', 'char', 'char16_t', 'char32_t', 'class',
    'compl', 'concept', 'const', 'constexpr', 'const_cast', 'continue',
    'decltype', 'default', 'delete', 'do', 'double', 'dynamic_cast', 'else',
    'enum', 'explicit', 'export', 'extern', 'false', 'float', 'for', 'friend',
    'goto', 'if', 'inline', 'int', 'long', 'mutable', 'namespace', 'new',
    'noexcept', 'not', 'not_eq', 'nullptr', 'operator', 'or', 'or_eq',
    'private', 'protected', 'public', 'register', 'reinterpret_cast',
    'requires', 'return', 'short', 'signed', 'sizeof', 'static',
    'static_assert', 'static_cast', 'struct', 'switch', 'template', 'this',
    'thread_local', 'throw', 'true', 'try', 'typedef', 'typeid', 'typename',
    'union', 'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t',
    'while', 'xor', 'xor_eq'
]

_max_id = 4
_id_prefix = [None, '', '_CPPv2', '_CPPv3', '_CPPv4']

# ------------------------------------------------------------------------------
# Id v1 constants
# ------------------------------------------------------------------------------

_id_fundamental_v1 = {
    'char': 'c',
    'signed char': 'c',
    'unsigned char': 'C',
    'int': 'i',
    'signed int': 'i',
    'unsigned int': 'U',
    'long': 'l',
    'signed long': 'l',
    'unsigned long': 'L',
    'bool': 'b'
}  # type: Dict[unicode, unicode]
_id_shorthands_v1 = {
    'std::string': 'ss',
    'std::ostream': 'os',
    'std::istream': 'is',
    'std::iostream': 'ios',
    'std::vector': 'v',
    'std::map': 'm'
}  # type: Dict[unicode, unicode]
_id_operator_v1 = {
    'new': 'new-operator',
    'new[]': 'new-array-operator',
    'delete': 'delete-operator',
    'delete[]': 'delete-array-operator',
    # the arguments will make the difference between unary and binary
    # '+(unary)' : 'ps',
    # '-(unary)' : 'ng',
    # '&(unary)' : 'ad',
    # '*(unary)' : 'de',
    '~': 'inv-operator',
    '+': 'add-operator',
    '-': 'sub-operator',
    '*': 'mul-operator',
    '/': 'div-operator',
    '%': 'mod-operator',
    '&': 'and-operator',
    '|': 'or-operator',
    '^': 'xor-operator',
    '=': 'assign-operator',
    '+=': 'add-assign-operator',
    '-=': 'sub-assign-operator',
    '*=': 'mul-assign-operator',
    '/=': 'div-assign-operator',
    '%=': 'mod-assign-operator',
    '&=': 'and-assign-operator',
    '|=': 'or-assign-operator',
    '^=': 'xor-assign-operator',
    '<<': 'lshift-operator',
    '>>': 'rshift-operator',
    '<<=': 'lshift-assign-operator',
    '>>=': 'rshift-assign-operator',
    '==': 'eq-operator',
    '!=': 'neq-operator',
    '<': 'lt-operator',
    '>': 'gt-operator',
    '<=': 'lte-operator',
    '>=': 'gte-operator',
    '!': 'not-operator',
    '&&': 'sand-operator',
    '||': 'sor-operator',
    '++': 'inc-operator',
    '--': 'dec-operator',
    ',': 'comma-operator',
    '->*': 'pointer-by-pointer-operator',
    '->': 'pointer-operator',
    '()': 'call-operator',
    '[]': 'subscript-operator'
}  # type: Dict[unicode, unicode]

# ------------------------------------------------------------------------------
# Id v > 1 constants
# ------------------------------------------------------------------------------

_id_fundamental_v2 = {
    # not all of these are actually parsed as fundamental types, TODO: do that
    'void': 'v',
    'bool': 'b',
    'char': 'c',
    'signed char': 'a',
    'unsigned char': 'h',
    'wchar_t': 'w',
    'char32_t': 'Di',
    'char16_t': 'Ds',
    'short': 's',
    'short int': 's',
    'signed short': 's',
    'signed short int': 's',
    'unsigned short': 't',
    'unsigned short int': 't',
    'int': 'i',
    'signed': 'i',
    'signed int': 'i',
    'unsigned': 'j',
    'unsigned int': 'j',
    'long': 'l',
    'long int': 'l',
    'signed long': 'l',
    'signed long int': 'l',
    'unsigned long': 'm',
    'unsigned long int': 'm',
    'long long': 'x',
    'long long int': 'x',
    'signed long long': 'x',
    'signed long long int': 'x',
    'unsigned long long': 'y',
    'unsigned long long int': 'y',
    'float': 'f',
    'double': 'd',
    'long double': 'e',
    'auto': 'Da',
    'decltype(auto)': 'Dc',
    'std::nullptr_t': 'Dn'
}  # type: Dict[unicode, unicode]
_id_operator_v2 = {
    'new': 'nw',
    'new[]': 'na',
    'delete': 'dl',
    'delete[]': 'da',
    # the arguments will make the difference between unary and binary
    # in operator definitions
    # '+(unary)' : 'ps',
    # '-(unary)' : 'ng',
    # '&(unary)' : 'ad',
    # '*(unary)' : 'de',
    '~': 'co',
    '+': 'pl',
    '-': 'mi',
    '*': 'ml',
    '/': 'dv',
    '%': 'rm',
    '&': 'an',
    '|': 'or',
    '^': 'eo',
    '=': 'aS',
    '+=': 'pL',
    '-=': 'mI',
    '*=': 'mL',
    '/=': 'dV',
    '%=': 'rM',
    '&=': 'aN',
    '|=': 'oR',
    '^=': 'eO',
    '<<': 'ls',
    '>>': 'rs',
    '<<=': 'lS',
    '>>=': 'rS',
    '==': 'eq',
    '!=': 'ne',
    '<': 'lt',
    '>': 'gt',
    '<=': 'le',
    '>=': 'ge',
    '!': 'nt',
    '&&': 'aa',
    '||': 'oo',
    '++': 'pp',
    '--': 'mm',
    ',': 'cm',
    '->*': 'pm',
    '->': 'pt',
    '()': 'cl',
    '[]': 'ix',
    '.*': 'ds'  # this one is not overloadable, but we need it for expressions
}  # type: Dict[unicode, unicode]
_id_operator_unary_v2 = {
    '++': 'pp_',
    '--': 'mm_',
    '*': 'de',
    '&': 'ad',
    '+': 'ps',
    '-': 'ng',
    '!': 'nt',
    '~': 'co'
}
_id_char_from_prefix = {
    None: 'c', 'u8': 'c',
    'u': 'Ds', 'U': 'Di', 'L': 'w'
}  # type: Dict[unicode, unicode]
# these are ordered by preceedence
_expression_bin_ops = [
    ['||'],
    ['&&'],
    ['|'],
    ['^'],
    ['&'],
    ['==', '!='],
    ['<=', '>=', '<', '>'],
    ['<<', '>>'],
    ['+', '-'],
    ['*', '/', '%'],
    ['.*', '->*']
]
_expression_unary_ops = ["++", "--", "*", "&", "+", "-", "!", "~"]
_expression_assignment_ops = ["=", "*=", "/=", "%=", "+=", "-=",
                              ">>=", "<<=", "&=", "^=", "|="]
_id_explicit_cast = {
    'dynamic_cast': 'dc',
    'static_cast': 'sc',
    'const_cast': 'cc',
    'reinterpret_cast': 'rc'
}


class NoOldIdError(UnicodeMixin, Exception):
    # Used to avoid implementing unneeded id generation for old id schmes.
    def __init__(self, description=""):
        # type: (unicode) -> None
        self.description = description

    def __unicode__(self):
        # type: () -> unicode
        return self.description


class DefinitionError(UnicodeMixin, Exception):
    def __init__(self, description):
        # type: (unicode) -> None
        self.description = description

    def __unicode__(self):
        # type: () -> unicode
        return self.description


class _DuplicateSymbolError(UnicodeMixin, Exception):
    def __init__(self, symbol, declaration):
        # type: (Symbol, Any) -> None
        assert symbol
        assert declaration
        self.symbol = symbol
        self.declaration = declaration

    def __unicode__(self):
        # type: () -> unicode
        return "Internal C++ duplicate symbol error:\n%s" % self.symbol.dump(0)


class ASTBase(UnicodeMixin):
    def __eq__(self, other):
        # type: (Any) -> bool
        if type(self) is not type(other):
            return False
        try:
            for key, value in iteritems(self.__dict__):
                if value != getattr(other, key):
                    return False
        except AttributeError:
            return False
        return True

    def __ne__(self, other):
        # type: (Any) -> bool
        return not self.__eq__(other)

    __hash__ = None  # type: Callable[[], int]

    def clone(self):
        # type: () -> ASTBase
        """Clone a definition expression node."""
        return deepcopy(self)

    def _stringify(self, transform):
        # type: (Callable[[Any], unicode]) -> unicode
        raise NotImplementedError(repr(self))

    def __unicode__(self):
        # type: () -> unicode
        return self._stringify(lambda ast: text_type(ast))

    def get_display_string(self):
        # type: () -> unicode
        return self._stringify(lambda ast: ast.get_display_string())

    def __repr__(self):
        # type: () -> str
        return '<%s %s>' % (self.__class__.__name__, self)


def _verify_description_mode(mode):
    # type: (unicode) -> None
    if mode not in ('lastIsName', 'noneIsName', 'markType', 'param'):
        raise Exception("Description mode '%s' is invalid." % mode)


################################################################################
# Attributes
################################################################################

class ASTCPPAttribute(ASTBase):
    def __init__(self, arg):
        # type: (unicode) -> None
        self.arg = arg

    def _stringify(self, transform):
        return "[[" + self.arg + "]]"

    def describe_signature(self, signode):
        # type: (addnodes.desc_signature) -> None
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


class ASTGnuAttribute(ASTBase):
    def __init__(self, name, args):
        # type: (unicode, Any) -> None
        self.name = name
        self.args = args

    def _stringify(self, transform):
        res = [self.name]  # type: List[unicode]
        if self.args:
            res.append('(')
            res.append(transform(self.args))
            res.append(')')
        return ''.join(res)


class ASTGnuAttributeList(ASTBase):
    def __init__(self, attrs):
        # type: (List[Any]) -> None
        self.attrs = attrs

    def _stringify(self, transform):
        res = ['__attribute__((']  # type: List[unicode]
        first = True
        for attr in self.attrs:
            if not first:
                res.append(', ')
            first = False
            res.append(transform(attr))
        res.append('))')
        return ''.join(res)

    def describe_signature(self, signode):
        # type: (addnodes.desc_signature) -> None
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


class ASTIdAttribute(ASTBase):
    """For simple attributes defined by the user."""

    def __init__(self, id):
        # type: (unicode) -> None
        self.id = id

    def _stringify(self, transform):
        return self.id

    def describe_signature(self, signode):
        # type: (addnodes.desc_signature) -> None
        signode.append(nodes.Text(self.id, self.id))


class ASTParenAttribute(ASTBase):
    """For paren attributes defined by the user."""

    def __init__(self, id, arg):
        # type: (unicode, unicode) -> None
        self.id = id
        self.arg = arg

    def _stringify(self, transform):
        return self.id + '(' + self.arg + ')'

    def describe_signature(self, signode):
        # type: (addnodes.desc_signature) -> None
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


################################################################################
# Expressions and Literals
################################################################################

class ASTPointerLiteral(ASTBase):
    def _stringify(self, transform):
        return u'nullptr'

    def get_id(self, version):
        return 'LDnE'

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('nullptr'))


class ASTBooleanLiteral(ASTBase):
    def __init__(self, value):
        self.value = value

    def _stringify(self, transform):
        if self.value:
            return u'true'
        else:
            return u'false'

    def get_id(self, version):
        if self.value:
            return 'L1E'
        else:
            return 'L0E'

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text(text_type(self)))


class ASTNumberLiteral(ASTBase):
    def __init__(self, data):
        # type: (unicode) -> None
        self.data = data

    def _stringify(self, transform):
        return self.data

    def get_id(self, version):
        return "L%sE" % self.data

    def describe_signature(self, signode, mode, env, symbol):
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


class UnsupportedMultiCharacterCharLiteral(UnicodeMixin, Exception):
    def __init__(self, decoded):
        self.decoded = decoded


class ASTCharLiteral(ASTBase):
    def __init__(self, prefix, data):
        # type: (unicode, unicode) -> None
        self.prefix = prefix  # may be None when no prefix
        self.data = data
        assert prefix in _id_char_from_prefix
        self.type = _id_char_from_prefix[prefix]
        decoded = data.encode().decode('unicode-escape')
        if len(decoded) == 1:
            self.value = ord(decoded)
        else:
            raise UnsupportedMultiCharacterCharLiteral(decoded)

    def _stringify(self, transform):
        if self.prefix is None:
            return "'" + self.data + "'"
        else:
            return self.prefix + "'" + self.data + "'"

    def get_id(self, version):
        return self.type + str(self.value)

    def describe_signature(self, signode, mode, env, symbol):
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


class ASTStringLiteral(ASTBase):
    def __init__(self, data):
        # type: (unicode) -> None
        self.data = data

    def _stringify(self, transform):
        return self.data

    def get_id(self, version):
        # note: the length is not really correct with escaping
        return "LA%d_KcE" % (len(self.data) - 2)

    def describe_signature(self, signode, mode, env, symbol):
        txt = text_type(self)
        signode.append(nodes.Text(txt, txt))


class ASTThisLiteral(ASTBase):
    def _stringify(self, transform):
        return "this"

    def get_id(self, version):
        return "fpT"

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text("this"))


class ASTParenExpr(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return '(' + transform(self.expr) + ')'

    def get_id(self, version):
        return self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('(', '('))
        self.expr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')', ')'))


class ASTFoldExpr(ASTBase):
    def __init__(self, leftExpr, op, rightExpr):
        # type: (Any, unicode, Any) -> None
        assert leftExpr is not None or rightExpr is not None
        self.leftExpr = leftExpr
        self.op = op
        self.rightExpr = rightExpr

    def _stringify(self, transform):
        res = [u'(']
        if self.leftExpr:
            res.append(transform(self.leftExpr))
            res.append(u' ')
            res.append(transform(self.op))
            res.append(u' ')
        res.append(u'...')
        if self.rightExpr:
            res.append(u' ')
            res.append(transform(self.op))
            res.append(u' ')
            res.append(transform(self.rightExpr))
        res.append(u')')
        return u''.join(res)

    def get_id(self, version):
        assert version >= 3
        if version == 3:
            return text_type(self)
        # https://github.com/itanium-cxx-abi/cxx-abi/pull/67
        res = []
        if self.leftExpr is None:  # (... op expr)
            res.append('fl')
        elif self.rightExpr is None:  # (expr op ...)
            res.append('fr')
        else:  # (expr op ... op expr)
            # we don't check where the parameter pack is,
            # we just always call this a binary left fold
            res.append('fL')
        res.append(str(_id_operator_v2[self.op]))  # TODO: remove str when merging to 2.0
        if self.leftExpr:
            res.append(self.leftExpr.get_id(version))
        if self.rightExpr:
            res.append(self.rightExpr.get_id(version))
        return ''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('('))
        if self.leftExpr:
            self.leftExpr.describe_signature(signode, mode, env, symbol)
            signode.append(nodes.Text(' '))
            signode.append(nodes.Text(self.op))
            signode.append(nodes.Text(' '))
        signode.append(nodes.Text('...'))
        if self.rightExpr:
            signode.append(nodes.Text(' '))
            signode.append(nodes.Text(self.op))
            signode.append(nodes.Text(' '))
            self.rightExpr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTBinOpExpr(ASTBase):
    def __init__(self, exprs, ops):
        assert len(exprs) > 0
        assert len(exprs) == len(ops) + 1
        self.exprs = exprs
        self.ops = ops

    def _stringify(self, transform):
        res = []
        res.append(transform(self.exprs[0]))
        for i in range(1, len(self.exprs)):
            res.append(' ')
            res.append(self.ops[i - 1])
            res.append(' ')
            res.append(transform(self.exprs[i]))
        return u''.join(res)

    def get_id(self, version):
        assert version >= 2
        res = []
        for i in range(len(self.ops)):
            res.append(_id_operator_v2[self.ops[i]])
            res.append(self.exprs[i].get_id(version))
        res.append(self.exprs[-1].get_id(version))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        self.exprs[0].describe_signature(signode, mode, env, symbol)
        for i in range(1, len(self.exprs)):
            signode.append(nodes.Text(' '))
            signode.append(nodes.Text(self.ops[i - 1]))
            signode.append(nodes.Text(' '))
            self.exprs[i].describe_signature(signode, mode, env, symbol)


class ASTAssignmentExpr(ASTBase):
    def __init__(self, exprs, ops):
        assert len(exprs) > 0
        assert len(exprs) == len(ops) + 1
        self.exprs = exprs
        self.ops = ops

    def _stringify(self, transform):
        res = []
        res.append(transform(self.exprs[0]))
        for i in range(1, len(self.exprs)):
            res.append(' ')
            res.append(self.ops[i - 1])
            res.append(' ')
            res.append(transform(self.exprs[i]))
        return u''.join(res)

    def get_id(self, version):
        res = []
        for i in range(len(self.ops)):
            res.append(_id_operator_v2[self.ops[i]])
            res.append(self.exprs[i].get_id(version))
        res.append(self.exprs[-1].get_id(version))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        self.exprs[0].describe_signature(signode, mode, env, symbol)
        for i in range(1, len(self.exprs)):
            signode.append(nodes.Text(' '))
            signode.append(nodes.Text(self.ops[i - 1]))
            signode.append(nodes.Text(' '))
            self.exprs[i].describe_signature(signode, mode, env, symbol)


class ASTCastExpr(ASTBase):
    def __init__(self, typ, expr):
        self.typ = typ
        self.expr = expr

    def _stringify(self, transform):
        res = [u'(']
        res.append(transform(self.typ))
        res.append(u')')
        res.append(transform(self.expr))
        return u''.join(res)

    def get_id(self, version):
        return 'cv' + self.typ.get_id(version) + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('('))
        self.typ.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTUnaryOpExpr(ASTBase):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def _stringify(self, transform):
        return transform(self.op) + transform(self.expr)

    def get_id(self, version):
        return _id_operator_unary_v2[self.op] + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text(self.op))
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTSizeofParamPack(ASTBase):
    def __init__(self, identifier):
        self.identifier = identifier

    def _stringify(self, transform):
        return "sizeof...(" + transform(self.identifier) + ")"

    def get_id(self, version):
        return 'sZ' + self.identifier.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('sizeof...('))
        self.identifier.describe_signature(signode, mode, env,
                                           symbol=symbol, prefix="", templateArgs="")
        signode.append(nodes.Text(')'))


class ASTSizeofType(ASTBase):
    def __init__(self, typ):
        self.typ = typ

    def _stringify(self, transform):
        return "sizeof(" + transform(self.typ) + ")"

    def get_id(self, version):
        return 'st' + self.typ.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('sizeof('))
        self.typ.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTSizeofExpr(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return "sizeof " + transform(self.expr)

    def get_id(self, version):
        return 'sz' + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('sizeof '))
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTAlignofExpr(ASTBase):
    def __init__(self, typ):
        self.typ = typ

    def _stringify(self, transform):
        return "alignof(" + transform(self.typ) + ")"

    def get_id(self, version):
        return 'at' + self.typ.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('alignof('))
        self.typ.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTNoexceptExpr(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return "noexcept(" + transform(self.expr) + ")"

    def get_id(self, version):
        return 'nx' + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('noexcept('))
        self.expr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTNewExpr(ASTBase):
    def __init__(self, rooted, isNewTypeId, typ, initList, initType):
        # type: (bool, bool,  ASTType, List[Any], unicode) -> None
        self.rooted = rooted
        self.isNewTypeId = isNewTypeId
        self.typ = typ
        self.initList = initList
        self.initType = initType
        if self.initList is not None:
            assert self.initType in ')}'

    def _stringify(self, transform):
        res = []
        if self.rooted:
            res.append('::')
        res.append('new ')
        # TODO: placement
        if self.isNewTypeId:
            res.append(transform(self.typ))
        else:
            assert False
        if self.initList is not None:
            if self.initType == ')':
                res.append('(')
            first = True
            for e in self.initList:
                if not first:
                    res.append(', ')
                first = False
                res.append(transform(e))
            res.append(self.initType)
        return u''.join(res)

    def get_id(self, version):
        # the array part will be in the type mangling, so na is not used
        res = ['nw']
        # TODO: placement
        res.append('_')
        res.append(self.typ.get_id(version))
        if self.initList is not None:
            if self.initType == ')':
                res.append('pi')
                for e in self.initList:
                    res.append(e.get_id(version))
                res.append('E')
            else:
                assert False
        else:
            res.append('E')
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        if self.rooted:
            signode.append(nodes.Text('::'))
        signode.append(nodes.Text('new '))
        # TODO: placement
        if self.isNewTypeId:
            self.typ.describe_signature(signode, mode, env, symbol)
        else:
            assert False
        if self.initList is not None:
            if self.initType == ')':
                signode.append(nodes.Text('('))
                first = True
                for e in self.initList:
                    if not first:
                        signode.append(nodes.Text(', '))
                    first = False
                    e.describe_signature(signode, mode, env, symbol)
                signode.append(nodes.Text(')'))
            else:
                assert False


class ASTDeleteExpr(ASTBase):
    def __init__(self, rooted, array, expr):
        self.rooted = rooted
        self.array = array
        self.expr = expr

    def _stringify(self, transform):
        res = []
        if self.rooted:
            res.append('::')
        res.append('delete ')
        if self.array:
            res.append('[] ')
        res.append(transform(self.expr))
        return u''.join(res)

    def get_id(self, version):
        if self.array:
            id = "da"
        else:
            id = "dl"
        return id + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        if self.rooted:
            signode.append(nodes.Text('::'))
        signode.append(nodes.Text('delete '))
        if self.array:
            signode.append(nodes.Text('[] '))
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTExplicitCast(ASTBase):
    def __init__(self, cast, typ, expr):
        assert cast in _id_explicit_cast
        self.cast = cast
        self.typ = typ
        self.expr = expr

    def _stringify(self, transform):
        res = [self.cast]
        res.append('<')
        res.append(transform(self.typ))
        res.append('>(')
        res.append(transform(self.expr))
        res.append(')')
        return u''.join(res)

    def get_id(self, version):
        return (_id_explicit_cast[self.cast] +
                self.typ.get_id(version) +
                self.expr.get_id(version))

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text(self.cast))
        signode.append(nodes.Text('<'))
        self.typ.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text('>'))
        signode.append(nodes.Text('('))
        self.expr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTTypeId(ASTBase):
    def __init__(self, typeOrExpr, isType):
        self.typeOrExpr = typeOrExpr
        self.isType = isType

    def _stringify(self, transform):
        return 'typeid(' + transform(self.typeOrExpr) + ')'

    def get_id(self, version):
        prefix = 'ti' if self.isType else 'te'
        return prefix + self.typeOrExpr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('typeid'))
        signode.append(nodes.Text('('))
        self.typeOrExpr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTPostfixCallExpr(ASTBase):
    def __init__(self, exprs):
        self.exprs = exprs

    def _stringify(self, transform):
        res = [u'(']
        first = True
        for e in self.exprs:
            if not first:
                res.append(u', ')
            first = False
            res.append(transform(e))
        res.append(u')')
        return u''.join(res)

    def get_id(self, idPrefix, version):
        res = ['cl', idPrefix]
        for e in self.exprs:
            res.append(e.get_id(version))
        res.append('E')
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('('))
        first = True
        for e in self.exprs:
            if not first:
                signode.append(nodes.Text(', '))
            first = False
            e.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTPostfixArray(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return u'[' + transform(self.expr) + ']'

    def get_id(self, idPrefix, version):
        return 'ix' + idPrefix + self.expr.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('['))
        self.expr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(']'))


class ASTPostfixInc(ASTBase):
    def _stringify(self, transform):
        return u'++'

    def get_id(self, idPrefix, version):
        return 'pp' + idPrefix

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('++'))


class ASTPostfixDec(ASTBase):
    def _stringify(self, transform):
        return u'--'

    def get_id(self, idPrefix, version):
        return 'mm' + idPrefix

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('--'))


class ASTPostfixMember(ASTBase):
    def __init__(self, name):
        self.name = name

    def _stringify(self, transform):
        return u'.' + transform(self.name)

    def get_id(self, idPrefix, version):
        return 'dt' + idPrefix + self.name.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('.'))
        self.name.describe_signature(signode, 'noneIsName', env, symbol)


class ASTPostfixMemberOfPointer(ASTBase):
    def __init__(self, name):
        self.name = name

    def _stringify(self, transform):
        return u'->' + transform(self.name)

    def get_id(self, idPrefix, version):
        return 'pt' + idPrefix + self.name.get_id(version)

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('->'))
        self.name.describe_signature(signode, 'noneIsName', env, symbol)


class ASTPostfixExpr(ASTBase):
    def __init__(self, prefix, postFixes):
        assert len(postFixes) > 0
        self.prefix = prefix
        self.postFixes = postFixes

    def _stringify(self, transform):
        res = [transform(self.prefix)]
        for p in self.postFixes:
            res.append(transform(p))
        return u''.join(res)

    def get_id(self, version):
        id = self.prefix.get_id(version)
        for p in self.postFixes:
            id = p.get_id(id, version)
        return id

    def describe_signature(self, signode, mode, env, symbol):
        self.prefix.describe_signature(signode, mode, env, symbol)
        for p in self.postFixes:
            p.describe_signature(signode, mode, env, symbol)


class ASTPackExpansionExpr(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return transform(self.expr) + '...'

    def get_id(self, version):
        id = self.expr.get_id(version)
        return 'sp' + id

    def describe_signature(self, signode, mode, env, symbol):
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += nodes.Text('...')


class ASTFallbackExpr(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return self.expr

    def get_id(self, version):
        return text_type(self.expr)

    def describe_signature(self, signode, mode, env, symbol):
        signode += nodes.Text(self.expr)


################################################################################
# The Rest
################################################################################

class ASTIdentifier(ASTBase):
    def __init__(self, identifier):
        # type: (unicode) -> None
        assert identifier is not None
        assert len(identifier) != 0
        self.identifier = identifier

    def is_anon(self):
        return self.identifier[0] == '@'

    def get_id(self, version):
        # type: (int) -> unicode
        if self.is_anon() and version < 3:
            raise NoOldIdError()
        if version == 1:
            if self.identifier == 'size_t':
                return 's'
            else:
                return self.identifier
        if self.identifier == "std":
            return 'St'
        elif self.identifier[0] == "~":
            # a destructor, just use an arbitrary version of dtors
            return 'D0'
        else:
            if self.is_anon():
                return u'Ut%d_%s' % (len(self.identifier) - 1, self.identifier[1:])
            else:
                return text_type(len(self.identifier)) + self.identifier

    # and this is where we finally make a difference between __unicode__ and the display string

    def __unicode__(self):
        # type: () -> unicode
        return self.identifier

    def get_display_string(self):
        # type: () -> unicode
        return u"[anonymous]" if self.is_anon() else self.identifier

    def describe_signature(self, signode, mode, env, prefix, templateArgs, symbol):
        # type: (Any, unicode, BuildEnvironment, unicode, unicode, Symbol) -> None
        _verify_description_mode(mode)
        if mode == 'markType':
            targetText = prefix + self.identifier + templateArgs
            pnode = addnodes.pending_xref('', refdomain='cpp',
                                          reftype='identifier',
                                          reftarget=targetText, modname=None,
                                          classname=None)
            key = symbol.get_lookup_key()
            pnode['cpp:parent_key'] = key
            if self.is_anon():
                pnode += nodes.strong(text="[anonymous]")
            else:
                pnode += nodes.Text(self.identifier)
            signode += pnode
        elif mode == 'lastIsName':
            if self.is_anon():
                signode += nodes.strong(text="[anonymous]")
            else:
                signode += addnodes.desc_name(self.identifier, self.identifier)
        elif mode == 'noneIsName':
            if self.is_anon():
                signode += nodes.strong(text="[anonymous]")
            else:
                signode += nodes.Text(self.identifier)
        else:
            raise Exception('Unknown description mode: %s' % mode)


class ASTTemplateKeyParamPackIdDefault(ASTBase):
    def __init__(self, key, identifier, parameterPack, default):
        # type: (unicode, ASTIdentifier, bool, ASTType) -> None
        assert key
        if parameterPack:
            assert default is None
        self.key = key
        self.identifier = identifier
        self.parameterPack = parameterPack
        self.default = default

    def get_identifier(self):
        # type: () -> ASTIdentifier
        return self.identifier

    def get_id(self, version):
        # type: (int) -> unicode
        assert version >= 2
        # this is not part of the normal name mangling in C++
        res = []
        if self.parameterPack:
            res.append('Dp')
        else:
            res.append('0')  # we need to put something
        return ''.join(res)

    def _stringify(self, transform):
        res = [self.key]  # type: List[unicode]
        if self.parameterPack:
            if self.identifier:
                res.append(' ')
            res.append('...')
        if self.identifier:
            if not self.parameterPack:
                res.append(' ')
            res.append(transform(self.identifier))
        if self.default:
            res.append(' = ')
            res.append(transform(self.default))
        return ''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        signode += nodes.Text(self.key)
        if self.parameterPack:
            if self.identifier:
                signode += nodes.Text(' ')
            signode += nodes.Text('...')
        if self.identifier:
            if not self.parameterPack:
                signode += nodes.Text(' ')
            self.identifier.describe_signature(signode, mode, env, '', '', symbol)
        if self.default:
            signode += nodes.Text(' = ')
            self.default.describe_signature(signode, 'markType', env, symbol)


class ASTTemplateParamType(ASTBase):
    def __init__(self, data):
        # type: (ASTTemplateKeyParamPackIdDefault) -> None
        assert data
        self.data = data

    @property
    def name(self):
        # type: () -> ASTNestedName
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self):
        return self.data.parameterPack

    def get_identifier(self):
        # type: () -> ASTIdentifier
        return self.data.get_identifier()

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        # this is not part of the normal name mangling in C++
        assert version >= 2
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=False)
        else:
            return self.data.get_id(version)

    def _stringify(self, transform):
        return transform(self.data)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        self.data.describe_signature(signode, mode, env, symbol)


class ASTTemplateParamConstrainedTypeWithInit(ASTBase):
    def __init__(self, type, init):
        # type: (Any, Any) -> None
        assert type
        self.type = type
        self.init = init

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.type.name

    @property
    def isPack(self):
        return self.type.isPack

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        # this is not part of the normal name mangling in C++
        assert version >= 2
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=False)
        else:
            return self.type.get_id(version)

    def _stringify(self, transform):
        res = transform(self.type)
        if self.init:
            res += " = "
            res += transform(self.init)
        return res

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        self.type.describe_signature(signode, mode, env, symbol)
        if self.init:
            signode += nodes.Text(" = ")
            self.init.describe_signature(signode, mode, env, symbol)


class ASTTemplateParamTemplateType(ASTBase):
    def __init__(self, nestedParams, data):
        # type: (Any, ASTTemplateKeyParamPackIdDefault) -> None
        assert nestedParams
        assert data
        self.nestedParams = nestedParams
        self.data = data

    @property
    def name(self):
        # type: () -> ASTNestedName
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self):
        return self.data.parameterPack

    def get_identifier(self):
        # type: () -> ASTIdentifier
        return self.data.get_identifier()

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        assert version >= 2
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        else:
            return self.nestedParams.get_id(version) + self.data.get_id(version)

    def _stringify(self, transform):
        return transform(self.nestedParams) + transform(self.data)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        self.nestedParams.describe_signature(signode, 'noneIsName', env, symbol)
        signode += nodes.Text(' ')
        self.data.describe_signature(signode, mode, env, symbol)


class ASTTemplateParamNonType(ASTBase):
    def __init__(self, param):
        # type: (Any) -> None
        assert param
        self.param = param

    @property
    def name(self):
        # type: () -> ASTNestedName
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self):
        return self.param.isPack

    def get_identifier(self):
        # type: () -> ASTIdentifier
        name = self.param.name
        if name:
            assert len(name.names) == 1
            assert name.names[0].identOrOp
            assert not name.names[0].templateArgs
            return name.names[0].identOrOp
        else:
            return None

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        assert version >= 2
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        else:
            return '_' + self.param.get_id(version)

    def _stringify(self, transform):
        return transform(self.param)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        self.param.describe_signature(signode, mode, env, symbol)


class ASTTemplateParams(ASTBase):
    def __init__(self, params):
        # type: (Any) -> None
        assert params is not None
        self.params = params
        self.isNested = False  # whether it's a template template param

    def get_id(self, version):
        # type: (int) -> unicode
        assert version >= 2
        res = []
        res.append("I")
        for param in self.params:
            res.append(param.get_id(version))
        res.append("E")
        return ''.join(res)

    def _stringify(self, transform):
        res = []
        res.append(u"template<")
        res.append(u", ".join(transform(a) for a in self.params))
        res.append(u"> ")
        return ''.join(res)

    def describe_signature(self, parentNode, mode, env, symbol, lineSpec=None):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol, bool) -> None
        # 'lineSpec' is defaulted becuase of template template parameters
        def makeLine(parentNode=parentNode):
            signode = addnodes.desc_signature_line()
            parentNode += signode
            signode.sphinx_cpp_tagname = 'templateParams'
            return signode
        if self.isNested:
            lineNode = parentNode
        else:
            lineNode = makeLine()
        lineNode += nodes.Text("template<")
        first = True
        for param in self.params:
            if not first:
                lineNode += nodes.Text(", ")
            first = False
            if lineSpec:
                lineNode = makeLine()
            param.describe_signature(lineNode, mode, env, symbol)
        if lineSpec and not first:
            lineNode = makeLine()
        lineNode += nodes.Text(">")


class ASTTemplateIntroductionParameter(ASTBase):
    def __init__(self, identifier, parameterPack):
        # type: (ASTIdentifier, bool) -> None
        self.identifier = identifier
        self.parameterPack = parameterPack

    @property
    def name(self):
        # type: () -> ASTNestedName
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self):
        return self.parameterPack

    def get_identifier(self):
        # type: () -> ASTIdentifier
        return self.identifier

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        assert version >= 2
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        else:
            if self.parameterPack:
                return 'Dp'
            else:
                return '0'  # we need to put something

    def get_id_as_arg(self, version):
        # type: (int) -> unicode
        assert version >= 2
        # used for the implicit requires clause
        res = self.identifier.get_id(version)
        if self.parameterPack:
            return u'sp' + res
        else:
            return res

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.parameterPack:
            res.append('...')
        res.append(transform(self.identifier))
        return ''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        if self.parameterPack:
            signode += nodes.Text('...')
        self.identifier.describe_signature(signode, mode, env, '', '', symbol)


class ASTTemplateIntroduction(ASTBase):
    def __init__(self, concept, params):
        # type: (Any, List[Any]) -> None
        assert len(params) > 0
        self.concept = concept
        self.params = params

    def get_id(self, version):
        # type: (int) -> unicode
        assert version >= 2
        # first do the same as a normal template parameter list
        res = []
        res.append("I")
        for param in self.params:
            res.append(param.get_id(version))
        res.append("E")
        # let's use X expr E, which is otherwise for constant template args
        res.append("X")
        res.append(self.concept.get_id(version))
        res.append("I")
        for param in self.params:
            res.append(param.get_id_as_arg(version))
        res.append("E")
        res.append("E")
        return ''.join(res)

    def _stringify(self, transform):
        res = []
        res.append(transform(self.concept))
        res.append('{')
        res.append(', '.join(transform(param) for param in self.params))
        res.append('} ')
        return ''.join(res)

    def describe_signature(self, parentNode, mode, env, symbol, lineSpec):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol, bool) -> None
        # Note: 'lineSpec' has no effect on template introductions.
        signode = addnodes.desc_signature_line()
        parentNode += signode
        signode.sphinx_cpp_tagname = 'templateIntroduction'
        self.concept.describe_signature(signode, 'markType', env, symbol)
        signode += nodes.Text('{')
        first = True
        for param in self.params:
            if not first:
                signode += nodes.Text(', ')
            first = False
            param.describe_signature(signode, mode, env, symbol)
        signode += nodes.Text('}')


class ASTTemplateDeclarationPrefix(ASTBase):
    def __init__(self, templates):
        # type: (List[Any]) -> None
        # templates is None means it's an explicit instantiation of a variable
        self.templates = templates

    def get_id(self, version):
        # type: (int) -> unicode
        assert version >= 2
        # this is not part of a normal name mangling system
        res = []
        for t in self.templates:
            res.append(t.get_id(version))
        return u''.join(res)

    def _stringify(self, transform):
        res = []
        for t in self.templates:
            res.append(transform(t))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol, lineSpec):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol, bool) -> None
        _verify_description_mode(mode)
        for t in self.templates:
            t.describe_signature(signode, 'lastIsName', env, symbol, lineSpec)


##############################################################################################


class ASTOperator(ASTBase):
    def is_anon(self):
        return False

    def is_operator(self):
        # type: () -> bool
        return True

    def get_id(self, version):
        # type: (int) -> unicode
        raise NotImplementedError()

    def describe_signature(self, signode, mode, env, prefix, templateArgs, symbol):
        # type: (addnodes.desc_signature, unicode, Any, unicode, unicode, Symbol) -> None
        _verify_description_mode(mode)
        identifier = text_type(self)
        if mode == 'lastIsName':
            signode += addnodes.desc_name(identifier, identifier)
        else:
            signode += addnodes.desc_addname(identifier, identifier)


class ASTOperatorBuildIn(ASTOperator):
    def __init__(self, op):
        # type: (unicode) -> None
        self.op = op

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            ids = _id_operator_v1
        else:
            ids = _id_operator_v2
        if self.op not in ids:
            raise Exception('Internal error: Build-in operator "%s" can not '
                            'be mapped to an id.' % self.op)
        return ids[self.op]

    def _stringify(self, transform):
        if self.op in ('new', 'new[]', 'delete', 'delete[]'):
            return u'operator ' + self.op
        else:
            return u'operator' + self.op


class ASTOperatorType(ASTOperator):
    def __init__(self, type):
        # type: (Any) -> None
        self.type = type

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            return u'castto-%s-operator' % self.type.get_id(version)
        else:
            return u'cv' + self.type.get_id(version)

    def _stringify(self, transform):
        return u''.join(['operator ', transform(self.type)])

    def get_name_no_template(self):
        # type: () -> unicode
        return text_type(self)


class ASTOperatorLiteral(ASTOperator):
    def __init__(self, identifier):
        # type: (Any) -> None
        self.identifier = identifier

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            raise NoOldIdError()
        else:
            return u'li' + self.identifier.get_id(version)

    def _stringify(self, transform):
        return u'operator""' + transform(self.identifier)


##############################################################################################


class ASTTemplateArgConstant(ASTBase):
    def __init__(self, value):
        # type: (Any) -> None
        self.value = value

    def _stringify(self, transform):
        return transform(self.value)

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            return text_type(self).replace(u' ', u'-')
        if version == 2:
            return u'X' + text_type(self) + u'E'
        return u'X' + self.value.get_id(version) + u'E'

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.value.describe_signature(signode, mode, env, symbol)


class ASTTemplateArgs(ASTBase):
    def __init__(self, args):
        # type: (List[Any]) -> None
        assert args is not None
        self.args = args

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            res = []  # type: List[unicode]
            res.append(':')
            res.append(u'.'.join(a.get_id(version) for a in self.args))
            res.append(':')
            return u''.join(res)

        res = []
        res.append('I')
        for a in self.args:
            res.append(a.get_id(version))
        res.append('E')
        return u''.join(res)

    def _stringify(self, transform):
        res = ', '.join(transform(a) for a in self.args)
        return '<' + res + '>'

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode += nodes.Text('<')
        first = True
        for a in self.args:
            if not first:
                signode += nodes.Text(', ')
            first = False
            a.describe_signature(signode, 'markType', env, symbol=symbol)
        signode += nodes.Text('>')


class ASTNestedNameElement(ASTBase):
    def __init__(self, identOrOp, templateArgs):
        # type: (Union[ASTIdentifier, ASTOperator], ASTTemplateArgs) -> None
        self.identOrOp = identOrOp
        self.templateArgs = templateArgs

    def is_operator(self):
        # type: () -> bool
        return False

    def get_id(self, version):
        # type: (int) -> unicode
        res = self.identOrOp.get_id(version)
        if self.templateArgs:
            res += self.templateArgs.get_id(version)
        return res

    def _stringify(self, transform):
        res = transform(self.identOrOp)
        if self.templateArgs:
            res += transform(self.templateArgs)
        return res

    def describe_signature(self, signode, mode, env, prefix, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, unicode, Symbol) -> None
        tArgs = text_type(self.templateArgs) if self.templateArgs is not None else ''
        self.identOrOp.describe_signature(signode, mode, env, prefix, tArgs, symbol)
        if self.templateArgs is not None:
            self.templateArgs.describe_signature(signode, mode, env, symbol)


class ASTNestedName(ASTBase):
    def __init__(self, names, templates, rooted):
        # type: (List[ASTNestedNameElement], List[bool], bool) -> None
        assert len(names) > 0
        self.names = names
        self.templates = templates
        assert len(self.names) == len(self.templates)
        self.rooted = rooted

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self

    def num_templates(self):
        # type: () -> int
        count = 0
        for n in self.names:
            if n.is_operator():
                continue
            if n.templateArgs:
                count += 1
        return count

    def get_id(self, version, modifiers=''):
        # type: (int, unicode) -> unicode
        if version == 1:
            tt = text_type(self)
            if tt in _id_shorthands_v1:
                return _id_shorthands_v1[tt]
            else:
                return u'::'.join(n.get_id(version) for n in self.names)
        res = []  # type: List[unicode]
        if len(self.names) > 1 or len(modifiers) > 0:
            res.append('N')
        res.append(modifiers)
        for n in self.names:
            res.append(n.get_id(version))
        if len(self.names) > 1 or len(modifiers) > 0:
            res.append('E')
        return u''.join(res)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.rooted:
            res.append('')
        for i in range(len(self.names)):
            n = self.names[i]
            t = self.templates[i]
            if t:
                res.append("template " + transform(n))
            else:
                res.append(transform(n))
        return '::'.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        # just print the name part, with template args, not template params
        if mode == 'noneIsName':
            signode += nodes.Text(text_type(self))
        elif mode == 'param':
            name = text_type(self)
            signode += nodes.emphasis(name, name)
        elif mode == 'markType' or mode == 'lastIsName':
            # Each element should be a pending xref targeting the complete
            # prefix. however, only the identifier part should be a link, such
            # that template args can be a link as well.
            # For 'lastIsName' we should also prepend template parameter lists.
            templateParams = []  # type: List[Any]
            if mode == 'lastIsName':
                assert symbol is not None
                if symbol.declaration.templatePrefix is not None:
                    templateParams = symbol.declaration.templatePrefix.templates
            iTemplateParams = 0
            templateParamsPrefix = u''
            prefix = ''  # type: unicode
            first = True
            names = self.names[:-1] if mode == 'lastIsName' else self.names
            # If lastIsName, then wrap all of the prefix in a desc_addname,
            # else append directly to signode.
            # NOTE: Breathe relies on the prefix being in the desc_addname node,
            #       so it can remove it in inner declarations.
            dest = signode
            if mode == 'lastIsName':
                dest = addnodes.desc_addname()
            for i in range(len(names)):
                nne = names[i]
                template = self.templates[i]
                if not first:
                    dest += nodes.Text('::')
                    prefix += '::'
                if template:
                    dest += nodes.Text("template ")
                first = False
                txt_nne = text_type(nne)
                if txt_nne != '':
                    if nne.templateArgs and iTemplateParams < len(templateParams):
                        templateParamsPrefix += text_type(templateParams[iTemplateParams])
                        iTemplateParams += 1
                    nne.describe_signature(dest, 'markType',
                                           env, templateParamsPrefix + prefix, symbol)
                prefix += txt_nne
            if mode == 'lastIsName':
                if len(self.names) > 1:
                    dest += addnodes.desc_addname('::', '::')
                    signode += dest
                if self.templates[-1]:
                    signode += nodes.Text("template ")
                self.names[-1].describe_signature(signode, mode, env, '', symbol)
        else:
            raise Exception('Unknown description mode: %s' % mode)


class ASTTrailingTypeSpecFundamental(ASTBase):
    def __init__(self, name):
        # type: (unicode) -> None
        self.name = name

    def _stringify(self, transform):
        return self.name

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            res = []
            for a in self.name.split(' '):
                if a in _id_fundamental_v1:
                    res.append(_id_fundamental_v1[a])
                else:
                    res.append(a)
            return u'-'.join(res)

        if self.name not in _id_fundamental_v2:
            raise Exception(
                'Semi-internal error: Fundamental type "%s" can not be mapped '
                'to an id. Is it a true fundamental type? If not so, the '
                'parser should have rejected it.' % self.name)
        return _id_fundamental_v2[self.name]

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        signode += nodes.Text(text_type(self.name))


class ASTTrailingTypeSpecName(ASTBase):
    def __init__(self, prefix, nestedName):
        # type: (unicode, Any) -> None
        self.prefix = prefix
        self.nestedName = nestedName

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.nestedName

    def get_id(self, version):
        # type: (int) -> unicode
        return self.nestedName.get_id(version)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.prefix:
            res.append(self.prefix)
            res.append(' ')
        res.append(transform(self.nestedName))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        if self.prefix:
            signode += addnodes.desc_annotation(self.prefix, self.prefix)
            signode += nodes.Text(' ')
        self.nestedName.describe_signature(signode, mode, env, symbol=symbol)


class ASTTrailingTypeSpecDecltypeAuto(ASTBase):
    def _stringify(self, transform):
        return u'decltype(auto)'

    def get_id(self, version):
        if version == 1:
            raise NoOldIdError()
        return 'Dc'

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        signode.append(nodes.Text(text_type(self)))


class ASTTrailingTypeSpecDecltype(ASTBase):
    def __init__(self, expr):
        self.expr = expr

    def _stringify(self, transform):
        return u'decltype(' + transform(self.expr) + ')'

    def get_id(self, version):
        if version == 1:
            raise NoOldIdError()
        return 'DT' + self.expr.get_id(version) + "E"

    def describe_signature(self, signode, mode, env, symbol):
        signode.append(nodes.Text('decltype('))
        self.expr.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text(')'))


class ASTFunctionParameter(ASTBase):
    def __init__(self, arg, ellipsis=False):
        # type: (Any, bool) -> None
        self.arg = arg
        self.ellipsis = ellipsis

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        # else, do the usual
        if self.ellipsis:
            return 'z'
        else:
            return self.arg.get_id(version)

    def _stringify(self, transform):
        if self.ellipsis:
            return '...'
        else:
            return transform(self.arg)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        if self.ellipsis:
            signode += nodes.Text('...')
        else:
            self.arg.describe_signature(signode, mode, env, symbol=symbol)


class ASTParametersQualifiers(ASTBase):
    def __init__(self, args, volatile, const, refQual, exceptionSpec, override,
                 final, initializer):
        # type: (List[Any], bool, bool, unicode, unicode, bool, bool, unicode) -> None
        self.args = args
        self.volatile = volatile
        self.const = const
        self.refQual = refQual
        self.exceptionSpec = exceptionSpec
        self.override = override
        self.final = final
        self.initializer = initializer

    @property
    def function_params(self):
        # type: () -> Any
        return self.args

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        res = []
        if self.volatile:
            res.append('V')
        if self.const:
            if version == 1:
                res.append('C')
            else:
                res.append('K')
        if self.refQual == '&&':
            res.append('O')
        elif self.refQual == '&':
            res.append('R')
        return u''.join(res)

    def get_param_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            if len(self.args) == 0:
                return ''
            else:
                return u'__' + u'.'.join(a.get_id(version) for a in self.args)
        if len(self.args) == 0:
            return 'v'
        else:
            return u''.join(a.get_id(version) for a in self.args)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        res.append('(')
        first = True
        for a in self.args:
            if not first:
                res.append(', ')
            first = False
            res.append(text_type(a))
        res.append(')')
        if self.volatile:
            res.append(' volatile')
        if self.const:
            res.append(' const')
        if self.refQual:
            res.append(' ')
            res.append(self.refQual)
        if self.exceptionSpec:
            res.append(' ')
            res.append(text_type(self.exceptionSpec))
        if self.final:
            res.append(' final')
        if self.override:
            res.append(' override')
        if self.initializer:
            res.append(' = ')
            res.append(self.initializer)
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        paramlist = addnodes.desc_parameterlist()
        for arg in self.args:
            param = addnodes.desc_parameter('', '', noemph=True)
            if mode == 'lastIsName':  # i.e., outer-function params
                arg.describe_signature(param, 'param', env, symbol=symbol)
            else:
                arg.describe_signature(param, 'markType', env, symbol=symbol)
            paramlist += param
        signode += paramlist

        def _add_anno(signode, text):
            signode += nodes.Text(' ')
            signode += addnodes.desc_annotation(text, text)

        def _add_text(signode, text):
            signode += nodes.Text(' ' + text)

        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            _add_anno(signode, 'const')
        if self.refQual:
            _add_text(signode, self.refQual)
        if self.exceptionSpec:
            _add_anno(signode, text_type(self.exceptionSpec))
        if self.final:
            _add_anno(signode, 'final')
        if self.override:
            _add_anno(signode, 'override')
        if self.initializer:
            _add_text(signode, '= ' + text_type(self.initializer))


class ASTDeclSpecsSimple(ASTBase):
    def __init__(self, storage, threadLocal, inline, virtual, explicit,
                 constexpr, volatile, const, friend, attrs):
        # type: (unicode, bool, bool, bool, bool, bool, bool, bool, bool, List[Any]) -> None
        self.storage = storage
        self.threadLocal = threadLocal
        self.inline = inline
        self.virtual = virtual
        self.explicit = explicit
        self.constexpr = constexpr
        self.volatile = volatile
        self.const = const
        self.friend = friend
        self.attrs = attrs

    def mergeWith(self, other):
        # type: (ASTDeclSpecsSimple) -> ASTDeclSpecsSimple
        if not other:
            return self
        return ASTDeclSpecsSimple(self.storage or other.storage,
                                  self.threadLocal or other.threadLocal,
                                  self.inline or other.inline,
                                  self.virtual or other.virtual,
                                  self.explicit or other.explicit,
                                  self.constexpr or other.constexpr,
                                  self.volatile or other.volatile,
                                  self.const or other.const,
                                  self.friend or other.friend,
                                  self.attrs + other.attrs)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        res.extend(transform(attr) for attr in self.attrs)
        if self.storage:
            res.append(self.storage)
        if self.threadLocal:
            res.append('thread_local')
        if self.inline:
            res.append('inline')
        if self.friend:
            res.append('friend')
        if self.virtual:
            res.append('virtual')
        if self.explicit:
            res.append('explicit')
        if self.constexpr:
            res.append('constexpr')
        if self.volatile:
            res.append('volatile')
        if self.const:
            res.append('const')
        return u' '.join(res)

    def describe_signature(self, modifiers):
        # type: (List[nodes.Node]) -> None
        def _add(modifiers, text):
            if len(modifiers) > 0:
                modifiers.append(nodes.Text(' '))
            modifiers.append(addnodes.desc_annotation(text, text))
        for attr in self.attrs:
            if len(modifiers) > 0:
                modifiers.append(nodes.Text(' '))
            modifiers.append(attr.describe_signature(modifiers))
        if self.storage:
            _add(modifiers, self.storage)
        if self.threadLocal:
            _add(modifiers, 'thread_local')
        if self.inline:
            _add(modifiers, 'inline')
        if self.friend:
            _add(modifiers, 'friend')
        if self.virtual:
            _add(modifiers, 'virtual')
        if self.explicit:
            _add(modifiers, 'explicit')
        if self.constexpr:
            _add(modifiers, 'constexpr')
        if self.volatile:
            _add(modifiers, 'volatile')
        if self.const:
            _add(modifiers, 'const')


class ASTDeclSpecs(ASTBase):
    def __init__(self, outer, leftSpecs, rightSpecs, trailing):
        # leftSpecs and rightSpecs are used for output
        # allSpecs are used for id generation
        self.outer = outer
        self.leftSpecs = leftSpecs
        self.rightSpecs = rightSpecs
        self.allSpecs = self.leftSpecs.mergeWith(self.rightSpecs)
        self.trailingTypeSpec = trailing

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.trailingTypeSpec.name

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            res = []
            res.append(self.trailingTypeSpec.get_id(version))
            if self.allSpecs.volatile:
                res.append('V')
            if self.allSpecs.const:
                res.append('C')
            return u''.join(res)
        res = []
        if self.allSpecs.volatile:
            res.append('V')
        if self.allSpecs.const:
            res.append('K')
        if self.trailingTypeSpec is not None:
            res.append(self.trailingTypeSpec.get_id(version))
        return u''.join(res)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        l = transform(self.leftSpecs)
        if len(l) > 0:
            if len(res) > 0:
                res.append(" ")
            res.append(l)
        if self.trailingTypeSpec:
            if len(res) > 0:
                res.append(" ")
            res.append(transform(self.trailingTypeSpec))
            r = text_type(self.rightSpecs)
            if len(r) > 0:
                if len(res) > 0:
                    res.append(" ")
                res.append(r)
        return "".join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        modifiers = []  # type: List[nodes.Node]

        def _add(modifiers, text):
            if len(modifiers) > 0:
                modifiers.append(nodes.Text(' '))
            modifiers.append(addnodes.desc_annotation(text, text))

        self.leftSpecs.describe_signature(modifiers)

        for m in modifiers:
            signode += m
        if self.trailingTypeSpec:
            if len(modifiers) > 0:
                signode += nodes.Text(' ')
            self.trailingTypeSpec.describe_signature(signode, mode, env,
                                                     symbol=symbol)
            modifiers = []
            self.rightSpecs.describe_signature(modifiers)
            if len(modifiers) > 0:
                signode += nodes.Text(' ')
            for m in modifiers:
                signode += m


class ASTArray(ASTBase):
    def __init__(self, size):
        self.size = size

    def _stringify(self, transform):
        if self.size:
            return u'[' + transform(self.size) + ']'
        else:
            return u'[]'

    def get_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            return u'A'
        if version == 2:
            if self.size:
                return u'A' + text_type(self.size) + u'_'
            else:
                return u'A_'
        if self.size:
            return u'A' + self.size.get_id(version) + u'_'
        else:
            return u'A_'

    def describe_signature(self, signode, mode, env, symbol):
        _verify_description_mode(mode)
        signode.append(nodes.Text("["))
        if self.size:
            self.size.describe_signature(signode, mode, env, symbol)
        signode.append(nodes.Text("]"))


class ASTDeclaratorPtr(ASTBase):
    def __init__(self, next, volatile, const, attrs):
        # type: (Any, bool, bool, Any) -> None
        assert next
        self.next = next
        self.volatile = volatile
        self.const = const
        self.attrs = attrs

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.next.name

    @property
    def function_params(self):
        # type: () -> Any
        return self.next.function_params

    def require_space_after_declSpecs(self):
        # type: () -> bool
        # TODO: if has paramPack, then False ?
        return True

    def _stringify(self, transform):
        res = ['*']  # type: List[unicode]
        for a in self.attrs:
            res.append(transform(a))
        if len(self.attrs) > 0 and (self.volatile or self.const):
            res.append(' ')
        if self.volatile:
            res.append('volatile')
        if self.const:
            if self.volatile:
                res.append(' ')
            res.append('const')
        if self.const or self.volatile or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs:
                res.append(' ')
        res.append(transform(self.next))
        return u''.join(res)

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version):
        # type: (int) -> unicode
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            res = ['P']
            if self.volatile:
                res.append('V')
            if self.const:
                res.append('C')
            res.append(self.next.get_ptr_suffix_id(version))
            return u''.join(res)

        res = [self.next.get_ptr_suffix_id(version)]
        res.append('P')
        if self.volatile:
            res.append('V')
        if self.const:
            res.append('C')
        return u''.join(res)

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        # ReturnType *next, so we are part of the return type of 'next
        res = ['P']  # type: List[unicode]
        if self.volatile:
            res.append('V')
        if self.const:
            res.append('C')
        res.append(returnTypeId)
        return self.next.get_type_id(version, returnTypeId=u''.join(res))

    def is_function_type(self):
        # type: () -> bool
        return self.next.is_function_type()

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode += nodes.Text("*")
        for a in self.attrs:
            a.describe_signature(signode)
        if len(self.attrs) > 0 and (self.volatile or self.const):
            signode += nodes.Text(' ')

        def _add_anno(signode, text):
            signode += addnodes.desc_annotation(text, text)
        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            if self.volatile:
                signode += nodes.Text(' ')
            _add_anno(signode, 'const')
        if self.const or self.volatile or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs:
                signode += nodes.Text(' ')
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorRef(ASTBase):
    def __init__(self, next, attrs):
        # type: (Any, Any) -> None
        assert next
        self.next = next
        self.attrs = attrs

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.next.name

    @property
    def isPack(self):
        return True

    @property
    def function_params(self):
        # type: () -> Any
        return self.next.function_params

    def require_space_after_declSpecs(self):
        # type: () -> bool
        return self.next.require_space_after_declSpecs()

    def _stringify(self, transform):
        res = ['&']
        for a in self.attrs:
            res.append(transform(a))
        if len(self.attrs) > 0 and self.next.require_space_after_declSpecs:
            res.append(' ')
        res.append(transform(self.next))
        return u''.join(res)

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version):  # only the parameters (if any)
        # type: (int) -> unicode
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            return u'R' + self.next.get_ptr_suffix_id(version)
        else:
            return self.next.get_ptr_suffix_id(version) + u'R'

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        assert version >= 2
        # ReturnType &next, so we are part of the return type of 'next
        return self.next.get_type_id(version, returnTypeId=u'R' + returnTypeId)

    def is_function_type(self):
        # type: () -> bool
        return self.next.is_function_type()

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode += nodes.Text("&")
        for a in self.attrs:
            a.describe_signature(signode)
        if len(self.attrs) > 0 and self.next.require_space_after_declSpecs:
            signode += nodes.Text(' ')
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorParamPack(ASTBase):
    def __init__(self, next):
        # type: (Any) -> None
        assert next
        self.next = next

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.next.name

    @property
    def function_params(self):
        # type: () -> Any
        return self.next.function_params

    def require_space_after_declSpecs(self):
        # type: () -> bool
        return False

    def _stringify(self, transform):
        res = transform(self.next)
        if self.next.name:
            res = ' ' + res
        return '...' + res

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version):  # only the parameters (if any)
        # type: (int) -> unicode
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            return 'Dp' + self.next.get_ptr_suffix_id(version)
        else:
            return self.next.get_ptr_suffix_id(version) + u'Dp'

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        assert version >= 2
        # ReturnType... next, so we are part of the return type of 'next
        return self.next.get_type_id(version, returnTypeId=u'Dp' + returnTypeId)

    def is_function_type(self):
        # type: () -> bool
        return self.next.is_function_type()

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode += nodes.Text("...")
        if self.next.name:
            signode += nodes.Text(' ')
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorMemPtr(ASTBase):
    def __init__(self, className, const, volatile, next):
        # type: (Any, bool, bool, Any) -> None
        assert className
        assert next
        self.className = className
        self.const = const
        self.volatile = volatile
        self.next = next

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.next.name

    @property
    def function_params(self):
        # type: () -> Any
        return self.next.function_params

    def require_space_after_declSpecs(self):
        # type: () -> bool
        return True

    def _stringify(self, transform):
        res = []
        res.append(transform(self.className))
        res.append('::*')
        if self.volatile:
            res.append(' volatile')
        if self.const:
            res.append(' const')
        if self.next.require_space_after_declSpecs():
            res.append(' ')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            raise NoOldIdError()
        else:
            return self.next.get_modifiers_id(version)

    def get_param_id(self, version):  # only the parameters (if any)
        # type: (int) -> unicode
        if version == 1:
            raise NoOldIdError()
        else:
            return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            raise NoOldIdError()
        else:
            raise NotImplementedError()
            return self.next.get_ptr_suffix_id(version) + u'Dp'

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        assert version >= 2
        # ReturnType name::* next, so we are part of the return type of next
        nextReturnTypeId = ''  # type: unicode
        if self.volatile:
            nextReturnTypeId += 'V'
        if self.const:
            nextReturnTypeId += 'K'
        nextReturnTypeId += 'M'
        nextReturnTypeId += self.className.get_id(version)
        nextReturnTypeId += returnTypeId
        return self.next.get_type_id(version, nextReturnTypeId)

    def is_function_type(self):
        # type: () -> bool
        return self.next.is_function_type()

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.className.describe_signature(signode, mode, env, symbol)
        signode += nodes.Text('::*')

        def _add_anno(signode, text):
            signode += addnodes.desc_annotation(text, text)
        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            if self.volatile:
                signode += nodes.Text(' ')
            _add_anno(signode, 'const')
        if self.next.require_space_after_declSpecs():
            if self.volatile or self.const:
                signode += nodes.Text(' ')
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorParen(ASTBase):
    def __init__(self, inner, next):
        # type: (Any, Any) -> None
        assert inner
        assert next
        self.inner = inner
        self.next = next
        # TODO: we assume the name, params, and qualifiers are in inner

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.inner.name

    @property
    def function_params(self):
        # type: () -> Any
        return self.inner.function_params

    def require_space_after_declSpecs(self):
        # type: () -> bool
        return True

    def _stringify(self, transform):
        res = ['(']  # type: List[unicode]
        res.append(transform(self.inner))
        res.append(')')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version):
        # type: (int) -> unicode
        return self.inner.get_modifiers_id(version)

    def get_param_id(self, version):  # only the parameters (if any)
        # type: (int) -> unicode
        return self.inner.get_param_id(version)

    def get_ptr_suffix_id(self, version):
        # type: (int) -> unicode
        if version == 1:
            raise NoOldIdError()  # TODO: was this implemented before?
            return self.next.get_ptr_suffix_id(version) + \
                self.inner.get_ptr_suffix_id(version)
        else:
            return self.inner.get_ptr_suffix_id(version) + \
                self.next.get_ptr_suffix_id(version)

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        assert version >= 2
        # ReturnType (inner)next, so 'inner' returns everything outside
        nextId = self.next.get_type_id(version, returnTypeId)
        return self.inner.get_type_id(version, returnTypeId=nextId)

    def is_function_type(self):
        # type: () -> bool
        return self.inner.is_function_type()

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode += nodes.Text('(')
        self.inner.describe_signature(signode, mode, env, symbol)
        signode += nodes.Text(')')
        self.next.describe_signature(signode, "noneIsName", env, symbol)


class ASTDeclaratorNameParamQual(ASTBase):
    def __init__(self, declId, arrayOps, paramQual):
        # type: (Any, List[Any], Any) -> None
        self.declId = declId
        self.arrayOps = arrayOps
        self.paramQual = paramQual

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.declId

    @property
    def isPack(self):
        return False

    @property
    def function_params(self):
        # type: () -> Any
        return self.paramQual.function_params

    def get_modifiers_id(self, version):  # only the modifiers for a function, e.g.,
        # type: (int) -> unicode
        # cv-qualifiers
        if self.paramQual:
            return self.paramQual.get_modifiers_id(version)
        raise Exception(
            "This should only be called on a function: %s" % text_type(self))

    def get_param_id(self, version):  # only the parameters (if any)
        # type: (int) -> unicode
        if self.paramQual:
            return self.paramQual.get_param_id(version)
        else:
            return ''

    def get_ptr_suffix_id(self, version):  # only the array specifiers
        # type: (int) -> unicode
        return u''.join(a.get_id(version) for a in self.arrayOps)

    def get_type_id(self, version, returnTypeId):
        # type: (int, unicode) -> unicode
        assert version >= 2
        res = []
        # TOOD: can we actually have both array ops and paramQual?
        res.append(self.get_ptr_suffix_id(version))
        if self.paramQual:
            res.append(self.get_modifiers_id(version))
            res.append('F')
            res.append(returnTypeId)
            res.append(self.get_param_id(version))
            res.append('E')
        else:
            res.append(returnTypeId)
        return u''.join(res)

    # ------------------------------------------------------------------------

    def require_space_after_declSpecs(self):
        # type: () -> bool
        return self.declId is not None

    def is_function_type(self):
        # type: () -> bool
        return self.paramQual is not None

    def _stringify(self, transform):
        res = []
        if self.declId:
            res.append(transform(self.declId))
        for op in self.arrayOps:
            res.append(transform(op))
        if self.paramQual:
            res.append(transform(self.paramQual))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        if self.declId:
            self.declId.describe_signature(signode, mode, env, symbol)
        for op in self.arrayOps:
            op.describe_signature(signode, mode, env, symbol)
        if self.paramQual:
            self.paramQual.describe_signature(signode, mode, env, symbol)


class ASTInitializer(ASTBase):
    def __init__(self, value):
        self.value = value

    def _stringify(self, transform):
        return u' = ' + transform(self.value)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        signode.append(nodes.Text(' = '))
        self.value.describe_signature(signode, 'markType', env, symbol)


class ASTType(ASTBase):
    def __init__(self, declSpecs, decl):
        # type: (Any, Any) -> None
        assert declSpecs
        assert decl
        self.declSpecs = declSpecs
        self.decl = decl

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.decl.name

    @property
    def isPack(self):
        return self.decl.isPack

    @property
    def function_params(self):
        # type: () -> Any
        return self.decl.function_params

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            res = []
            if objectType:  # needs the name
                if objectType == 'function':  # also modifiers
                    res.append(symbol.get_full_nested_name().get_id(version))
                    res.append(self.decl.get_param_id(version))
                    res.append(self.decl.get_modifiers_id(version))
                    if (self.declSpecs.leftSpecs.constexpr or
                            (self.declSpecs.rightSpecs and
                             self.declSpecs.rightSpecs.constexpr)):
                        res.append('CE')
                elif objectType == 'type':  # just the name
                    res.append(symbol.get_full_nested_name().get_id(version))
                else:
                    print(objectType)
                    assert False
            else:  # only type encoding
                if self.decl.is_function_type():
                    raise NoOldIdError()
                res.append(self.declSpecs.get_id(version))
                res.append(self.decl.get_ptr_suffix_id(version))
                res.append(self.decl.get_param_id(version))
            return u''.join(res)
        # other versions
        res = []
        if objectType:  # needs the name
            if objectType == 'function':  # also modifiers
                modifiers = self.decl.get_modifiers_id(version)
                res.append(symbol.get_full_nested_name().get_id(version, modifiers))
                if version >= 4:
                    # with templates we need to mangle the return type in as well
                    templ = symbol.declaration.templatePrefix
                    if templ is not None:
                        typeId = self.decl.get_ptr_suffix_id(version)
                        returnTypeId = self.declSpecs.get_id(version)
                        res.append(typeId)
                        res.append(returnTypeId)
                res.append(self.decl.get_param_id(version))
            elif objectType == 'type':  # just the name
                res.append(symbol.get_full_nested_name().get_id(version))
            else:
                print(objectType)
                assert False
        else:  # only type encoding
            # the 'returnType' of a non-function type is simply just the last
            # type, i.e., for 'int*' it is 'int'
            returnTypeId = self.declSpecs.get_id(version)
            typeId = self.decl.get_type_id(version, returnTypeId)
            res.append(typeId)
        return u''.join(res)

    def _stringify(self, transform):
        res = []
        declSpecs = transform(self.declSpecs)
        res.append(declSpecs)
        if self.decl.require_space_after_declSpecs() and len(declSpecs) > 0:
            res.append(u' ')
        res.append(transform(self.decl))
        return u''.join(res)

    def get_type_declaration_prefix(self):
        # type: () -> unicode
        if self.declSpecs.trailingTypeSpec:
            return 'typedef'
        else:
            return 'type'

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.declSpecs.describe_signature(signode, 'markType', env, symbol)
        if (self.decl.require_space_after_declSpecs() and
                len(text_type(self.declSpecs)) > 0):
            signode += nodes.Text(' ')
        # for parameters that don't really declare new names we get 'markType',
        # this should not be propagated, but be 'noneIsName'.
        if mode == 'markType':
            mode = 'noneIsName'
        self.decl.describe_signature(signode, mode, env, symbol)


class ASTTypeWithInit(ASTBase):
    def __init__(self, type, init):
        # type: (Any, Any) -> None
        self.type = type
        self.init = init

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.type.name

    @property
    def isPack(self):
        return self.type.isPack

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        if objectType != 'member':
            return self.type.get_id(version, objectType)
        if version == 1:
            return symbol.get_full_nested_name().get_id(version) + u'__' \
                + self.type.get_id(version)
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = []
        res.append(transform(self.type))
        if self.init:
            res.append(transform(self.init))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.type.describe_signature(signode, mode, env, symbol)
        if self.init:
            self.init.describe_signature(signode, mode, env, symbol)


class ASTTypeUsing(ASTBase):
    def __init__(self, name, type):
        # type: (Any, Any) -> None
        self.name = name
        self.type = type

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            raise NoOldIdError()
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = []
        res.append(transform(self.name))
        if self.type:
            res.append(' = ')
            res.append(transform(self.type))
        return u''.join(res)

    def get_type_declaration_prefix(self):
        # type: () -> unicode
        return 'using'

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.type:
            signode += nodes.Text(' = ')
            self.type.describe_signature(signode, 'markType', env, symbol=symbol)


class ASTConcept(ASTBase):
    def __init__(self, nestedName, initializer):
        # type: (Any, Any) -> None
        self.nestedName = nestedName
        self.initializer = initializer

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.nestedName

    def get_id(self, version, objectType=None, symbol=None):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            raise NoOldIdError()
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = transform(self.nestedName)
        if self.initializer:
            res += transform(self.initializer)
        return res

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        self.nestedName.describe_signature(signode, mode, env, symbol)
        if self.initializer:
            self.initializer.describe_signature(signode, mode, env, symbol)


class ASTBaseClass(ASTBase):
    def __init__(self, name, visibility, virtual, pack):
        # type: (Any, unicode, bool, bool) -> None
        self.name = name
        self.visibility = visibility
        self.virtual = virtual
        self.pack = pack

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.visibility != 'private':
            res.append(self.visibility)
            res.append(' ')
        if self.virtual:
            res.append('virtual ')
        res.append(transform(self.name))
        if self.pack:
            res.append('...')
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        if self.visibility != 'private':
            signode += addnodes.desc_annotation(self.visibility,
                                                self.visibility)
            signode += nodes.Text(' ')
        if self.virtual:
            signode += addnodes.desc_annotation('virtual', 'virtual')
            signode += nodes.Text(' ')
        self.name.describe_signature(signode, 'markType', env, symbol=symbol)
        if self.pack:
            signode += nodes.Text('...')


class ASTClass(ASTBase):
    def __init__(self, name, final, bases):
        # type: (Any, bool, List[Any]) -> None
        self.name = name
        self.final = final
        self.bases = bases

    def get_id(self, version, objectType, symbol):
        # type: (int, unicode, Symbol) -> unicode
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = []
        res.append(transform(self.name))
        if self.final:
            res.append(' final')
        if len(self.bases) > 0:
            res.append(' : ')
            first = True
            for b in self.bases:
                if not first:
                    res.append(', ')
                first = False
                res.append(transform(b))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.final:
            signode += nodes.Text(' ')
            signode += addnodes.desc_annotation('final', 'final')
        if len(self.bases) > 0:
            signode += nodes.Text(' : ')
            for b in self.bases:
                b.describe_signature(signode, mode, env, symbol=symbol)
                signode += nodes.Text(', ')
            signode.pop()


class ASTUnion(ASTBase):
    def __init__(self, name):
        # type: (Any) -> None
        self.name = name

    def get_id(self, version, objectType, symbol):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            raise NoOldIdError()
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        return transform(self.name)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)


class ASTEnum(ASTBase):
    def __init__(self, name, scoped, underlyingType):
        # type: (Any, unicode, Any) -> None
        self.name = name
        self.scoped = scoped
        self.underlyingType = underlyingType

    def get_id(self, version, objectType, symbol):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            raise NoOldIdError()
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.scoped:
            res.append(self.scoped)
            res.append(' ')
        res.append(transform(self.name))
        if self.underlyingType:
            res.append(' : ')
            res.append(transform(self.underlyingType))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        # self.scoped has been done by the CPPEnumObject
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.underlyingType:
            signode += nodes.Text(' : ')
            self.underlyingType.describe_signature(signode, 'noneIsName',
                                                   env, symbol=symbol)


class ASTEnumerator(ASTBase):
    def __init__(self, name, init):
        # type: (Any, Any) -> None
        self.name = name
        self.init = init

    def get_id(self, version, objectType, symbol):
        # type: (int, unicode, Symbol) -> unicode
        if version == 1:
            raise NoOldIdError()
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform):
        res = []
        res.append(transform(self.name))
        if self.init:
            res.append(transform(self.init))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, symbol):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Symbol) -> None
        _verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol)
        if self.init:
            self.init.describe_signature(signode, 'markType', env, symbol)


class ASTDeclaration(ASTBase):
    def __init__(self, objectType, visibility, templatePrefix, declaration):
        # type: (unicode, unicode, Any, Any) -> None
        self.objectType = objectType
        self.visibility = visibility
        self.templatePrefix = templatePrefix
        self.declaration = declaration

        self.symbol = None  # type: Symbol
        # set by CPPObject._add_enumerator_to_parent
        self.enumeratorScopedSymbol = None  # type: Any

    def clone(self):
        # type: () -> ASTDeclaration
        if self.templatePrefix:
            templatePrefixClone = self.templatePrefix.clone()
        else:
            templatePrefixClone = None
        return ASTDeclaration(self.objectType, self.visibility,
                              templatePrefixClone,
                              self.declaration.clone())

    @property
    def name(self):
        # type: () -> ASTNestedName
        return self.declaration.name

    @property
    def function_params(self):
        # type: () -> Any
        if self.objectType != 'function':
            return None
        return self.declaration.function_params

    def get_id(self, version, prefixed=True):
        # type: (int, bool) -> unicode
        if version == 1:
            if self.templatePrefix:
                raise NoOldIdError()
            if self.objectType == 'enumerator' and self.enumeratorScopedSymbol:
                return self.enumeratorScopedSymbol.declaration.get_id(version)
            return self.declaration.get_id(version, self.objectType, self.symbol)
        # version >= 2
        if self.objectType == 'enumerator' and self.enumeratorScopedSymbol:
            return self.enumeratorScopedSymbol.declaration.get_id(version, prefixed)
        if prefixed:
            res = [_id_prefix[version]]
        else:
            res = []
        if self.templatePrefix:
            res.append(self.templatePrefix.get_id(version))
        res.append(self.declaration.get_id(version, self.objectType, self.symbol))
        return u''.join(res)

    def get_newest_id(self):
        # type: () -> unicode
        return self.get_id(_max_id, True)

    def _stringify(self, transform):
        res = []  # type: List[unicode]
        if self.visibility and self.visibility != "public":
            res.append(self.visibility)
            res.append(u' ')
        if self.templatePrefix:
            res.append(transform(self.templatePrefix))
        res.append(transform(self.declaration))
        return u''.join(res)

    def describe_signature(self, signode, mode, env, options):
        # type: (addnodes.desc_signature, unicode, BuildEnvironment, Dict) -> None
        _verify_description_mode(mode)
        assert self.symbol
        # The caller of the domain added a desc_signature node.
        # Always enable multiline:
        signode['is_multiline'] = True
        # Put each line in a desc_signature_line node.
        mainDeclNode = addnodes.desc_signature_line()
        mainDeclNode.sphinx_cpp_tagname = 'declarator'
        mainDeclNode['add_permalink'] = not self.symbol.isRedeclaration

        if self.templatePrefix:
            self.templatePrefix.describe_signature(signode, mode, env,
                                                   symbol=self.symbol,
                                                   lineSpec=options.get('tparam-line-spec'))
        signode += mainDeclNode
        if self.visibility and self.visibility != "public":
            mainDeclNode += addnodes.desc_annotation(self.visibility + " ",
                                                     self.visibility + " ")
        if self.objectType == 'type':
            prefix = self.declaration.get_type_declaration_prefix()
            prefix += ' '
            mainDeclNode += addnodes.desc_annotation(prefix, prefix)
        elif self.objectType == 'concept':
            mainDeclNode += addnodes.desc_annotation('concept ', 'concept ')
        elif self.objectType == 'member':
            pass
        elif self.objectType == 'function':
            pass
        elif self.objectType == 'class':
            mainDeclNode += addnodes.desc_annotation('class ', 'class ')
        elif self.objectType == 'union':
            mainDeclNode += addnodes.desc_annotation('union ', 'union ')
        elif self.objectType == 'enum':
            prefix = 'enum '
            if self.scoped:  # type: ignore
                prefix += self.scoped  # type: ignore
                prefix += ' '
            mainDeclNode += addnodes.desc_annotation(prefix, prefix)
        elif self.objectType == 'enumerator':
            mainDeclNode += addnodes.desc_annotation('enumerator ', 'enumerator ')
        else:
            assert False
        self.declaration.describe_signature(mainDeclNode, mode, env, self.symbol)


class ASTNamespace(ASTBase):
    def __init__(self, nestedName, templatePrefix):
        # type: (ASTNestedName, ASTTemplateDeclarationPrefix) -> None
        self.nestedName = nestedName
        self.templatePrefix = templatePrefix


class SymbolLookupResult(object):
    def __init__(self, symbols, parentSymbol, identOrOp, templateParams, templateArgs):
        # type: (Iterator[Symbol], Symbol, Union[ASTIdentifier, ASTOperator], Any, ASTTemplateArgs) -> None  # NOQA
        self.symbols = symbols
        self.parentSymbol = parentSymbol
        self.identOrOp = identOrOp
        self.templateParams = templateParams
        self.templateArgs = templateArgs


class Symbol(object):
    debug_lookup = False
    debug_show_tree = False

    def _assert_invariants(self):
        # type: () -> None
        if not self.parent:
            # parent == None means global scope, so declaration means a parent
            assert not self.identOrOp
            assert not self.templateParams
            assert not self.templateArgs
            assert not self.declaration
            assert not self.docname
        else:
            if self.declaration:
                assert self.docname

    def __setattr__(self, key, value):
        if key == "children":
            assert False
        else:
            return object.__setattr__(self, key, value)

    def __init__(self,
                 parent,          # type: Symbol
                 identOrOp,       # type: Union[ASTIdentifier, ASTOperator]
                 templateParams,  # type: Any
                 templateArgs,    # type: Any
                 declaration,     # type: ASTDeclaration
                 docname          # type: unicode
                 ):
        # type: (...) -> None
        self.parent = parent
        self.identOrOp = identOrOp
        self.templateParams = templateParams  # template<templateParams>
        self.templateArgs = templateArgs  # identifier<templateArgs>
        self.declaration = declaration
        self.docname = docname
        self.isRedeclaration = False
        self._assert_invariants()

        # Remember to modify Symbol.remove if modifications to the parent change.
        self._children = []  # type: List[Symbol]
        self._anonChildren = []  # type: List[Symbol]
        # note: _children includes _anonChildren
        if self.parent:
            self.parent._children.append(self)
        if self.declaration:
            self.declaration.symbol = self

        # Do symbol addition after self._children has been initialised.
        self._add_template_and_function_params()

    def _fill_empty(self, declaration, docname):
        # type: (ASTDeclaration, unicode) -> None
        self._assert_invariants()
        assert not self.declaration
        assert not self.docname
        assert declaration
        assert docname
        self.declaration = declaration
        self.declaration.symbol = self
        self.docname = docname
        self._assert_invariants()
        # and symbol addition should be done as well
        self._add_template_and_function_params()

    def _add_template_and_function_params(self):
        # Note: we may be called from _fill_empty, so the symbols we want
        #       to add may actually already be present (as empty symbols).

        # add symbols for the template params
        if self.templateParams:
            for p in self.templateParams.params:
                if not p.get_identifier():
                    continue
                # only add a declaration if we our self are from a declaration
                if self.declaration:
                    decl = ASTDeclaration('templateParam', None, None, p)
                else:
                    decl = None
                nne = ASTNestedNameElement(p.get_identifier(), None)
                nn = ASTNestedName([nne], [False], rooted=False)
                self._add_symbols(nn, [], decl, self.docname)
        # add symbols for function parameters, if any
        if self.declaration is not None and self.declaration.function_params is not None:
            for p in self.declaration.function_params:
                if p.arg is None:
                    continue
                nn = p.arg.name
                if nn is None:
                    continue
                # (comparing to the template params: we have checked that we are a declaration)
                decl = ASTDeclaration('functionParam', None, None, p)
                assert not nn.rooted
                assert len(nn.names) == 1
                self._add_symbols(nn, [], decl, self.docname)

    def remove(self):
        if self.parent is None:
            return
        assert self in self.parent._children
        self.parent._children.remove(self)
        self.parent = None

    def clear_doc(self, docname):
        # type: (unicode) -> None
        newChildren = []
        for sChild in self._children:
            sChild.clear_doc(docname)
            if sChild.declaration and sChild.docname == docname:
                sChild.declaration = None
                sChild.docname = None
            newChildren.append(sChild)
        self._children = newChildren

    def get_all_symbols(self):
        # type: () -> Iterator[Any]
        yield self
        for sChild in self._children:
            for s in sChild.get_all_symbols():
                yield s

    @property
    def children_recurse_anon(self):
        for c in self._children:
            yield c
            if not c.identOrOp.is_anon():
                continue
            # TODO: change to 'yield from' when Python 2 support is dropped
            for nested in c.children_recurse_anon:
                yield nested

    def get_lookup_key(self):
        # type: () -> List[Tuple[ASTNestedNameElement, Any]]
        symbols = []
        s = self
        while s.parent:
            symbols.append(s)
            s = s.parent
        symbols.reverse()
        key = []
        for s in symbols:
            nne = ASTNestedNameElement(s.identOrOp, s.templateArgs)
            key.append((nne, s.templateParams))
        return key

    def get_full_nested_name(self):
        # type: () -> ASTNestedName
        names = []
        templates = []
        for nne, templateParams in self.get_lookup_key():
            names.append(nne)
            templates.append(False)
        return ASTNestedName(names, templates, rooted=False)

    def _find_first_named_symbol(
            self,
            identOrOp,          # type: Union[ASTIdentifier, ASTOperator]
            templateParams,     # type: Any
            templateArgs,       # type: ASTTemplateArgs
            templateShorthand,  # type: bool
            matchSelf,          # type: bool
            recurseInAnon,      # type: bool
            correctPrimaryTemplateArgs  # type: bool
            ):  # NOQA
        # type: (...) -> Symbol
        res = self._find_named_symbols(identOrOp, templateParams, templateArgs,
                                       templateShorthand, matchSelf, recurseInAnon,
                                       correctPrimaryTemplateArgs)
        try:
            return next(res)
        except StopIteration:
            return None

    def _find_named_symbols(self,
                            identOrOp,          # type: Union[ASTIdentifier, ASTOperator]
                            templateParams,     # type: Any
                            templateArgs,       # type: ASTTemplateArgs
                            templateShorthand,  # type: bool
                            matchSelf,          # type: bool
                            recurseInAnon,      # type: bool
                            correctPrimaryTemplateArgs  # type: bool
                            ):
        # type: (...) -> Iterator[Symbol]

        def isSpecialization():
            # the names of the template parameters must be given exactly as args
            # and params that are packs must in the args be the name expanded
            if len(templateParams.params) != len(templateArgs.args):
                return True
            # having no template params and no arguments is also a specialization
            if len(templateParams.params) == 0:
                return True
            for i in range(len(templateParams.params)):
                param = templateParams.params[i]
                arg = templateArgs.args[i]
                # TODO: doing this by string manipulation is probably not the most efficient
                paramName = text_type(param.name)
                argTxt = text_type(arg)
                isArgPackExpansion = argTxt.endswith('...')
                if param.isPack != isArgPackExpansion:
                    return True
                argName = argTxt[:-3] if isArgPackExpansion else argTxt
                if paramName != argName:
                    return True
            return False
        if correctPrimaryTemplateArgs:
            if templateParams is not None and templateArgs is not None:
                # If both are given, but it's not a specialization, then do lookup as if
                # there is no argument list.
                # For example: template<typename T> int A<T>::var;
                if not isSpecialization():
                    templateArgs = None

        def matches(s):
            if s.identOrOp != identOrOp:
                return False
            if (s.templateParams is None) != (templateParams is None):
                if templateParams is not None:
                    # we query with params, they must match params
                    return False
                if not templateShorthand:
                    # we don't query with params, and we do care about them
                    return False
            if templateParams:
                # TODO: do better comparison
                if text_type(s.templateParams) != text_type(templateParams):
                    return False
            if (s.templateArgs is None) != (templateArgs is None):
                return False
            if s.templateArgs:
                # TODO: do better comparison
                if text_type(s.templateArgs) != text_type(templateArgs):
                    return False
            return True
        if matchSelf and matches(self):
            yield self
        children = self.children_recurse_anon if recurseInAnon else self._children
        for s in children:
            if matches(s):
                yield s

    def _symbol_lookup(
            self,
            nestedName,                   # type: ASTNestedName
            templateDecls,                # type: List[Any]
            onMissingQualifiedSymbol,
            # type: Callable[[Symbol, Union[ASTIdentifier, ASTOperator], Any, ASTTemplateArgs], Symbol]  # NOQA
            strictTemplateParamArgLists,  # type: bool
            ancestorLookupType,           # type: unicode
            templateShorthand,            # type: bool
            matchSelf,                    # type: bool
            recurseInAnon,                # type: bool
            correctPrimaryTemplateArgs    # type: bool
            ):
        # type: (...) -> SymbolLookupResult
        # ancestorLookupType: if not None, specifies the target type of the lookup

        if strictTemplateParamArgLists:
            # Each template argument list must have a template parameter list.
            # But to declare a template there must be an additional template parameter list.
            assert (nestedName.num_templates() == len(templateDecls) or
                    nestedName.num_templates() + 1 == len(templateDecls))
        else:
            assert len(templateDecls) <= nestedName.num_templates() + 1

        names = nestedName.names

        # find the right starting point for lookup
        parentSymbol = self
        if nestedName.rooted:
            while parentSymbol.parent:
                parentSymbol = parentSymbol.parent
        if ancestorLookupType is not None:
            # walk up until we find the first identifier
            firstName = names[0]
            if not firstName.is_operator():
                while parentSymbol.parent:
                    if parentSymbol.find_identifier(firstName.identOrOp,
                                                    matchSelf=matchSelf,
                                                    recurseInAnon=recurseInAnon):
                        # if we are in the scope of a constructor but wants to
                        # reference the class we need to walk one extra up
                        if (len(names) == 1 and ancestorLookupType == 'class' and matchSelf and
                                parentSymbol.parent and
                                parentSymbol.parent.identOrOp == firstName.identOrOp):
                            pass
                        else:
                            break
                    parentSymbol = parentSymbol.parent

        # and now the actual lookup
        iTemplateDecl = 0
        for name in names[:-1]:
            identOrOp = name.identOrOp
            templateArgs = name.templateArgs
            if strictTemplateParamArgLists:
                # there must be a parameter list
                if templateArgs:
                    assert iTemplateDecl < len(templateDecls)
                    templateParams = templateDecls[iTemplateDecl]
                    iTemplateDecl += 1
                else:
                    templateParams = None
            else:
                # take the next template parameter list if there is one
                # otherwise it's ok
                if templateArgs and iTemplateDecl < len(templateDecls):
                    templateParams = templateDecls[iTemplateDecl]
                    iTemplateDecl += 1
                else:
                    templateParams = None

            symbol = parentSymbol._find_first_named_symbol(
                identOrOp,
                templateParams, templateArgs,
                templateShorthand=templateShorthand,
                matchSelf=matchSelf,
                recurseInAnon=recurseInAnon,
                correctPrimaryTemplateArgs=correctPrimaryTemplateArgs)
            if symbol is None:
                symbol = onMissingQualifiedSymbol(parentSymbol, identOrOp,
                                                  templateParams, templateArgs)
                if symbol is None:
                    return None
            # We have now matched part of a nested name, and need to match more
            # so even if we should matchSelf before, we definitely shouldn't
            # even more. (see also issue #2666)
            matchSelf = False
            parentSymbol = symbol

        # handle the last name
        name = names[-1]
        identOrOp = name.identOrOp
        templateArgs = name.templateArgs
        if iTemplateDecl < len(templateDecls):
            assert iTemplateDecl + 1 == len(templateDecls)
            templateParams = templateDecls[iTemplateDecl]
        else:
            assert iTemplateDecl == len(templateDecls)
            templateParams = None

        symbols = parentSymbol._find_named_symbols(
            identOrOp, templateParams, templateArgs,
            templateShorthand=templateShorthand, matchSelf=matchSelf,
            recurseInAnon=recurseInAnon, correctPrimaryTemplateArgs=False)
        return SymbolLookupResult(symbols, parentSymbol,
                                  identOrOp, templateParams, templateArgs)

    def _add_symbols(self, nestedName, templateDecls, declaration, docname):
        # type: (ASTNestedName, List[Any], ASTDeclaration, unicode) -> Symbol
        # Used for adding a whole path of symbols, where the last may or may not
        # be an actual declaration.

        if Symbol.debug_lookup:
            print("_add_symbols:")
            print("   tdecls:", templateDecls)
            print("   nn:    ", nestedName)
            print("   decl:  ", declaration)
            print("   doc:   ", docname)

        def onMissingQualifiedSymbol(parentSymbol, identOrOp, templateParams, templateArgs):
            # type: (Symbol, Union[ASTIdentifier, ASTOperator], Any, ASTTemplateArgs) -> Symbol
            if Symbol.debug_lookup:
                print("   _add_symbols, onMissingQualifiedSymbol:")
                print("      templateParams:", templateParams)
                print("      identOrOp:     ", identOrOp)
                print("      templateARgs:  ", templateArgs)
            return Symbol(parent=parentSymbol, identOrOp=identOrOp,
                          templateParams=templateParams,
                          templateArgs=templateArgs, declaration=None,
                          docname=None)

        lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                           onMissingQualifiedSymbol,
                                           strictTemplateParamArgLists=True,
                                           ancestorLookupType=None,
                                           templateShorthand=False,
                                           matchSelf=False,
                                           recurseInAnon=True,
                                           correctPrimaryTemplateArgs=True)
        assert lookupResult is not None  # we create symbols all the way, so that can't happen
        symbols = list(lookupResult.symbols)
        if len(symbols) == 0:
            if Symbol.debug_lookup:
                print("   _add_symbols, result, no symbol:")
                print("      templateParams:", lookupResult.templateParams)
                print("      identOrOp:     ", lookupResult.identOrOp)
                print("      templateArgs:  ", lookupResult.templateArgs)
                print("      declaration:   ", declaration)
                print("      docname:       ", docname)
            symbol = Symbol(parent=lookupResult.parentSymbol,
                            identOrOp=lookupResult.identOrOp,
                            templateParams=lookupResult.templateParams,
                            templateArgs=lookupResult.templateArgs,
                            declaration=declaration,
                            docname=docname)
            return symbol

        if Symbol.debug_lookup:
            print("   _add_symbols, result, symbols:")
            print("      number symbols:", len(symbols))

        if not declaration:
            if Symbol.debug_lookup:
                print("      no delcaration")
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
            print("      #noDecl:  ", len(noDecl))
            print("      #withDecl:", len(withDecl))
            print("      #dupDecl: ", len(dupDecl))
        # With partial builds we may start with a large symbol tree stripped of declarations.
        # Essentially any combination of noDecl, withDecl, and dupDecls seems possible.
        # TODO: make partial builds fully work. What should happen when the primary symbol gets
        #  deleted, and other duplicates exist? The full document should probably be rebuild.

        # First check if one of those with a declaration matches.
        # If it's a function, we need to compare IDs,
        # otherwise there should be only one symbol with a declaration.
        def makeCandSymbol():
            if Symbol.debug_lookup:
                print("      begin: creating candidate symbol")
            symbol = Symbol(parent=lookupResult.parentSymbol,
                            identOrOp=lookupResult.identOrOp,
                            templateParams=lookupResult.templateParams,
                            templateArgs=lookupResult.templateArgs,
                            declaration=declaration,
                            docname=docname)
            if Symbol.debug_lookup:
                print("      end:   creating candidate symbol")
            return symbol
        if len(withDecl) == 0:
            candSymbol = None
        else:
            candSymbol = makeCandSymbol()

            def handleDuplicateDeclaration(symbol, candSymbol):
                if Symbol.debug_lookup:
                    print("      redeclaration")
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
                print("      candId:", candId)
            for symbol in withDecl:
                oldId = symbol.declaration.get_newest_id()
                if Symbol.debug_lookup:
                    print("      oldId: ", oldId)
                if candId == oldId:
                    handleDuplicateDeclaration(symbol, candSymbol)
                    # (not reachable)
            # no candidate symbol found with matching ID
        # if there is an empty symbol, fill that one
        if len(noDecl) == 0:
            if Symbol.debug_lookup:
                print("      no match, no empty, candSybmol is not None?:", candSymbol is not None)  # NOQA
            if candSymbol is not None:
                return candSymbol
            else:
                return makeCandSymbol()
        else:
            if Symbol.debug_lookup:
                print("      no match, but fill an empty declaration, candSybmol is not None?:", candSymbol is not None)  # NOQA
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
            symbol._fill_empty(declaration, docname)
            return symbol

    def merge_with(self, other, docnames, env):
        # type: (Symbol, List[unicode], BuildEnvironment) -> None
        assert other is not None
        for otherChild in other._children:
            ourChild = self._find_first_named_symbol(
                identOrOp=otherChild.identOrOp,
                templateParams=otherChild.templateParams,
                templateArgs=otherChild.templateArgs,
                templateShorthand=False, matchSelf=False,
                recurseInAnon=False, correctPrimaryTemplateArgs=False)
            if ourChild is None:
                # TODO: hmm, should we prune by docnames?
                self._children.append(otherChild)
                otherChild.parent = self
                otherChild._assert_invariants()
                continue
            if otherChild.declaration and otherChild.docname in docnames:
                if not ourChild.declaration:
                    ourChild._fill_empty(otherChild.declaration, otherChild.docname)
                elif ourChild.docname != otherChild.docname:
                    name = text_type(ourChild.declaration)
                    msg = __("Duplicate declaration, also defined in '%s'.\n"
                             "Declaration is '%s'.")
                    msg = msg % (ourChild.docname, name)
                    logger.warning(msg, location=otherChild.docname)
                else:
                    # Both have declarations, and in the same docname.
                    # This can apparently happen, it should be safe to
                    # just ignore it, right?
                    pass
            ourChild.merge_with(otherChild, docnames, env)

    def add_name(self, nestedName, templatePrefix=None):
        # type: (ASTNestedName, ASTTemplateDeclarationPrefix) -> Symbol
        if templatePrefix:
            templateDecls = templatePrefix.templates
        else:
            templateDecls = []
        return self._add_symbols(nestedName, templateDecls,
                                 declaration=None, docname=None)

    def add_declaration(self, declaration, docname):
        # type: (ASTDeclaration, unicode) -> Symbol
        assert declaration
        assert docname
        nestedName = declaration.name
        if declaration.templatePrefix:
            templateDecls = declaration.templatePrefix.templates
        else:
            templateDecls = []
        return self._add_symbols(nestedName, templateDecls, declaration, docname)

    def find_identifier(self, identOrOp, matchSelf, recurseInAnon):
        # type: (Union[ASTIdentifier, ASTOperator], bool, bool) -> Symbol
        if matchSelf and self.identOrOp == identOrOp:
            return self
        children = self.children_recurse_anon if recurseInAnon else self._children
        for s in children:
            if s.identOrOp == identOrOp:
                return s
        return None

    def direct_lookup(self, key):
        # type: (List[Tuple[ASTNestedNameElement, Any]]) -> Symbol
        s = self
        for name, templateParams in key:
            identOrOp = name.identOrOp
            templateArgs = name.templateArgs
            s = s._find_first_named_symbol(identOrOp,
                                           templateParams, templateArgs,
                                           templateShorthand=False,
                                           matchSelf=False,
                                           recurseInAnon=False,
                                           correctPrimaryTemplateArgs=False)
            if not s:
                return None
        return s

    def find_name(self, nestedName, templateDecls, typ, templateShorthand,
                  matchSelf, recurseInAnon):
        # type: (ASTNestedName, List[Any], unicode, bool, bool, bool) -> Symbol
        # templateShorthand: missing template parameter lists for templates is ok

        def onMissingQualifiedSymbol(parentSymbol, identOrOp, templateParams, templateArgs):
            # type: (Symbol, Union[ASTIdentifier, ASTOperator], Any, ASTTemplateArgs) -> Symbol
            # TODO: Maybe search without template args?
            #       Though, the correctPrimaryTemplateArgs does
            #       that for primary templates.
            #       Is there another case where it would be good?
            return None

        lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                           onMissingQualifiedSymbol,
                                           strictTemplateParamArgLists=False,
                                           ancestorLookupType=typ,
                                           templateShorthand=templateShorthand,
                                           matchSelf=matchSelf,
                                           recurseInAnon=recurseInAnon,
                                           correctPrimaryTemplateArgs=False)
        if lookupResult is None:
            # if it was a part of the qualification that could not be found
            return None

        # TODO: hmm, what if multiple symbols match?
        try:
            return next(lookupResult.symbols)
        except StopIteration:
            pass

        # try without template params and args
        symbol = lookupResult.parentSymbol._find_first_named_symbol(
            lookupResult.identOrOp, None, None,
            templateShorthand=templateShorthand, matchSelf=matchSelf,
            recurseInAnon=recurseInAnon, correctPrimaryTemplateArgs=False)
        return symbol

    def find_declaration(self, declaration, typ, templateShorthand,
                         matchSelf, recurseInAnon):
        # type: (ASTDeclaration, unicode, bool, bool, bool) -> Symbol
        # templateShorthand: missing template parameter lists for templates is ok
        nestedName = declaration.name
        if declaration.templatePrefix:
            templateDecls = declaration.templatePrefix.templates
        else:
            templateDecls = []

        def onMissingQualifiedSymbol(parentSymbol, identOrOp, templateParams, templateArgs):
            # type: (Symbol, Union[ASTIdentifier, ASTOperator], Any, ASTTemplateArgs) -> Symbol
            return None

        lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                           onMissingQualifiedSymbol,
                                           strictTemplateParamArgLists=False,
                                           ancestorLookupType=typ,
                                           templateShorthand=templateShorthand,
                                           matchSelf=matchSelf,
                                           recurseInAnon=recurseInAnon,
                                           correctPrimaryTemplateArgs=False)

        if lookupResult is None:
            return None

        symbols = list(lookupResult.symbols)
        if len(symbols) == 0:
            return None

        querySymbol = Symbol(parent=lookupResult.parentSymbol,
                             identOrOp=lookupResult.identOrOp,
                             templateParams=lookupResult.templateParams,
                             templateArgs=lookupResult.templateArgs,
                             declaration=declaration,
                             docname='fakeDocnameForQuery')
        queryId = declaration.get_newest_id()
        for symbol in symbols:
            candId = symbol.declaration.get_newest_id()
            if candId == queryId:
                querySymbol.remove()
                return symbol
        querySymbol.remove()
        return None

    def to_string(self, indent):
        # type: (int) -> unicode
        res = ['\t' * indent]  # type: List[unicode]
        if not self.parent:
            res.append('::')
        else:
            if self.templateParams:
                res.append(text_type(self.templateParams))
                res.append('\n')
                res.append('\t' * indent)
            if self.identOrOp:
                res.append(text_type(self.identOrOp))
            else:
                res.append(text_type(self.declaration))
            if self.templateArgs:
                res.append(text_type(self.templateArgs))
            if self.declaration:
                res.append(": ")
                if self.isRedeclaration:
                    res.append('!!duplicate!! ')
                res.append(text_type(self.declaration))
        if self.docname:
            res.append('\t(')
            res.append(self.docname)
            res.append(')')
        res.append('\n')
        return ''.join(res)

    def dump(self, indent):
        # type: (int) -> unicode
        res = [self.to_string(indent)]
        for c in self._children:
            res.append(c.dump(indent + 1))
        return ''.join(res)


class DefinitionParser(object):
    # those without signedness and size modifiers
    # see http://en.cppreference.com/w/cpp/language/types
    _simple_fundemental_types = (
        'void', 'bool', 'char', 'wchar_t', 'char16_t', 'char32_t', 'int',
        'float', 'double', 'auto'
    )

    _prefix_keys = ('class', 'struct', 'enum', 'union', 'typename')

    def __init__(self, definition, warnEnv, config):
        # type: (Any, Any, Config) -> None
        self.definition = definition.strip()
        self.pos = 0
        self.end = len(self.definition)
        self.last_match = None  # type: Match
        self._previous_state = (0, None)  # type: Tuple[int, Match]
        self.otherErrors = []  # type: List[DefinitionError]
        # in our tests the following is set to False to capture bad parsing
        self.allowFallbackExpressionParsing = True

        self.warnEnv = warnEnv
        self.config = config

    def _make_multi_error(self, errors, header):
        # type: (List[Any], unicode) -> DefinitionError
        if len(errors) == 1:
            if len(header) > 0:
                return DefinitionError(header + '\n' + errors[0][0].description)
            else:
                return DefinitionError(errors[0][0].description)
        result = [header, '\n']
        for e in errors:
            if len(e[1]) > 0:
                ident = '  '
                result.append(e[1])
                result.append(':\n')
                for line in e[0].description.split('\n'):
                    if len(line) == 0:
                        continue
                    result.append(ident)
                    result.append(line)
                    result.append('\n')
            else:
                result.append(e[0].description)
        return DefinitionError(''.join(result))

    def status(self, msg):
        # type: (unicode) -> None
        # for debugging
        indicator = '-' * self.pos + '^'
        print("%s\n%s\n%s" % (msg, self.definition, indicator))

    def fail(self, msg):
        # type: (unicode) -> None
        errors = []
        indicator = '-' * self.pos + '^'
        exMain = DefinitionError(
            'Invalid definition: %s [error at %d]\n  %s\n  %s' %
            (msg, self.pos, self.definition, indicator))
        errors.append((exMain, "Main error"))
        for err in self.otherErrors:
            errors.append((err, "Potential other error"))
        self.otherErrors = []
        raise self._make_multi_error(errors, '')

    def warn(self, msg):
        # type: (unicode) -> None
        if self.warnEnv:
            self.warnEnv.warn(msg)
        else:
            print("Warning: %s" % msg)

    def match(self, regex):
        # type: (Pattern) -> bool
        match = regex.match(self.definition, self.pos)
        if match is not None:
            self._previous_state = (self.pos, self.last_match)
            self.pos = match.end()
            self.last_match = match
            return True
        return False

    def backout(self):
        # type: () -> None
        self.pos, self.last_match = self._previous_state

    def skip_string(self, string):
        # type: (unicode) -> bool
        strlen = len(string)
        if self.definition[self.pos:self.pos + strlen] == string:
            self.pos += strlen
            return True
        return False

    def skip_word(self, word):
        # type: (unicode) -> bool
        return self.match(re.compile(r'\b%s\b' % re.escape(word)))

    def skip_ws(self):
        # type: () -> bool
        return self.match(_whitespace_re)

    def skip_word_and_ws(self, word):
        # type: (unicode) -> bool
        if self.skip_word(word):
            self.skip_ws()
            return True
        return False

    def skip_string_and_ws(self, string):
        # type: (unicode) -> bool
        if self.skip_string(string):
            self.skip_ws()
            return True
        return False

    @property
    def eof(self):
        # type: () -> bool
        return self.pos >= self.end

    @property
    def current_char(self):
        # type: () -> unicode
        try:
            return self.definition[self.pos]
        except IndexError:
            return 'EOF'

    @property
    def matched_text(self):
        # type: () -> unicode
        if self.last_match is not None:
            return self.last_match.group()
        else:
            return None

    def read_rest(self):
        # type: () -> unicode
        rv = self.definition[self.pos:]
        self.pos = self.end
        return rv

    def assert_end(self):
        # type: () -> None
        self.skip_ws()
        if not self.eof:
            self.fail('Expected end of definition.')

    def _parse_string(self):
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

    def _parse_balanced_token_seq(self, end):
        # type: (List[unicode]) -> unicode
        # TODO: add handling of string literals and similar
        brackets = {'(': ')', '[': ']', '{': '}'}  # type: Dict[unicode, unicode]
        startPos = self.pos
        symbols = []  # type: List[unicode]
        while not self.eof:
            if len(symbols) == 0 and self.current_char in end:
                break
            if self.current_char in brackets.keys():
                symbols.append(brackets[self.current_char])
            elif len(symbols) > 0 and self.current_char == symbols[-1]:
                symbols.pop()
            elif self.current_char in ")]}":
                self.fail("Unexpected '%s' in balanced-token-seq." % self.current_char)
            self.pos += 1
        if self.eof:
            self.fail("Could not find end of balanced-token-seq starting at %d."
                      % startPos)
        return self.definition[startPos:self.pos]

    def _parse_attribute(self):
        # type: () -> Any
        self.skip_ws()
        # try C++11 style
        startPos = self.pos
        if self.skip_string_and_ws('['):
            if not self.skip_string('['):
                self.pos = startPos
            else:
                # TODO: actually implement the correct grammar
                arg = self._parse_balanced_token_seq(end=[']'])
                if not self.skip_string_and_ws(']'):
                    self.fail("Expected ']' in end of attribute.")
                if not self.skip_string_and_ws(']'):
                    self.fail("Expected ']' in end of attribute after [[...]")
                return ASTCPPAttribute(arg)

        # try GNU style
        if self.skip_word_and_ws('__attribute__'):
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after '__attribute__'.")
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after '__attribute__('.")
            attrs = []
            while 1:
                if self.match(_identifier_re):
                    name = self.matched_text
                    self.skip_ws()
                    if self.skip_string_and_ws('('):
                        self.fail('Parameterized GNU style attribute not yet supported.')
                    attrs.append(ASTGnuAttribute(name, None))
                    # TODO: parse arguments for the attribute
                if self.skip_string_and_ws(','):
                    continue
                elif self.skip_string_and_ws(')'):
                    break
                else:
                    self.fail("Expected identifier, ')', or ',' in __attribute__.")
            if not self.skip_string_and_ws(')'):
                self.fail("Expected ')' after '__attribute__((...)'")
            return ASTGnuAttributeList(attrs)

        # try the simple id attributes defined by the user
        for id in self.config.cpp_id_attributes:
            if self.skip_word_and_ws(id):
                return ASTIdAttribute(id)

        # try the paren attributes defined by the user
        for id in self.config.cpp_paren_attributes:
            if not self.skip_string_and_ws(id):
                continue
            if not self.skip_string('('):
                self.fail("Expected '(' after user-defined paren-attribute.")
            arg = self._parse_balanced_token_seq(end=[')'])
            if not self.skip_string(')'):
                self.fail("Expected ')' to end user-defined paren-attribute.")
            return ASTParenAttribute(id, arg)

        return None

    def _parse_literal(self):
        # -> integer-literal
        #  | character-literal
        #  | floating-literal
        #  | string-literal
        #  | boolean-literal -> "false" | "true"
        #  | pointer-literal -> "nullptr"
        #  | user-defined-literal
        self.skip_ws()
        if self.skip_word('nullptr'):
            return ASTPointerLiteral()
        if self.skip_word('true'):
            return ASTBooleanLiteral(True)
        if self.skip_word('false'):
            return ASTBooleanLiteral(False)
        for regex in [_float_literal_re, _binary_literal_re, _hex_literal_re,
                      _integer_literal_re, _octal_literal_re]:
            pos = self.pos
            if self.match(regex):
                while self.current_char in 'uUlLfF':
                    self.pos += 1
                return ASTNumberLiteral(self.definition[pos:self.pos])

        string = self._parse_string()
        if string is not None:
            return ASTStringLiteral(string)

        # character-literal
        if self.match(_char_literal_re):
            prefix = self.last_match.group(1)  # may be None when no prefix
            data = self.last_match.group(2)
            try:
                return ASTCharLiteral(prefix, data)
            except UnicodeDecodeError as e:
                self.fail("Can not handle character literal. Internal error was: %s" % e)
            except UnsupportedMultiCharacterCharLiteral:
                self.fail("Can not handle character literal"
                          " resulting in multiple decoded characters.")

        # TODO: user-defined lit
        return None

    def _parse_fold_or_paren_expression(self):
        # "(" expression ")"
        # fold-expression
        # -> ( cast-expression fold-operator ... )
        #  | ( ... fold-operator cast-expression )
        #  | ( cast-expression fold-operator ... fold-operator cast-expression
        if self.current_char != '(':
            return None
        self.pos += 1
        self.skip_ws()
        if self.skip_string_and_ws("..."):
            # ( ... fold-operator cast-expression )
            if not self.match(_fold_operator_re):
                self.fail("Expected fold operator after '...' in fold expression.")
            op = self.matched_text
            rightExpr = self._parse_cast_expression()
            if not self.skip_string(')'):
                self.fail("Expected ')' in end of fold expression.")
            return ASTFoldExpr(None, op, rightExpr)
        # try first parsing a unary right fold, or a binary fold
        pos = self.pos
        try:
            self.skip_ws()
            leftExpr = self._parse_cast_expression()
            self.skip_ws()
            if not self.match(_fold_operator_re):
                self.fail("Expected fold operator after left expression in fold expression.")
            op = self.matched_text
            self.skip_ws()
            if not self.skip_string_and_ws('...'):
                self.fail("Expected '...' after fold operator in fold expression.")
        except DefinitionError as eFold:
            self.pos = pos
            # fall back to a paren expression
            try:
                res = self._parse_expression(inTemplate=False)
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail("Expected ')' in end of parenthesized expression.")
            except DefinitionError as eExpr:
                raise self._make_multi_error([
                    (eFold, "If fold expression"),
                    (eExpr, "If parenthesized expression")
                ], "Error in fold expression or parenthesized expression.")
            return ASTParenExpr(res)
        # now it definitely is a fold expression
        if self.skip_string(')'):
            return ASTFoldExpr(leftExpr, op, None)
        if not self.match(_fold_operator_re):
            self.fail("Expected fold operator or ')' after '...' in fold expression.")
        if op != self.matched_text:
            self.fail("Operators are different in binary fold: '%s' and '%s'."
                      % (op, self.matched_text))
        rightExpr = self._parse_cast_expression()
        self.skip_ws()
        if not self.skip_string(')'):
            self.fail("Expected ')' to end binary fold expression.")
        return ASTFoldExpr(leftExpr, op, rightExpr)

    def _parse_primary_expression(self):
        # literal
        # "this"
        # lambda-expression
        # "(" expression ")"
        # fold-expression
        # id-expression -> we parse this with _parse_nested_name
        self.skip_ws()
        res = self._parse_literal()
        if res is not None:
            return res
        self.skip_ws()
        if self.skip_word("this"):
            return ASTThisLiteral()
        # TODO: try lambda expression
        res = self._parse_fold_or_paren_expression()
        if res is not None:
            return res
        return self._parse_nested_name()

    def _parse_expression_list_or_braced_init_list(self):
        # type: () -> Tuple[List[Any], unicode]
        self.skip_ws()
        if self.skip_string_and_ws('('):
            close = ')'
            name = 'parenthesized expression-list'
        elif self.skip_string_and_ws('{'):
            close = '}'
            name = 'braced-init-list'
            self.fail('Sorry, braced-init-list not yet supported.')
        else:
            return None, None
        exprs = []
        self.skip_ws()
        if not self.skip_string(close):
            while True:
                self.skip_ws()
                expr = self._parse_expression(inTemplate=False)
                self.skip_ws()
                if self.skip_string('...'):
                    exprs.append(ASTPackExpansionExpr(expr))
                else:
                    exprs.append(expr)
                self.skip_ws()
                if self.skip_string(close):
                    break
                if not self.skip_string(','):
                    self.fail("Error in %s, expected ',' or '%s'." % (name, close))
        return exprs, close

    def _parse_postfix_expression(self):
        # -> primary
        #  | postfix "[" expression "]"
        #  | postfix "[" braced-init-list [opt] "]"
        #  | postfix "(" expression-list [opt] ")"
        #  | postfix "." "template" [opt] id-expression
        #  | postfix "->" "template" [opt] id-expression
        #  | postfix "." pseudo-destructor-name
        #  | postfix "->" pseudo-destructor-name
        #  | postfix "++"
        #  | postfix "--"
        #  | simple-type-specifier "(" expression-list [opt] ")"
        #  | simple-type-specifier braced-init-list
        #  | typename-specifier "(" expression-list [opt] ")"
        #  | typename-specifier braced-init-list
        #  | "dynamic_cast" "<" type-id ">" "(" expression ")"
        #  | "static_cast" "<" type-id ">" "(" expression ")"
        #  | "reinterpret_cast" "<" type-id ">" "(" expression ")"
        #  | "const_cast" "<" type-id ">" "(" expression ")"
        #  | "typeid" "(" expression ")"
        #  | "typeid" "(" type-id ")"

        prefixType = None
        prefix = None  # type: Any
        self.skip_ws()

        cast = None
        for c in _id_explicit_cast:
            if self.skip_word_and_ws(c):
                cast = c
                break
        if cast is not None:
            prefixType = "cast"
            if not self.skip_string("<"):
                self.fail("Expected '<' afer '%s'." % cast)
            typ = self._parse_type(False)
            self.skip_ws()
            if not self.skip_string_and_ws(">"):
                self.fail("Expected '>' after type in '%s'." % cast)
            if not self.skip_string("("):
                self.fail("Expected '(' in '%s'." % cast)

            def parser():
                return self._parse_expression(inTemplate=False)
            expr = self._parse_expression_fallback([')'], parser)
            self.skip_ws()
            if not self.skip_string(")"):
                self.fail("Expected ')' to end '%s'." % cast)
            prefix = ASTExplicitCast(cast, typ, expr)
        elif self.skip_word_and_ws("typeid"):
            prefixType = "typeid"
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after 'typeid'.")
            pos = self.pos
            try:
                typ = self._parse_type(False)
                prefix = ASTTypeId(typ, isType=True)
                if not self.skip_string(')'):
                    self.fail("Expected ')' to end 'typeid' of type.")
            except DefinitionError as eType:
                self.pos = pos
                try:

                    def parser():
                        return self._parse_expression(inTemplate=False)
                    expr = self._parse_expression_fallback([')'], parser)
                    prefix = ASTTypeId(expr, isType=False)
                    if not self.skip_string(')'):
                        self.fail("Expected ')' to end 'typeid' of expression.")
                except DefinitionError as eExpr:
                    self.pos = pos
                    header = "Error in 'typeid(...)'."
                    header += " Expected type or expression."
                    errors = []
                    errors.append((eType, "If type"))
                    errors.append((eExpr, "If expression"))
                    raise self._make_multi_error(errors, header)
        else:  # a primary expression or a type
            pos = self.pos
            try:
                prefix = self._parse_primary_expression()
                prefixType = 'expr'
            except DefinitionError as eOuter:
                self.pos = pos
                try:
                    # we are potentially casting, so save parens for us
                    # TODO: hmm, would we need to try both with operatorCast and with None?
                    prefix = self._parse_type(False, 'operatorCast')
                    prefixType = 'typeOperatorCast'
                    #  | simple-type-specifier "(" expression-list [opt] ")"
                    #  | simple-type-specifier braced-init-list
                    #  | typename-specifier "(" expression-list [opt] ")"
                    #  | typename-specifier braced-init-list
                    self.skip_ws()
                    if self.current_char != '(' and self.current_char != '{':
                        self.fail("Expecting '(' or '{' after type in cast expression.")
                except DefinitionError as eInner:
                    self.pos = pos
                    header = "Error in postfix expression,"
                    header += " expected primary expression or type."
                    errors = []
                    errors.append((eOuter, "If primary expression"))
                    errors.append((eInner, "If type"))
                    raise self._make_multi_error(errors, header)

        # and now parse postfixes
        postFixes = []
        while True:
            self.skip_ws()
            if prefixType in ['expr', 'cast', 'typeid']:
                if self.skip_string_and_ws('['):
                    expr = self._parse_expression(inTemplate=False)
                    self.skip_ws()
                    if not self.skip_string(']'):
                        self.fail("Expected ']' in end of postfix expression.")
                    postFixes.append(ASTPostfixArray(expr))
                    continue
                if self.skip_string('.'):
                    if self.skip_string('*'):
                        # don't steal the dot
                        self.pos -= 2
                    elif self.skip_string('..'):
                        # don't steal the dot
                        self.pos -= 3
                    else:
                        name = self._parse_nested_name()
                        postFixes.append(ASTPostfixMember(name))  # type: ignore
                        continue
                if self.skip_string('->'):
                    if self.skip_string('*'):
                        # don't steal the arrow
                        self.pos -= 3
                    else:
                        name = self._parse_nested_name()
                        postFixes.append(ASTPostfixMemberOfPointer(name))  # type: ignore
                        continue
                if self.skip_string('++'):
                    postFixes.append(ASTPostfixInc())  # type: ignore
                    continue
                if self.skip_string('--'):
                    postFixes.append(ASTPostfixDec())  # type: ignore
                    continue
            lst, typ = self._parse_expression_list_or_braced_init_list()
            if lst is not None:
                if typ == ')':
                    postFixes.append(ASTPostfixCallExpr(lst))  # type: ignore
                else:
                    assert typ == '}'
                    assert False
                continue
            break
        if len(postFixes) == 0:
            return prefix
        else:
            return ASTPostfixExpr(prefix, postFixes)

    def _parse_unary_expression(self):
        # -> postfix
        #  | "++" cast
        #  | "--" cast
        #  | unary-operator cast -> (* | & | + | - | ! | ~) cast
        # The rest:
        #  | "sizeof" unary
        #  | "sizeof" "(" type-id ")"
        #  | "sizeof" "..." "(" identifier ")"
        #  | "alignof" "(" type-id ")"
        #  | noexcept-expression -> noexcept "(" expression ")"
        #  | new-expression
        #  | delete-expression
        self.skip_ws()
        for op in _expression_unary_ops:
            # TODO: hmm, should we be able to backtrack here?
            if self.skip_string(op):
                expr = self._parse_cast_expression()
                return ASTUnaryOpExpr(op, expr)
        if self.skip_word_and_ws('sizeof'):
            if self.skip_string_and_ws('...'):
                if not self.skip_string_and_ws('('):
                    self.fail("Expecting '(' after 'sizeof...'.")
                if not self.match(_identifier_re):
                    self.fail("Expecting identifier for 'sizeof...'.")
                ident = ASTIdentifier(self.matched_text)
                self.skip_ws()
                if not self.skip_string(")"):
                    self.fail("Expecting ')' to end 'sizeof...'.")
                return ASTSizeofParamPack(ident)
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
        if self.skip_word_and_ws('noexcept'):
            if not self.skip_string_and_ws('('):
                self.fail("Expecting '(' after 'noexcept'.")
            expr = self._parse_expression(inTemplate=False)
            self.skip_ws()
            if not self.skip_string(')'):
                self.fail("Expecting ')' to end 'noexcept'.")
            return ASTNoexceptExpr(expr)
        # new-expression
        pos = self.pos
        rooted = self.skip_string('::')
        self.skip_ws()
        if not self.skip_word_and_ws('new'):
            self.pos = pos
        else:
            # new-placement[opt] new-type-id new-initializer[opt]
            # new-placement[opt] ( type-id ) new-initializer[opt]
            isNewTypeId = True
            if self.skip_string_and_ws('('):
                # either this is a new-placement or it's the second production
                # without placement, and it's actually the ( type-id ) part
                self.fail("Sorry, neither new-placement nor parenthesised type-id "
                          "in new-epression is supported yet.")
                # set isNewTypeId = False if it's (type-id)
            if isNewTypeId:
                declSpecs = self._parse_decl_specs(outer=None)
                decl = self._parse_declarator(named=False, paramMode="new")
            else:
                self.fail("Sorry, parenthesised type-id in new expression not yet supported.")
            lst, typ = self._parse_expression_list_or_braced_init_list()
            if lst:
                assert typ in ")}"
            return ASTNewExpr(rooted, isNewTypeId, ASTType(declSpecs, decl), lst, typ)
        # delete-expression
        pos = self.pos
        rooted = self.skip_string('::')
        self.skip_ws()
        if not self.skip_word_and_ws('delete'):
            self.pos = pos
        else:
            array = self.skip_string_and_ws('[')
            if array and not self.skip_string_and_ws(']'):
                self.fail("Expected ']' in array delete-expression.")
            expr = self._parse_cast_expression()
            return ASTDeleteExpr(rooted, array, expr)
        return self._parse_postfix_expression()

    def _parse_cast_expression(self):
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
                    raise self._make_multi_error(errs, "Error in cast expression.")
        else:
            return self._parse_unary_expression()

    def _parse_logical_or_expression(self, inTemplate):
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
        def _parse_bin_op_expr(self, opId, inTemplate):
            if opId + 1 == len(_expression_bin_ops):
                def parser(inTemplate):
                    return self._parse_cast_expression()
            else:
                def parser(inTemplate):
                    return _parse_bin_op_expr(self, opId + 1, inTemplate=inTemplate)
            exprs = []
            ops = []
            exprs.append(parser(inTemplate=inTemplate))
            while True:
                self.skip_ws()
                if inTemplate and self.current_char == '>':
                    break
                pos = self.pos
                oneMore = False
                for op in _expression_bin_ops[opId]:
                    if not self.skip_string(op):
                        continue
                    if op == '&' and self.current_char == '&':
                        # don't split the && 'token'
                        self.pos -= 1
                        # and btw. && has lower precedence, so we are done
                        break
                    try:
                        expr = parser(inTemplate=inTemplate)
                        exprs.append(expr)
                        ops.append(op)
                        oneMore = True
                        break
                    except DefinitionError:
                        self.pos = pos
                if not oneMore:
                    break
            return ASTBinOpExpr(exprs, ops)
        return _parse_bin_op_expr(self, 0, inTemplate=inTemplate)

    def _parse_conditional_expression_tail(self, orExprHead):
        # -> "?" expression ":" assignment-expression
        return None

    def _parse_assignment_expression(self, inTemplate):
        # -> conditional-expression
        #  | logical-or-expression assignment-operator initializer-clause
        #  | throw-expression
        # TODO: parse throw-expression: "throw" assignment-expression [opt]
        # if not a throw expression, then:
        # -> conditional-expression ->
        #     logical-or-expression
        #   | logical-or-expression "?" expression ":" assignment-expression
        #   | logical-or-expression assignment-operator initializer-clause
        exprs = []
        ops = []
        orExpr = self._parse_logical_or_expression(inTemplate=inTemplate)
        exprs.append(orExpr)
        # TODO: handle ternary with _parse_conditional_expression_tail
        while True:
            oneMore = False
            self.skip_ws()
            for op in _expression_assignment_ops:
                if not self.skip_string(op):
                    continue
                expr = self._parse_logical_or_expression(False)
                exprs.append(expr)
                ops.append(op)
                oneMore = True
            if not oneMore:
                break
        if len(ops) == 0:
            return orExpr
        else:
            return ASTAssignmentExpr(exprs, ops)

    def _parse_constant_expression(self, inTemplate):
        # -> conditional-expression
        orExpr = self._parse_logical_or_expression(inTemplate=inTemplate)
        # TODO: use _parse_conditional_expression_tail
        return orExpr

    def _parse_expression(self, inTemplate):
        # -> assignment-expression
        #  | expression "," assignment-expresion
        # TODO: actually parse the second production
        return self._parse_assignment_expression(inTemplate=inTemplate)

    def _parse_expression_fallback(self, end, parser, allow=True):
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
                      " Error was:\n%s" % e.description)
            self.pos = prevPos
        # and then the fallback scanning
        assert end is not None
        self.skip_ws()
        startPos = self.pos
        if self.match(_string_re):
            value = self.matched_text
        else:
            # TODO: add handling of more bracket-like things, and quote handling
            brackets = {'(': ')', '[': ']', '<': '>'}  # type: Dict[unicode, unicode]
            symbols = []  # type: List[unicode]
            while not self.eof:
                if (len(symbols) == 0 and self.current_char in end):
                    break
                if self.current_char in brackets.keys():
                    symbols.append(brackets[self.current_char])
                elif len(symbols) > 0 and self.current_char == symbols[-1]:
                    symbols.pop()
                self.pos += 1
            if len(end) > 0 and self.eof:
                self.fail("Could not find end of expression starting at %d."
                          % startPos)
            value = self.definition[startPos:self.pos].strip()
        return ASTFallbackExpr(value.strip())

    def _parse_operator(self):
        # type: () -> ASTOperator
        self.skip_ws()
        # adapted from the old code
        # thank god, a regular operator definition
        if self.match(_operator_re):
            return ASTOperatorBuildIn(self.matched_text)

        # new/delete operator?
        for op in 'new', 'delete':
            if not self.skip_word(op):
                continue
            self.skip_ws()
            if self.skip_string('['):
                self.skip_ws()
                if not self.skip_string(']'):
                    self.fail('Expected "]" after  "operator ' + op + '["')
                op += '[]'
            return ASTOperatorBuildIn(op)

        # user-defined literal?
        if self.skip_string('""'):
            self.skip_ws()
            if not self.match(_identifier_re):
                self.fail("Expected user-defined literal suffix.")
            identifier = ASTIdentifier(self.matched_text)
            return ASTOperatorLiteral(identifier)

        # oh well, looks like a cast operator definition.
        # In that case, eat another type.
        type = self._parse_type(named=False, outer="operatorCast")
        return ASTOperatorType(type)

    def _parse_template_argument_list(self):
        # type: () -> ASTTemplateArgs
        self.skip_ws()
        if not self.skip_string_and_ws('<'):
            return None
        if self.skip_string('>'):
            return ASTTemplateArgs([])
        prevErrors = []
        templateArgs = []  # type: List
        while 1:
            pos = self.pos
            parsedComma = False
            parsedEnd = False
            try:
                type = self._parse_type(named=False)
                self.skip_ws()
                if self.skip_string('>'):
                    parsedEnd = True
                elif self.skip_string(','):
                    parsedComma = True
                else:
                    self.fail('Expected ">" or "," in template argument list.')
                templateArgs.append(type)
            except DefinitionError as e:
                prevErrors.append((e, "If type argument"))
                self.pos = pos
                try:
                    def parser():
                        return self._parse_constant_expression(inTemplate=True)
                    value = self._parse_expression_fallback([',', '>'], parser)
                    self.skip_ws()
                    if self.skip_string('>'):
                        parsedEnd = True
                    elif self.skip_string(','):
                        parsedComma = True
                    else:
                        self.fail('Expected ">" or "," in template argument list.')
                    templateArgs.append(ASTTemplateArgConstant(value))
                except DefinitionError as e:
                    self.pos = pos
                    prevErrors.append((e, "If non-type argument"))
                    header = "Error in parsing template argument list."
                    raise self._make_multi_error(prevErrors, header)
            if parsedEnd:
                assert not parsedComma
                break
        return ASTTemplateArgs(templateArgs)

    def _parse_nested_name(self, memberPointer=False):
        # type: (bool) -> ASTNestedName
        names = []  # type: List[Any]
        templates = []  # type: List[bool]

        self.skip_ws()
        rooted = False
        if self.skip_string('::'):
            rooted = True
        while 1:
            self.skip_ws()
            if len(names) > 0:
                template = self.skip_word_and_ws('template')
            else:
                template = False
            templates.append(template)
            identOrOp = None  # type: Union[ASTIdentifier, ASTOperator]
            if self.skip_word_and_ws('operator'):
                identOrOp = self._parse_operator()
            else:
                if not self.match(_identifier_re):
                    if memberPointer and len(names) > 0:
                        templates.pop()
                        break
                    self.fail("Expected identifier in nested name.")
                identifier = self.matched_text
                # make sure there isn't a keyword
                if identifier in _keywords:
                    self.fail("Expected identifier in nested name, "
                              "got keyword: %s" % identifier)
                identOrOp = ASTIdentifier(identifier)
            # try greedily to get template arguments,
            # but otherwise a < might be because we are in an expression
            pos = self.pos
            try:
                templateArgs = self._parse_template_argument_list()
            except DefinitionError as ex:
                self.pos = pos
                templateArgs = None
                self.otherErrors.append(ex)
            names.append(ASTNestedNameElement(identOrOp, templateArgs))

            self.skip_ws()
            if not self.skip_string('::'):
                if memberPointer:
                    self.fail("Expected '::' in pointer to member (function).")
                break
        return ASTNestedName(names, templates, rooted)

    def _parse_trailing_type_spec(self):
        # type: () -> Any
        # fundemental types
        self.skip_ws()
        for t in self._simple_fundemental_types:
            if self.skip_word(t):
                return ASTTrailingTypeSpecFundamental(t)

        # TODO: this could/should be more strict
        elements = []
        if self.skip_word_and_ws('signed'):
            elements.append('signed')
        elif self.skip_word_and_ws('unsigned'):
            elements.append('unsigned')
        while 1:
            if self.skip_word_and_ws('short'):
                elements.append('short')
            elif self.skip_word_and_ws('long'):
                elements.append('long')
            else:
                break
        if self.skip_word_and_ws('char'):
            elements.append('char')
        elif self.skip_word_and_ws('int'):
            elements.append('int')
        elif self.skip_word_and_ws('double'):
            elements.append('double')
        if len(elements) > 0:
            return ASTTrailingTypeSpecFundamental(u' '.join(elements))

        # decltype
        self.skip_ws()
        if self.skip_word_and_ws('decltype'):
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after 'decltype'.")
            if self.skip_word_and_ws('auto'):
                if not self.skip_string(')'):
                    self.fail("Expected ')' after 'decltype(auto'.")
                return ASTTrailingTypeSpecDecltypeAuto()
            expr = self._parse_expression(inTemplate=False)
            self.skip_ws()
            if not self.skip_string(')'):
                self.fail("Expected ')' after 'decltype(<expr>'.")
            return ASTTrailingTypeSpecDecltype(expr)

        # prefixed
        prefix = None
        self.skip_ws()
        for k in self._prefix_keys:
            if self.skip_word_and_ws(k):
                prefix = k
                break

        nestedName = self._parse_nested_name()
        return ASTTrailingTypeSpecName(prefix, nestedName)

    def _parse_parameters_and_qualifiers(self, paramMode):
        # type: (unicode) -> ASTParametersQualifiers
        if paramMode == 'new':
            return None
        self.skip_ws()
        if not self.skip_string('('):
            if paramMode == 'function':
                self.fail('Expecting "(" in parameters_and_qualifiers.')
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
                        self.fail('Expected ")" after "..." in '
                                  'parameters_and_qualifiers.')
                    break
                # note: it seems that function arguments can always be named,
                # even in function pointers and similar.
                arg = self._parse_type_with_init(outer=None, named='single')
                # TODO: parse default parameters # TODO: didn't we just do that?
                args.append(ASTFunctionParameter(arg))

                self.skip_ws()
                if self.skip_string(','):
                    continue
                elif self.skip_string(')'):
                    break
                else:
                    self.fail(
                        'Expecting "," or ")" in parameters_and_qualifiers, '
                        'got "%s".' % self.current_char)

        # TODO: why did we have this bail-out?
        # does it hurt to parse the extra stuff?
        # it's needed for pointer to member functions
        if paramMode != 'function' and False:
            return ASTParametersQualifiers(
                args, None, None, None, None, None, None, None)

        self.skip_ws()
        const = self.skip_word_and_ws('const')
        volatile = self.skip_word_and_ws('volatile')
        if not const:  # the can be permuted
            const = self.skip_word_and_ws('const')

        refQual = None
        if self.skip_string('&&'):
            refQual = '&&'
        if not refQual and self.skip_string('&'):
            refQual = '&'

        exceptionSpec = None
        override = None
        final = None
        initializer = None
        self.skip_ws()
        if self.skip_string('noexcept'):
            exceptionSpec = 'noexcept'
            self.skip_ws()
            if self.skip_string('('):
                self.fail('Parameterised "noexcept" not implemented.')

        self.skip_ws()
        override = self.skip_word_and_ws('override')
        final = self.skip_word_and_ws('final')
        if not override:
            override = self.skip_word_and_ws(
                'override')  # they can be permuted

        self.skip_ws()
        if self.skip_string('='):
            self.skip_ws()
            valid = ('0', 'delete', 'default')
            for w in valid:
                if self.skip_word_and_ws(w):
                    initializer = w
                    break
            if not initializer:
                self.fail(
                    'Expected "%s" in initializer-specifier.'
                    % u'" or "'.join(valid))

        return ASTParametersQualifiers(
            args, volatile, const, refQual, exceptionSpec, override, final,
            initializer)

    def _parse_decl_specs_simple(self, outer, typed):
        # type: (unicode, bool) -> ASTDeclSpecsSimple
        """Just parse the simple ones."""
        storage = None
        threadLocal = None
        inline = None
        virtual = None
        explicit = None
        constexpr = None
        volatile = None
        const = None
        friend = None
        attrs = []
        while 1:  # accept any permutation of a subset of some decl-specs
            self.skip_ws()
            if not storage:
                if outer in ('member', 'function'):
                    if self.skip_word('static'):
                        storage = 'static'
                        continue
                    if self.skip_word('extern'):
                        storage = 'extern'
                        continue
                if outer == 'member':
                    if self.skip_word('mutable'):
                        storage = 'mutable'
                        continue
                if self.skip_word('register'):
                    storage = 'register'
                    continue
            if not threadLocal and outer == 'member':
                threadLocal = self.skip_word('thread_local')
                if threadLocal:
                    continue

            if outer == 'function':
                # function-specifiers
                if not inline:
                    inline = self.skip_word('inline')
                    if inline:
                        continue
                if not friend:
                    friend = self.skip_word('friend')
                    if friend:
                        continue
                if not virtual:
                    virtual = self.skip_word('virtual')
                    if virtual:
                        continue
                if not explicit:
                    explicit = self.skip_word('explicit')
                    if explicit:
                        continue

            if not constexpr and outer in ('member', 'function'):
                constexpr = self.skip_word("constexpr")
                if constexpr:
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
        return ASTDeclSpecsSimple(storage, threadLocal, inline, virtual,
                                  explicit, constexpr, volatile, const,
                                  friend, attrs)

    def _parse_decl_specs(self, outer, typed=True):
        # type: (unicode, bool) -> ASTDeclSpecs
        if outer:
            if outer not in ('type', 'member', 'function', 'templateParam'):
                raise Exception('Internal error, unknown outer "%s".' % outer)
        """
        storage-class-specifier function-specifier "constexpr"
        "volatile" "const" trailing-type-specifier

        storage-class-specifier ->
              "static" (only for member_object and function_object)
            | "register"

        function-specifier -> "inline" | "virtual" | "explicit" (only for
        function_object)

        "constexpr" (only for member_object and function_object)
        """
        leftSpecs = self._parse_decl_specs_simple(outer, typed)
        rightSpecs = None

        if typed:
            trailing = self._parse_trailing_type_spec()
            rightSpecs = self._parse_decl_specs_simple(outer, typed)
        else:
            trailing = None
        return ASTDeclSpecs(outer, leftSpecs, rightSpecs, trailing)

    def _parse_declarator_name_param_qual(self, named, paramMode, typed):
        # type: (Union[bool, unicode], unicode, bool) -> ASTDeclaratorNameParamQual
        # now we should parse the name, and then suffixes
        if named == 'maybe':
            pos = self.pos
            try:
                declId = self._parse_nested_name()
            except DefinitionError:
                self.pos = pos
                declId = None
        elif named == 'single':
            if self.match(_identifier_re):
                identifier = ASTIdentifier(self.matched_text)
                nne = ASTNestedNameElement(identifier, None)
                declId = ASTNestedName([nne], [False], rooted=False)
                # if it's a member pointer, we may have '::', which should be an error
                self.skip_ws()
                if self.current_char == ':':
                    self.fail("Unexpected ':' after identifier.")
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
                if self.skip_string(']'):
                    arrayOps.append(ASTArray(None))
                    continue

                def parser():
                    return self._parse_expression(inTemplate=False)
                value = self._parse_expression_fallback([']'], parser)
                if not self.skip_string(']'):
                    self.fail("Expected ']' in end of array operator.")
                arrayOps.append(ASTArray(value))
                continue
            else:
                break
        paramQual = self._parse_parameters_and_qualifiers(paramMode)
        return ASTDeclaratorNameParamQual(declId=declId, arrayOps=arrayOps,
                                          paramQual=paramQual)

    def _parse_declarator(self, named, paramMode, typed=True):
        # type: (Union[bool, unicode], unicode, bool) -> Any
        # 'typed' here means 'parse return type stuff'
        if paramMode not in ('type', 'function', 'operatorCast', 'new'):
            raise Exception(
                "Internal error, unknown paramMode '%s'." % paramMode)
        prevErrors = []
        self.skip_ws()
        if typed and self.skip_string('*'):
            self.skip_ws()
            volatile = False
            const = False
            attrs = []
            while 1:
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
            return ASTDeclaratorPtr(next=next, volatile=volatile, const=const, attrs=attrs)
        # TODO: shouldn't we parse an R-value ref here first?
        if typed and self.skip_string("&"):
            attrs = []
            while 1:
                attr = self._parse_attribute()
                if attr is None:
                    break
                attrs.append(attr)
            next = self._parse_declarator(named, paramMode, typed)
            return ASTDeclaratorRef(next=next, attrs=attrs)
        if typed and self.skip_string("..."):
            next = self._parse_declarator(named, paramMode, False)
            return ASTDeclaratorParamPack(next=next)
        if typed:  # pointer to member
            pos = self.pos
            try:
                name = self._parse_nested_name(memberPointer=True)
                self.skip_ws()
                if not self.skip_string('*'):
                    self.fail("Expected '*' in pointer to member declarator.")
                self.skip_ws()
            except DefinitionError as e:
                self.pos = pos
                prevErrors.append((e, "If pointer to member declarator"))
            else:
                volatile = False
                const = False
                while 1:
                    if not volatile:
                        volatile = self.skip_word_and_ws('volatile')
                        if volatile:
                            continue
                    if not const:
                        const = self.skip_word_and_ws('const')
                        if const:
                            continue
                    break
                next = self._parse_declarator(named, paramMode, typed)
                return ASTDeclaratorMemPtr(name, const, volatile, next=next)
        if typed and self.current_char == '(':  # note: peeking, not skipping
            if paramMode == "operatorCast":
                # TODO: we should be able to parse cast operators which return
                # function pointers. For now, just hax it and ignore.
                return ASTDeclaratorNameParamQual(declId=None, arrayOps=[],
                                                  paramQual=None)
            # maybe this is the beginning of params and quals,try that first,
            # otherwise assume it's noptr->declarator > ( ptr-declarator )
            pos = self.pos
            try:
                # assume this is params and quals
                res = self._parse_declarator_name_param_qual(named, paramMode,
                                                             typed)
                return res
            except DefinitionError as exParamQual:
                prevErrors.append((exParamQual, "If declId, parameters, and qualifiers"))
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
                    prevErrors.append((exNoPtrParen, "If parenthesis in noptr-declarator"))
                    header = "Error in declarator"
                    raise self._make_multi_error(prevErrors, header)
        pos = self.pos
        try:
            return self._parse_declarator_name_param_qual(named, paramMode, typed)
        except DefinitionError as e:
            self.pos = pos
            prevErrors.append((e, "If declarator-id"))
            header = "Error in declarator or parameters and qualifiers"
            raise self._make_multi_error(prevErrors, header)

    def _parse_initializer(self, outer=None, allowFallback=True):
        # type: (unicode, bool) -> ASTInitializer
        self.skip_ws()
        # TODO: support paren and brace initialization for memberObject
        if not self.skip_string('='):
            return None
        else:
            if outer == 'member':
                def parser():
                    return self._parse_assignment_expression(inTemplate=False)
                value = self._parse_expression_fallback([], parser,
                                                        allow=allowFallback)
            elif outer == 'templateParam':
                def parser():
                    return self._parse_assignment_expression(inTemplate=True)
                value = self._parse_expression_fallback([',', '>'], parser,
                                                        allow=allowFallback)
            elif outer is None:  # function parameter
                def parser():
                    return self._parse_assignment_expression(inTemplate=False)
                value = self._parse_expression_fallback([',', ')'], parser,
                                                        allow=allowFallback)
            else:
                self.fail("Internal error, initializer for outer '%s' not "
                          "implemented." % outer)
            return ASTInitializer(value)

    def _parse_type(self, named, outer=None):
        # type: (Union[bool, unicode], unicode) -> ASTType
        """
        named=False|'maybe'|True: 'maybe' is e.g., for function objects which
        doesn't need to name the arguments

        outer == operatorCast: annoying case, we should not take the params
        """
        if outer:  # always named
            if outer not in ('type', 'member', 'function',
                             'operatorCast', 'templateParam'):
                raise Exception('Internal error, unknown outer "%s".' % outer)
            if outer != 'operatorCast':
                assert named

        if outer in ('type', 'function'):
            # We allow type objects to just be a name.
            # Some functions don't have normal return types: constructors,
            # destrutors, cast operators
            prevErrors = []
            startPos = self.pos
            # first try without the type
            try:
                declSpecs = self._parse_decl_specs(outer=outer, typed=False)
                decl = self._parse_declarator(named=True, paramMode=outer,
                                              typed=False)
                self.assert_end()
            except DefinitionError as exUntyped:
                if outer == 'type':
                    desc = "If just a name"
                elif outer == 'function':
                    desc = "If the function has no return type"
                else:
                    assert False
                prevErrors.append((exUntyped, desc))
                self.pos = startPos
                try:
                    declSpecs = self._parse_decl_specs(outer=outer)
                    decl = self._parse_declarator(named=True, paramMode=outer)
                except DefinitionError as exTyped:
                    self.pos = startPos
                    if outer == 'type':
                        desc = "If typedef-like declaration"
                    elif outer == 'function':
                        desc = "If the function has a return type"
                    else:
                        assert False
                    prevErrors.append((exTyped, desc))
                    # Retain the else branch for easier debugging.
                    # TODO: it would be nice to save the previous stacktrace
                    #       and output it here.
                    if True:
                        if outer == 'type':
                            header = "Type must be either just a name or a "
                            header += "typedef-like declaration."
                        elif outer == 'function':
                            header = "Error when parsing function declaration."
                        else:
                            assert False
                        raise self._make_multi_error(prevErrors, header)
                    else:
                        # For testing purposes.
                        # do it again to get the proper traceback (how do you
                        # reliably save a traceback when an exception is
                        # constructed?)
                        self.pos = startPos
                        typed = True
                        declSpecs = self._parse_decl_specs(outer=outer, typed=typed)
                        decl = self._parse_declarator(named=True, paramMode=outer,
                                                      typed=typed)
        else:
            paramMode = 'type'
            if outer == 'member':  # i.e., member
                named = True
            elif outer == 'operatorCast':
                paramMode = 'operatorCast'
                outer = None
            elif outer == 'templateParam':
                named = 'single'
            declSpecs = self._parse_decl_specs(outer=outer)
            decl = self._parse_declarator(named=named, paramMode=paramMode)
        return ASTType(declSpecs, decl)

    def _parse_type_with_init(self, named, outer):
        # type: (Union[bool, unicode], unicode) -> Any
        if outer:
            assert outer in ('type', 'member', 'function', 'templateParam')
        type = self._parse_type(outer=outer, named=named)
        if outer != 'templateParam':
            init = self._parse_initializer(outer=outer)
            return ASTTypeWithInit(type, init)
        # it could also be a constrained type parameter, e.g., C T = int&
        pos = self.pos
        eExpr = None
        try:
            init = self._parse_initializer(outer=outer, allowFallback=False)
            # note: init may be None if there is no =
            if init is None:
                return ASTTypeWithInit(type, None)
            # we parsed an expression, so we must have a , or a >,
            # otherwise the expression didn't get everything
            self.skip_ws()
            if self.current_char != ',' and self.current_char != '>':
                # pretend it didn't happen
                self.pos = pos
                init = None
            else:
                # we assume that it was indeed an expression
                return ASTTypeWithInit(type, init)
        except DefinitionError as e:
            self.pos = pos
            eExpr = e
        if not self.skip_string("="):
            return ASTTypeWithInit(type, None)
        try:
            typeInit = self._parse_type(named=False, outer=None)
            return ASTTemplateParamConstrainedTypeWithInit(type, typeInit)
        except DefinitionError as eType:
            if eExpr is None:
                raise eType
            errs = []
            errs.append((eExpr, "If default is an expression"))
            errs.append((eType, "If default is a type"))
            msg = "Error in non-type template parameter"
            msg += " or constrianted template paramter."
            raise self._make_multi_error(errs, msg)

    def _parse_type_using(self):
        # type: () -> ASTTypeUsing
        name = self._parse_nested_name()
        self.skip_ws()
        if not self.skip_string('='):
            return ASTTypeUsing(name, None)
        type = self._parse_type(False, None)
        return ASTTypeUsing(name, type)

    def _parse_concept(self):
        # type: () -> ASTConcept
        nestedName = self._parse_nested_name()
        self.skip_ws()
        initializer = self._parse_initializer('member')
        return ASTConcept(nestedName, initializer)

    def _parse_class(self):
        # type: () -> ASTClass
        name = self._parse_nested_name()
        self.skip_ws()
        final = self.skip_word_and_ws('final')
        bases = []
        self.skip_ws()
        if self.skip_string(':'):
            while 1:
                self.skip_ws()
                visibility = 'private'  # type: unicode
                virtual = False
                pack = False
                if self.skip_word_and_ws('virtual'):
                    virtual = True
                if self.match(_visibility_re):
                    visibility = self.matched_text
                    self.skip_ws()
                if not virtual and self.skip_word_and_ws('virtual'):
                    virtual = True
                baseName = self._parse_nested_name()
                self.skip_ws()
                pack = self.skip_string('...')
                bases.append(ASTBaseClass(baseName, visibility, virtual, pack))
                self.skip_ws()
                if self.skip_string(','):
                    continue
                else:
                    break
        return ASTClass(name, final, bases)

    def _parse_union(self):
        # type: () -> ASTUnion
        name = self._parse_nested_name()
        return ASTUnion(name)

    def _parse_enum(self):
        # type: () -> ASTEnum
        scoped = None  # type: unicode #  is set by CPPEnumObject
        self.skip_ws()
        name = self._parse_nested_name()
        self.skip_ws()
        underlyingType = None
        if self.skip_string(':'):
            underlyingType = self._parse_type(named=False)
        return ASTEnum(name, scoped, underlyingType)

    def _parse_enumerator(self):
        # type: () -> ASTEnumerator
        name = self._parse_nested_name()
        self.skip_ws()
        init = None
        if self.skip_string('='):
            self.skip_ws()

            def parser():
                return self._parse_constant_expression(inTemplate=False)
            initVal = self._parse_expression_fallback([], parser)
            init = ASTInitializer(initVal)
        return ASTEnumerator(name, init)

    def _parse_template_parameter_list(self):
        # type: () -> ASTTemplateParams
        # only: '<' parameter-list '>'
        # we assume that 'template' has just been parsed
        templateParams = []  # type: List
        self.skip_ws()
        if not self.skip_string("<"):
            self.fail("Expected '<' after 'template'")
        while 1:
            prevErrors = []
            self.skip_ws()
            if self.skip_word('template'):
                # declare a tenplate template parameter
                nestedParams = self._parse_template_parameter_list()
                nestedParams.isNested = True
            else:
                nestedParams = None
            self.skip_ws()
            key = None
            if self.skip_word_and_ws('typename'):
                key = 'typename'
            elif self.skip_word_and_ws('class'):
                key = 'class'
            elif nestedParams:
                self.fail("Expected 'typename' or 'class' after "
                          "template template parameter list.")
            if key:
                # declare a type or template type parameter
                self.skip_ws()
                parameterPack = self.skip_string('...')
                self.skip_ws()
                if self.match(_identifier_re):
                    identifier = ASTIdentifier(self.matched_text)
                else:
                    identifier = None
                self.skip_ws()
                if not parameterPack and self.skip_string('='):
                    default = self._parse_type(named=False, outer=None)
                else:
                    default = None
                data = ASTTemplateKeyParamPackIdDefault(key, identifier,
                                                        parameterPack, default)
                if nestedParams:
                    # template type
                    param = ASTTemplateParamTemplateType(nestedParams, data)  # type: Any
                else:
                    # type
                    param = ASTTemplateParamType(data)
                templateParams.append(param)
            else:
                # declare a non-type parameter, or constrained type parameter
                pos = self.pos
                try:
                    param = self._parse_type_with_init('maybe', 'templateParam')
                    templateParams.append(ASTTemplateParamNonType(param))
                except DefinitionError as e:
                    msg = "If non-type template parameter or constrained template parameter"
                    prevErrors.append((e, msg))
                    self.pos = pos
            self.skip_ws()
            if self.skip_string('>'):
                return ASTTemplateParams(templateParams)
            elif self.skip_string(','):
                continue
            else:
                header = "Error in template parameter list."
                try:
                    self.fail('Expected "=", ",", or ">".')
                except DefinitionError as e:
                    prevErrors.append((e, ""))
                raise self._make_multi_error(prevErrors, header)

    def _parse_template_introduction(self):
        # type: () -> ASTTemplateIntroduction
        pos = self.pos
        try:
            concept = self._parse_nested_name()
        except Exception:
            self.pos = pos
            return None
        self.skip_ws()
        if not self.skip_string('{'):
            self.pos = pos
            return None

        # for sure it must be a template introduction now
        params = []
        while 1:
            self.skip_ws()
            parameterPack = self.skip_string('...')
            self.skip_ws()
            if not self.match(_identifier_re):
                self.fail("Expected identifier in template introduction list.")
            txt_identifier = self.matched_text
            # make sure there isn't a keyword
            if txt_identifier in _keywords:
                self.fail("Expected identifier in template introduction list, "
                          "got keyword: %s" % txt_identifier)
            identifier = ASTIdentifier(txt_identifier)
            params.append(ASTTemplateIntroductionParameter(identifier, parameterPack))

            self.skip_ws()
            if self.skip_string('}'):
                break
            elif self.skip_string(','):
                continue
            else:
                self.fail("Error in template introduction list. "
                          'Expected ",", or "}".')
        return ASTTemplateIntroduction(concept, params)

    def _parse_template_declaration_prefix(self, objectType):
        # type: (unicode) -> ASTTemplateDeclarationPrefix
        templates = []  # type: List
        while 1:
            self.skip_ws()
            # the saved position is only used to provide a better error message
            pos = self.pos
            if self.skip_word("template"):
                try:
                    params = self._parse_template_parameter_list()  # type: Any
                except DefinitionError as e:
                    if objectType == 'member' and len(templates) == 0:
                        return ASTTemplateDeclarationPrefix(None)
                    else:
                        raise e
            else:
                params = self._parse_template_introduction()
                if not params:
                    break
            if objectType == 'concept' and len(templates) > 0:
                self.pos = pos
                self.fail("More than 1 template parameter list for concept.")
            templates.append(params)
        if len(templates) == 0 and objectType == 'concept':
            self.fail('Missing template parameter list for concept.')
        if len(templates) == 0:
            return None
        else:
            return ASTTemplateDeclarationPrefix(templates)

    def _check_template_consistency(self,
                                    nestedName,         # type: ASTNestedName
                                    templatePrefix,     # type: ASTTemplateDeclarationPrefix
                                    fullSpecShorthand,  # type: bool
                                    isMember=False      # type: bool
                                    ):
        # type: (...) -> ASTTemplateDeclarationPrefix
        numArgs = nestedName.num_templates()
        isMemberInstantiation = False
        if not templatePrefix:
            numParams = 0
        else:
            if isMember and templatePrefix.templates is None:
                numParams = 0
                isMemberInstantiation = True
            else:
                numParams = len(templatePrefix.templates)
        if numArgs + 1 < numParams:
            self.fail("Too few template argument lists comapred to parameter"
                      " lists. Argument lists: %d, Parameter lists: %d."
                      % (numArgs, numParams))
        if numArgs > numParams:
            numExtra = numArgs - numParams
            if not fullSpecShorthand and not isMemberInstantiation:
                msg = "Too many template argument lists compared to parameter" \
                    " lists. Argument lists: %d, Parameter lists: %d," \
                    " Extra empty parameters lists prepended: %d." \
                    % (numArgs, numParams, numExtra)  # type: unicode
                msg += " Declaration:\n\t"
                if templatePrefix:
                    msg += "%s\n\t" % text_type(templatePrefix)
                msg += text_type(nestedName)
                self.warn(msg)

            newTemplates = []
            for i in range(numExtra):
                newTemplates.append(ASTTemplateParams([]))
            if templatePrefix and not isMemberInstantiation:
                newTemplates.extend(templatePrefix.templates)
            templatePrefix = ASTTemplateDeclarationPrefix(newTemplates)
        return templatePrefix

    def parse_declaration(self, objectType):
        # type: (unicode) -> ASTDeclaration
        if objectType not in ('type', 'concept', 'member',
                              'function', 'class', 'union', 'enum', 'enumerator'):
            raise Exception('Internal error, unknown objectType "%s".' % objectType)
        visibility = None
        templatePrefix = None
        declaration = None  # type: Any

        self.skip_ws()
        if self.match(_visibility_re):
            visibility = self.matched_text

        if objectType in ('type', 'concept', 'member', 'function', 'class'):
            templatePrefix = self._parse_template_declaration_prefix(objectType)

        if objectType == 'type':
            prevErrors = []
            pos = self.pos
            try:
                if not templatePrefix:
                    declaration = self._parse_type(named=True, outer='type')
            except DefinitionError as e:
                prevErrors.append((e, "If typedef-like declaration"))
                self.pos = pos
            pos = self.pos
            try:
                if not declaration:
                    declaration = self._parse_type_using()
            except DefinitionError as e:
                self.pos = pos
                prevErrors.append((e, "If type alias or template alias"))
                header = "Error in type declaration."
                raise self._make_multi_error(prevErrors, header)
        elif objectType == 'concept':
            declaration = self._parse_concept()
        elif objectType == 'member':
            declaration = self._parse_type_with_init(named=True, outer='member')
        elif objectType == 'function':
            declaration = self._parse_type(named=True, outer='function')
        elif objectType == 'class':
            declaration = self._parse_class()
        elif objectType == 'union':
            declaration = self._parse_union()
        elif objectType == 'enum':
            declaration = self._parse_enum()
        elif objectType == 'enumerator':
            declaration = self._parse_enumerator()
        else:
            assert False
        templatePrefix = self._check_template_consistency(declaration.name,
                                                          templatePrefix,
                                                          fullSpecShorthand=False,
                                                          isMember=objectType == 'member')
        return ASTDeclaration(objectType, visibility,
                              templatePrefix, declaration)

    def parse_namespace_object(self):
        # type: () -> ASTNamespace
        templatePrefix = self._parse_template_declaration_prefix(objectType="namespace")
        name = self._parse_nested_name()
        templatePrefix = self._check_template_consistency(name, templatePrefix,
                                                          fullSpecShorthand=False)
        res = ASTNamespace(name, templatePrefix)
        res.objectType = 'namespace'  # type: ignore
        return res

    def parse_xref_object(self):
        # type: () -> Tuple[Any, bool]
        pos = self.pos
        try:
            templatePrefix = self._parse_template_declaration_prefix(objectType="xref")
            name = self._parse_nested_name()
            # if there are '()' left, just skip them
            self.skip_ws()
            self.skip_string('()')
            templatePrefix = self._check_template_consistency(name, templatePrefix,
                                                              fullSpecShorthand=True)
            res1 = ASTNamespace(name, templatePrefix)
            res1.objectType = 'xref'  # type: ignore
            return res1, True
        except DefinitionError as e1:
            try:
                self.pos = pos
                res2 = self.parse_declaration('function')
                # if there are '()' left, just skip them
                self.skip_ws()
                self.skip_string('()')
                return res2, False
            except DefinitionError as e2:
                errs = []
                errs.append((e1, "If shorthand ref"))
                errs.append((e2, "If full function ref"))
                msg = "Error in cross-reference."
                raise self._make_multi_error(errs, msg)

    def parse_expression(self):
        pos = self.pos
        try:
            expr = self._parse_expression(False)
            self.skip_ws()
            self.assert_end()
        except DefinitionError as exExpr:
            self.pos = pos
            try:
                expr = self._parse_type(False)
                self.skip_ws()
                self.assert_end()
            except DefinitionError as exType:
                header = "Error when parsing (type) expression."
                errs = []
                errs.append((exExpr, "If expression"))
                errs.append((exType, "If type"))
                raise self._make_multi_error(errs, header)
        return expr


def _make_phony_error_name():
    # type: () -> ASTNestedName
    nne = ASTNestedNameElement(ASTIdentifier("PhonyNameDueToError"), None)
    return ASTNestedName([nne], [False], rooted=False)


class CPPObject(ObjectDescription):
    """Description of a C++ language object."""

    doc_field_types = [
        GroupedField('parameter', label=_('Parameters'),
                     names=('param', 'parameter', 'arg', 'argument'),
                     can_collapse=True),
        GroupedField('template parameter', label=_('Template Parameters'),
                     names=('tparam', 'template parameter'),
                     can_collapse=True),
        GroupedField('exceptions', label=_('Throws'), rolename='cpp:class',
                     names=('throws', 'throw', 'exception'),
                     can_collapse=True),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
    ]

    option_spec = dict(ObjectDescription.option_spec)
    option_spec['tparam-line-spec'] = directives.flag

    def warn(self, msg):
        # type: (unicode) -> None
        self.state_machine.reporter.warning(msg, line=self.lineno)

    def _add_enumerator_to_parent(self, ast):
        # type: (Any) -> None
        assert ast.objectType == 'enumerator'
        # find the parent, if it exists && is an enum
        #                     && it's unscoped,
        #                  then add the name to the parent scope
        symbol = ast.symbol
        assert symbol
        assert symbol.identOrOp is not None
        assert symbol.templateParams is None
        assert symbol.templateArgs is None
        parentSymbol = symbol.parent
        assert parentSymbol
        if parentSymbol.parent is None:
            # TODO: we could warn, but it is somewhat equivalent to unscoped
            # enums, without the enum
            return  # no parent
        parentDecl = parentSymbol.declaration
        if parentDecl is None:
            # the parent is not explicitly declared
            # TODO: we could warn, but it could be a style to just assume
            # enumerator parents to be scoped
            return
        if parentDecl.objectType != 'enum':
            # TODO: maybe issue a warning, enumerators in non-enums is weird,
            # but it is somewhat equivalent to unscoped enums, without the enum
            return
        if parentDecl.scoped:
            return

        targetSymbol = parentSymbol.parent
        s = targetSymbol.find_identifier(symbol.identOrOp, matchSelf=False, recurseInAnon=True)
        if s is not None:
            # something is already declared with that name
            return
        declClone = symbol.declaration.clone()
        declClone.enumeratorScopedSymbol = symbol
        Symbol(parent=targetSymbol, identOrOp=symbol.identOrOp,
               templateParams=None, templateArgs=None,
               declaration=declClone,
               docname=self.env.docname)

    def add_target_and_index(self, ast, sig, signode):
        # type: (Any, unicode, addnodes.desc_signature) -> None
        # general note: name must be lstrip(':')'ed, to remove "::"
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
        if not re.compile(r'^[a-zA-Z0-9_]*$').match(newestId):
            self.warn('Index id generation for C++ object "%s" failed, please '
                      'report as bug (id=%s).' % (text_type(ast), newestId))

        name = ast.symbol.get_full_nested_name().get_display_string().lstrip(':')
        # Add index entry, but not if it's a declaration inside a concept
        isInConcept = False
        s = ast.symbol.parent
        while s is not None:
            decl = s.declaration
            s = s.parent
            if decl is None:
                continue
            if decl.objectType == 'concept':
                isInConcept = True
                break
        if not isInConcept:
            strippedName = name
            for prefix in self.env.config.cpp_index_common_prefix:
                if name.startswith(prefix):
                    strippedName = strippedName[len(prefix):]
                    break
            indexText = self.get_index_text(strippedName)
            self.indexnode['entries'].append(('single', indexText, newestId, '', None))

        if newestId not in self.state.document.ids:
            # if the name is not unique, the first one will win
            names = self.env.domaindata['cpp']['names']
            if name not in names:
                names[name] = ast.symbol.docname
                signode['names'].append(name)
            else:
                # print("[CPP] non-unique name:", name)
                pass
            # always add the newest id
            assert newestId
            signode['ids'].append(newestId)
            # only add compatibility ids when there are no conflicts
            for id in ids[1:]:
                if not id:  # is None when the element didn't exist in that version
                    continue
                if id not in self.state.document.ids:
                    signode['ids'].append(id)
            signode['first'] = (not self.names)  # hmm, what is this about?
            self.state.document.note_explicit_target(signode)

    def parse_definition(self, parser):
        # type: (Any) -> Any
        raise NotImplementedError()

    def describe_signature(self, signode, ast, options):
        # type: (addnodes.desc_signature, Any, Dict) -> None
        ast.describe_signature(signode, 'lastIsName', self.env, options)

    def run(self):
        env = self.state.document.settings.env  # from ObjectDescription.run
        if 'cpp:parent_symbol' not in env.temp_data:
            root = env.domaindata['cpp']['root_symbol']
            env.temp_data['cpp:parent_symbol'] = root
            env.ref_context['cpp:parent_key'] = root.get_lookup_key()

        # The lookup keys assume that no nested scopes exists inside overloaded functions.
        # (see also #5191)
        # Example:
        # .. cpp:function:: void f(int)
        # .. cpp:function:: void f(double)
        #
        #    .. cpp:function:: void g()
        #
        #       :cpp:any:`boom`
        #
        # So we disallow any signatures inside functions.
        parentSymbol = env.temp_data['cpp:parent_symbol']
        parentDecl = parentSymbol.declaration
        if parentDecl is not None and parentDecl.objectType == 'function':
            self.warn("C++ declarations inside functions are not supported." +
                      " Parent function is " + text_type(parentSymbol.get_full_nested_name()))
            name = _make_phony_error_name()
            symbol = parentSymbol.add_name(name)
            env.temp_data['cpp:last_symbol'] = symbol
            return []
        return ObjectDescription.run(self)

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> Any
        parentSymbol = self.env.temp_data['cpp:parent_symbol']

        parser = DefinitionParser(sig, self, self.env.config)
        try:
            ast = self.parse_definition(parser)
            parser.assert_end()
        except DefinitionError as e:
            self.warn(e.description)
            # It is easier to assume some phony name than handling the error in
            # the possibly inner declarations.
            name = _make_phony_error_name()
            symbol = parentSymbol.add_name(name)
            self.env.temp_data['cpp:last_symbol'] = symbol
            raise ValueError

        try:
            symbol = parentSymbol.add_declaration(ast, docname=self.env.docname)
            self.env.temp_data['cpp:last_symbol'] = symbol
        except _DuplicateSymbolError as e:
            # Assume we are actually in the old symbol,
            # instead of the newly created duplicate.
            self.env.temp_data['cpp:last_symbol'] = e.symbol
            self.warn("Duplicate declaration, %s" % sig)

        if ast.objectType == 'enumerator':
            self._add_enumerator_to_parent(ast)

        # note: handle_signature may be called multiple time per directive,
        # if it has multiple signatures, so don't mess with the original options.
        options = dict(self.options)
        options['tparam-line-spec'] = 'tparam-line-spec' in self.options
        self.describe_signature(signode, ast, options)
        return ast

    def before_content(self):
        # type: () -> None
        lastSymbol = self.env.temp_data['cpp:last_symbol']
        assert lastSymbol
        self.oldParentSymbol = self.env.temp_data['cpp:parent_symbol']
        self.oldParentKey = self.env.ref_context['cpp:parent_key']
        self.env.temp_data['cpp:parent_symbol'] = lastSymbol
        self.env.ref_context['cpp:parent_key'] = lastSymbol.get_lookup_key()

    def after_content(self):
        # type: () -> None
        self.env.temp_data['cpp:parent_symbol'] = self.oldParentSymbol
        self.env.ref_context['cpp:parent_key'] = self.oldParentKey


class CPPTypeObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ type)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("type")


class CPPConceptObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ concept)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("concept")


class CPPMemberObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ member)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("member")


class CPPFunctionObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ function)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("function")


class CPPClassObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ class)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("class")


class CPPUnionObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ union)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("union")


class CPPEnumObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ enum)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        ast = parser.parse_declaration("enum")
        # self.objtype is set by ObjectDescription in run()
        if self.objtype == "enum":
            ast.scoped = None
        elif self.objtype == "enum-struct":
            ast.scoped = "struct"
        elif self.objtype == "enum-class":
            ast.scoped = "class"
        else:
            assert False
        return ast


class CPPEnumeratorObject(CPPObject):
    def get_index_text(self, name):
        # type: (unicode) -> unicode
        return _('%s (C++ enumerator)') % name

    def parse_definition(self, parser):
        # type: (Any) -> Any
        return parser.parse_declaration("enumerator")


class CPPNamespaceObject(SphinxDirective):
    """
    This directive is just to tell Sphinx that we're documenting stuff in
    namespace foo.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def warn(self, msg):
        # type: (unicode) -> None
        self.state_machine.reporter.warning(msg, line=self.lineno)

    def run(self):
        # type: () -> List[nodes.Node]
        rootSymbol = self.env.domaindata['cpp']['root_symbol']
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            symbol = rootSymbol
            stack = []  # type: List[Symbol]
        else:
            parser = DefinitionParser(self.arguments[0], self, self.config)
            try:
                ast = parser.parse_namespace_object()
                parser.assert_end()
            except DefinitionError as e:
                self.warn(e.description)
                name = _make_phony_error_name()
                ast = ASTNamespace(name, None)
            symbol = rootSymbol.add_name(ast.nestedName, ast.templatePrefix)
            stack = [symbol]
        self.env.temp_data['cpp:parent_symbol'] = symbol
        self.env.temp_data['cpp:namespace_stack'] = stack
        self.env.ref_context['cpp:parent_key'] = symbol.get_lookup_key()
        return []


class CPPNamespacePushObject(SphinxDirective):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def warn(self, msg):
        # type: (unicode) -> None
        self.state_machine.reporter.warning(msg, line=self.lineno)

    def run(self):
        # type: () -> List[nodes.Node]
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            return []
        parser = DefinitionParser(self.arguments[0], self, self.config)
        try:
            ast = parser.parse_namespace_object()
            parser.assert_end()
        except DefinitionError as e:
            self.warn(e.description)
            name = _make_phony_error_name()
            ast = ASTNamespace(name, None)
        oldParent = self.env.temp_data.get('cpp:parent_symbol', None)
        if not oldParent:
            oldParent = self.env.domaindata['cpp']['root_symbol']
        symbol = oldParent.add_name(ast.nestedName, ast.templatePrefix)
        stack = self.env.temp_data.get('cpp:namespace_stack', [])
        stack.append(symbol)
        self.env.temp_data['cpp:parent_symbol'] = symbol
        self.env.temp_data['cpp:namespace_stack'] = stack
        self.env.ref_context['cpp:parent_key'] = symbol.get_lookup_key()
        return []


class CPPNamespacePopObject(SphinxDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def warn(self, msg):
        # type: (unicode) -> None
        self.state_machine.reporter.warning(msg, line=self.lineno)

    def run(self):
        # type: () -> List[nodes.Node]
        stack = self.env.temp_data.get('cpp:namespace_stack', None)
        if not stack or len(stack) == 0:
            self.warn("C++ namespace pop on empty stack. Defaulting to gobal scope.")
            stack = []
        else:
            stack.pop()
        if len(stack) > 0:
            symbol = stack[-1]
        else:
            symbol = self.env.domaindata['cpp']['root_symbol']
        self.env.temp_data['cpp:parent_symbol'] = symbol
        self.env.temp_data['cpp:namespace_stack'] = stack
        self.env.ref_context['cpp:parent_key'] = symbol.get_lookup_key()
        return []


class CPPXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.Node, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        refnode.attributes.update(env.ref_context)

        if not has_explicit_title:
            # major hax: replace anon names via simple string manipulation.
            # Can this actually fail?
            title = _anon_identifier_re.sub("[anonymous]", str(title))

        if refnode['reftype'] == 'any':
            # Assume the removal part of fix_parens for :any: refs.
            # The addition part is done with the reference is resolved.
            if not has_explicit_title and title.endswith('()'):
                title = title[:-2]
            if target.endswith('()'):
                target = target[:-2]
        # TODO: should this really be here?
        if not has_explicit_title:
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[:1] == '~':
                title = title[1:]
                dcolon = title.rfind('::')
                if dcolon != -1:
                    title = title[dcolon + 2:]
        return title, target


class CPPExprRole(object):
    def __init__(self, asCode):
        if asCode:
            # render the expression as inline code
            self.class_type = 'cpp-expr'
            self.node_type = nodes.literal
        else:
            # render the expression as inline text
            self.class_type = 'cpp-texpr'
            self.node_type = nodes.inline

    def __call__(self, typ, rawtext, text, lineno, inliner, options={}, content=[]):
        class Warner(object):
            def warn(self, msg):
                inliner.reporter.warning(msg, line=lineno)
        text = utils.unescape(text).replace('\n', ' ')
        env = inliner.document.settings.env
        parser = DefinitionParser(text, Warner(), env.config)
        # attempt to mimic XRefRole classes, except that...
        classes = ['xref', 'cpp', self.class_type]
        try:
            ast = parser.parse_expression()
        except DefinitionError as ex:
            Warner().warn('Unparseable C++ expression: %r\n%s'
                          % (text, text_type(ex.description)))
            # see below
            return [self.node_type(text, text, classes=classes)], []
        parentSymbol = env.temp_data.get('cpp:parent_symbol', None)
        if parentSymbol is None:
            parentSymbol = env.domaindata['cpp']['root_symbol']
        # ...most if not all of these classes should really apply to the individual references,
        # not the container node
        signode = self.node_type(classes=classes)
        ast.describe_signature(signode, 'markType', env, parentSymbol)
        return [signode], []


class CPPDomain(Domain):
    """C++ language domain."""
    name = 'cpp'
    label = 'C++'
    object_types = {
        'class':      ObjType(_('class'),      'class',             'type', 'identifier'),
        'union':      ObjType(_('union'),      'union',             'type', 'identifier'),
        'function':   ObjType(_('function'),   'function',  'func', 'type', 'identifier'),
        'member':     ObjType(_('member'),     'member',    'var'),
        'type':       ObjType(_('type'),                            'type', 'identifier'),
        'concept':    ObjType(_('concept'),    'concept',                   'identifier'),
        'enum':       ObjType(_('enum'),       'enum',              'type', 'identifier'),
        'enumerator': ObjType(_('enumerator'), 'enumerator')
    }

    directives = {
        'class': CPPClassObject,
        'union': CPPUnionObject,
        'function': CPPFunctionObject,
        'member': CPPMemberObject,
        'var': CPPMemberObject,
        'type': CPPTypeObject,
        'concept': CPPConceptObject,
        'enum': CPPEnumObject,
        'enum-struct': CPPEnumObject,
        'enum-class': CPPEnumObject,
        'enumerator': CPPEnumeratorObject,
        'namespace': CPPNamespaceObject,
        'namespace-push': CPPNamespacePushObject,
        'namespace-pop': CPPNamespacePopObject
    }
    roles = {
        'any': CPPXRefRole(),
        'class': CPPXRefRole(),
        'union': CPPXRefRole(),
        'func': CPPXRefRole(fix_parens=True),
        'member': CPPXRefRole(),
        'var': CPPXRefRole(),
        'type': CPPXRefRole(),
        'concept': CPPXRefRole(),
        'enum': CPPXRefRole(),
        'enumerator': CPPXRefRole(),
        'expr': CPPExprRole(asCode=True),
        'texpr': CPPExprRole(asCode=False)
    }
    initial_data = {
        'root_symbol': Symbol(None, None, None, None, None, None),
        'names': {}  # full name for indexing -> docname
    }

    def clear_doc(self, docname):
        # type: (unicode) -> None
        if Symbol.debug_show_tree:
            print("clear_doc:", docname)
            print("\tbefore:")
            print(self.data['root_symbol'].dump(1))
            print("\tbefore end")

        rootSymbol = self.data['root_symbol']
        rootSymbol.clear_doc(docname)

        if Symbol.debug_show_tree:
            print("\tafter:")
            print(self.data['root_symbol'].dump(1))
            print("\tafter end")
            print("clear_doc end:", docname)
        for name, nDocname in list(self.data['names'].items()):
            if nDocname == docname:
                del self.data['names'][name]

    def process_doc(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        if Symbol.debug_show_tree:
            print("process_doc:", docname)
            print(self.data['root_symbol'].dump(0))
            print("process_doc end:", docname)

    def process_field_xref(self, pnode):
        # type: (nodes.Node) -> None
        pnode.attributes.update(self.env.ref_context)

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        if Symbol.debug_show_tree:
            print("merge_domaindata:")
            print("\tself:")
            print(self.data['root_symbol'].dump(1))
            print("\tself end")
            print("\tother:")
            print(otherdata['root_symbol'].dump(1))
            print("\tother end")
            print("merge_domaindata end")

        self.data['root_symbol'].merge_with(otherdata['root_symbol'],
                                            docnames, self.env)
        ourNames = self.data['names']
        for name, docname in otherdata['names'].items():
            if docname in docnames:
                if name in ourNames:
                    msg = __("Duplicate declaration, also defined in '%s'.\n"
                             "Name of declaration is '%s'.")
                    msg = msg % (ourNames[name], name)
                    logger.warning(msg, location=docname)
                else:
                    ourNames[name] = docname

    def _resolve_xref_inner(self, env, fromdocname, builder, typ,
                            target, node, contnode, emitWarnings=True):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node, bool) -> nodes.Node  # NOQA

        class Warner(object):
            def warn(self, msg):
                if emitWarnings:
                    logger.warning(msg, location=node)
        warner = Warner()
        # add parens again for those that could be functions
        if typ == 'any' or typ == 'func':
            target += '()'
        parser = DefinitionParser(target, warner, env.config)
        try:
            ast, isShorthand = parser.parse_xref_object()
            parser.assert_end()
        except DefinitionError as e:
            def findWarning(e):  # as arg to stop flake8 from complaining
                if typ != 'any' and typ != 'func':
                    return target, e
                # hax on top of the paren hax to try to get correct errors
                parser2 = DefinitionParser(target[:-2], warner, env.config)
                try:
                    parser2.parse_xref_object()
                    parser2.assert_end()
                except DefinitionError as e2:
                    return target[:-2], e2
                # strange, that we don't get the error now, use the original
                return target, e
            t, ex = findWarning(e)
            warner.warn('Unparseable C++ cross-reference: %r\n%s'
                        % (t, text_type(ex.description)))
            return None, None
        parentKey = node.get("cpp:parent_key", None)
        rootSymbol = self.data['root_symbol']
        if parentKey:
            parentSymbol = rootSymbol.direct_lookup(parentKey)
            if not parentSymbol:
                print("Target: ", target)
                print("ParentKey: ", parentKey)
                print(rootSymbol.dump(1))
            assert parentSymbol  # should be there
        else:
            parentSymbol = rootSymbol

        if isShorthand:
            ns = ast  # type: ASTNamespace
            name = ns.nestedName
            if ns.templatePrefix:
                templateDecls = ns.templatePrefix.templates
            else:
                templateDecls = []
            s = parentSymbol.find_name(name, templateDecls, typ,
                                       templateShorthand=True,
                                       matchSelf=True, recurseInAnon=True)
        else:
            decl = ast  # type: ASTDeclaration
            name = decl.name
            s = parentSymbol.find_declaration(decl, typ,
                                              templateShorthand=True,
                                              matchSelf=True, recurseInAnon=True)
        if s is None or s.declaration is None:
            txtName = text_type(name)
            if txtName.startswith('std::') or txtName == 'std':
                raise NoUri()
            return None, None

        if typ.startswith('cpp:'):
            typ = typ[4:]
        if typ == 'func':
            typ = 'function'
        declTyp = s.declaration.objectType

        def checkType():
            if typ == 'any' or typ == 'identifier':
                return True
            if declTyp == 'templateParam':
                return True
            objtypes = self.objtypes_for_role(typ)
            if objtypes:
                return declTyp in objtypes
            print("Type is %s, declType is %s" % (typ, declTyp))
            assert False
        if not checkType():
            warner.warn("cpp:%s targets a %s (%s)."
                        % (typ, s.declaration.objectType,
                           s.get_full_nested_name()))

        declaration = s.declaration
        if isShorthand:
            fullNestedName = s.get_full_nested_name()
            displayName = fullNestedName.get_display_string().lstrip(':')
        else:
            displayName = decl.get_display_string()
        docname = s.docname
        assert docname

        # the non-identifier refs are cross-references, which should be processed:
        # - fix parenthesis due to operator() and add_function_parentheses
        if typ != "identifier":
            title = contnode.pop(0).astext()
            # If it's operator(), we need to add '()' if explicit function parens
            # are requested. Then the Sphinx machinery will add another pair.
            # Also, if it's an 'any' ref that resolves to a function, we need to add
            # parens as well.
            # However, if it's a non-shorthand function ref, for a function that
            # takes no arguments, then we may need to add parens again as well.
            addParen = 0
            if not node.get('refexplicit', False) and declaration.objectType == 'function':
                if isShorthand:
                    # this is just the normal haxing for 'any' roles
                    if env.config.add_function_parentheses and typ == 'any':
                        addParen += 1
                    # and now this stuff for operator()
                    if (env.config.add_function_parentheses and typ == 'function' and
                            title.endswith('operator()')):
                        addParen += 1
                    if ((typ == 'any' or typ == 'function') and
                            title.endswith('operator') and
                            displayName.endswith('operator()')):
                        addParen += 1
                else:
                    # our job here is to essentially nullify add_function_parentheses
                    if env.config.add_function_parentheses:
                        if typ == 'any' and displayName.endswith('()'):
                            addParen += 1
                        elif typ == 'function':
                            if title.endswith('()') and not displayName.endswith('()'):
                                title = title[:-2]
                    else:
                        if displayName.endswith('()'):
                            addParen += 1
            if addParen > 0:
                title += '()' * addParen
            # and reconstruct the title again
            contnode += nodes.Text(title)
        return make_refnode(builder, fromdocname, docname,
                            declaration.get_newest_id(), contnode, displayName
                            ), declaration.objectType

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        return self._resolve_xref_inner(env, fromdocname, builder, typ,
                                        target, node, contnode)[0]

    def resolve_any_xref(self, env, fromdocname, builder, target,
                         node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[Tuple[unicode, nodes.Node]]  # NOQA
        node, objtype = self._resolve_xref_inner(env, fromdocname, builder,
                                                 'any', target, node, contnode,
                                                 emitWarnings=False)
        if node:
            if objtype == 'templateParam':
                return [('cpp:templateParam', node)]
            else:
                return [('cpp:' + self.role_for_objtype(objtype), node)]
        return []

    def get_objects(self):
        # type: () -> Iterator[Tuple[unicode, unicode, unicode, unicode, unicode, int]]
        rootSymbol = self.data['root_symbol']
        for symbol in rootSymbol.get_all_symbols():
            if symbol.declaration is None:
                continue
            assert symbol.docname
            fullNestedName = symbol.get_full_nested_name()
            name = text_type(fullNestedName).lstrip(':')
            dispname = fullNestedName.get_display_string().lstrip(':')
            objectType = symbol.declaration.objectType
            docname = symbol.docname
            newestId = symbol.declaration.get_newest_id()
            yield (name, dispname, objectType, docname, newestId, 1)

    def get_full_qualified_name(self, node):
        # type: (nodes.Node) -> unicode
        target = node.get('reftarget', None)
        if target is None:
            return None
        parentKey = node.get("cpp:parent_key", None)
        if parentKey is None or len(parentKey) <= 0:
            return None

        rootSymbol = self.data['root_symbol']
        parentSymbol = rootSymbol.direct_lookup(parentKey)
        parentName = parentSymbol.get_full_nested_name()
        return '::'.join([text_type(parentName), target])


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(CPPDomain)
    app.add_config_value("cpp_index_common_prefix", [], 'env')
    app.add_config_value("cpp_id_attributes", [], 'env')
    app.add_config_value("cpp_paren_attributes", [], 'env')

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
