"""The C++ language domain."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.errors import NoUri
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
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from docutils.nodes import Element, Node, TextElement, system_message

    from sphinx.addnodes import desc_signature, pending_xref
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec

logger = logging.getLogger(__name__)
T = TypeVar('T')

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
    'sphinx_line_type' set to one of the following (prioritized):
    - 'declarator', if the line contains the name of the declared object.
    - 'templateParams', if the line starts a template parameter list,
    - 'templateParams', if the line has template parameters
      Note: such lines might get a new tag in the future.
    - 'templateIntroduction, if the line is on the form 'conceptName{...}'
    No other desc_signature nodes should exist (so far).


    Grammar
    ----------------------------------------------------------------------------

    See https://www.nongnu.org/hcb/ for the grammar,
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
        # Make the semicolon optional.
        # For now: drop the attributes (TODO).
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
        # Inside e.g., template parameters a strict subset is used
        # (see type-specifier-seq)
        trailing-type-specifier ->
              simple-type-specifier ->
                ::[opt] nested-name-specifier[opt] type-name
              | ::[opt] nested-name-specifier "template" simple-template-id
              | "char" | "bool" | etc.
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
            built-in -> "char" | "bool" | etc.
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
        # use it (e.g., function pointers)
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
              attribute-specifier-seq[opt]
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
            ("class" | "struct")[opt] visibility[opt]
                attribute-specifier-seq[opt] nested-name (":" type)[opt]
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

udl_identifier_re = re.compile(r'''
    [a-zA-Z_][a-zA-Z0-9_]*\b   # note, no word boundary in the beginning
''', re.VERBOSE)
_string_re = re.compile(r"[LuU8]?('([^'\\]*(?:\\.[^'\\]*)*)'"
                        r'|"([^"\\]*(?:\\.[^"\\]*)*)")', re.S)
_visibility_re = re.compile(r'\b(public|private|protected)\b')
_operator_re = re.compile(r'''
        \[\s*\]
    |   \(\s*\)
    |   \+\+ | --
    |   ->\*? | \,
    |   (<<|>>)=? | && | \|\|
    |   <=>
    |   [!<>=/*%+|&^~-]=?
    |   (\b(and|and_eq|bitand|bitor|compl|not|not_eq|or|or_eq|xor|xor_eq)\b)
''', re.VERBOSE)
_fold_operator_re = re.compile(r'''
        ->\*    |    \.\*    |    \,
    |   (<<|>>)=?    |    &&    |    \|\|
    |   !=
    |   [<>=/*%+|&^~-]=?
''', re.VERBOSE)
# see https://en.cppreference.com/w/cpp/keyword
_keywords = [
    'alignas', 'alignof', 'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor',
    'bool', 'break', 'case', 'catch', 'char', 'char8_t', 'char16_t', 'char32_t',
    'class', 'compl', 'concept', 'const', 'consteval', 'constexpr', 'constinit',
    'const_cast', 'continue',
    'decltype', 'default', 'delete', 'do', 'double', 'dynamic_cast', 'else',
    'enum', 'explicit', 'export', 'extern', 'false', 'float', 'for', 'friend',
    'goto', 'if', 'inline', 'int', 'long', 'mutable', 'namespace', 'new',
    'noexcept', 'not', 'not_eq', 'nullptr', 'operator', 'or', 'or_eq',
    'private', 'protected', 'public', 'register', 'reinterpret_cast',
    'requires', 'return', 'short', 'signed', 'sizeof', 'static',
    'static_assert', 'static_cast', 'struct', 'switch', 'template', 'this',
    'thread_local', 'throw', 'true', 'try', 'typedef', 'typeid', 'typename',
    'union', 'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t',
    'while', 'xor', 'xor_eq',
]


_simple_type_specifiers_re = re.compile(r"""
    \b(
    auto|void|bool
    |signed|unsigned
    |short|long
    |char|wchar_t|char(8|16|32)_t
    |int
    |__int(64|128)  # extension
    |float|double
    |__float80|_Float64x|__float128|_Float128  # extension
    |_Complex|_Imaginary  # extension
    )\b
""", re.VERBOSE)

_max_id = 4
_id_prefix = [None, '', '_CPPv2', '_CPPv3', '_CPPv4']
# Ids are used in lookup keys which are used across pickled files,
# so when _max_id changes, make sure to update the ENV_VERSION.

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
    'bool': 'b',
}
_id_shorthands_v1 = {
    'std::string': 'ss',
    'std::ostream': 'os',
    'std::istream': 'is',
    'std::iostream': 'ios',
    'std::vector': 'v',
    'std::map': 'm',
}
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
    '[]': 'subscript-operator',
}

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
    'char8_t': 'Du',
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
    '__int64': 'x',
    'unsigned long long': 'y',
    'unsigned long long int': 'y',
    '__int128': 'n',
    'signed __int128': 'n',
    'unsigned __int128': 'o',
    'float': 'f',
    'double': 'd',
    'long double': 'e',
    '__float80': 'e', '_Float64x': 'e',
    '__float128': 'g', '_Float128': 'g',
    '_Complex float': 'Cf',
    '_Complex double': 'Cd',
    '_Complex long double': 'Ce',
    '_Imaginary float': 'f',
    '_Imaginary double': 'd',
    '_Imaginary long double': 'e',
    'auto': 'Da',
    'decltype(auto)': 'Dc',
    'std::nullptr_t': 'Dn',
}
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
    '~': 'co', 'compl': 'co',
    '+': 'pl',
    '-': 'mi',
    '*': 'ml',
    '/': 'dv',
    '%': 'rm',
    '&': 'an', 'bitand': 'an',
    '|': 'or', 'bitor': 'or',
    '^': 'eo', 'xor': 'eo',
    '=': 'aS',
    '+=': 'pL',
    '-=': 'mI',
    '*=': 'mL',
    '/=': 'dV',
    '%=': 'rM',
    '&=': 'aN', 'and_eq': 'aN',
    '|=': 'oR', 'or_eq': 'oR',
    '^=': 'eO', 'xor_eq': 'eO',
    '<<': 'ls',
    '>>': 'rs',
    '<<=': 'lS',
    '>>=': 'rS',
    '==': 'eq',
    '!=': 'ne', 'not_eq': 'ne',
    '<': 'lt',
    '>': 'gt',
    '<=': 'le',
    '>=': 'ge',
    '<=>': 'ss',
    '!': 'nt', 'not': 'nt',
    '&&': 'aa', 'and': 'aa',
    '||': 'oo', 'or': 'oo',
    '++': 'pp',
    '--': 'mm',
    ',': 'cm',
    '->*': 'pm',
    '->': 'pt',
    '()': 'cl',
    '[]': 'ix',
    '.*': 'ds',  # this one is not overloadable, but we need it for expressions
    '?': 'qu',
}
_id_operator_unary_v2 = {
    '++': 'pp_',
    '--': 'mm_',
    '*': 'de',
    '&': 'ad',
    '+': 'ps',
    '-': 'ng',
    '!': 'nt', 'not': 'nt',
    '~': 'co', 'compl': 'co',
}
_id_char_from_prefix: dict[str | None, str] = {
    None: 'c', 'u8': 'c',
    'u': 'Ds', 'U': 'Di', 'L': 'w',
}
# these are ordered by preceedence
_expression_bin_ops = [
    ['||', 'or'],
    ['&&', 'and'],
    ['|', 'bitor'],
    ['^', 'xor'],
    ['&', 'bitand'],
    ['==', '!=', 'not_eq'],
    ['<=>', '<=', '>=', '<', '>'],
    ['<<', '>>'],
    ['+', '-'],
    ['*', '/', '%'],
    ['.*', '->*'],
]
_expression_unary_ops = ["++", "--", "*", "&", "+", "-", "!", "not", "~", "compl"]
_expression_assignment_ops = ["=", "*=", "/=", "%=", "+=", "-=",
                              ">>=", "<<=", "&=", "and_eq", "^=", "|=", "xor_eq", "or_eq"]
_id_explicit_cast = {
    'dynamic_cast': 'dc',
    'static_cast': 'sc',
    'const_cast': 'cc',
    'reinterpret_cast': 'rc',
}


class _DuplicateSymbolError(Exception):
    def __init__(self, symbol: Symbol, declaration: ASTDeclaration) -> None:
        assert symbol
        assert declaration
        self.symbol = symbol
        self.declaration = declaration

    def __str__(self) -> str:
        return "Internal C++ duplicate symbol error:\n%s" % self.symbol.dump(0)


class ASTBase(ASTBaseBase):
    pass


# Names
################################################################################

class ASTIdentifier(ASTBase):
    def __init__(self, identifier: str) -> None:
        assert identifier is not None
        assert len(identifier) != 0
        self.identifier = identifier

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.identifier)

    def is_anon(self) -> bool:
        return self.identifier[0] == '@'

    def get_id(self, version: int) -> str:
        if self.is_anon() and version < 3:
            raise NoOldIdError
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
                return 'Ut%d_%s' % (len(self.identifier) - 1, self.identifier[1:])
            else:
                return str(len(self.identifier)) + self.identifier

    # and this is where we finally make a difference between __str__ and the display string

    def __str__(self) -> str:
        return self.identifier

    def get_display_string(self) -> str:
        return "[anonymous]" if self.is_anon() else self.identifier

    def describe_signature(self, signode: TextElement, mode: str, env: BuildEnvironment,
                           prefix: str, templateArgs: str, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.is_anon():
            node = addnodes.desc_sig_name(text="[anonymous]")
        else:
            node = addnodes.desc_sig_name(self.identifier, self.identifier)
        if mode == 'markType':
            targetText = prefix + self.identifier + templateArgs
            pnode = addnodes.pending_xref('', refdomain='cpp',
                                          reftype='identifier',
                                          reftarget=targetText, modname=None,
                                          classname=None)
            pnode['cpp:parent_key'] = symbol.get_lookup_key()
            pnode += node
            signode += pnode
        elif mode == 'lastIsName':
            nameNode = addnodes.desc_name()
            nameNode += node
            signode += nameNode
        elif mode == 'noneIsName':
            signode += node
        elif mode == 'param':
            node['classes'].append('sig-param')
            signode += node
        elif mode == 'udl':
            # the target is 'operator""id' instead of just 'id'
            assert len(prefix) == 0
            assert len(templateArgs) == 0
            assert not self.is_anon()
            targetText = 'operator""' + self.identifier
            pnode = addnodes.pending_xref('', refdomain='cpp',
                                          reftype='identifier',
                                          reftarget=targetText, modname=None,
                                          classname=None)
            pnode['cpp:parent_key'] = symbol.get_lookup_key()
            pnode += node
            signode += pnode
        else:
            raise Exception('Unknown description mode: %s' % mode)


class ASTNestedNameElement(ASTBase):
    def __init__(self, identOrOp: ASTIdentifier | ASTOperator,
                 templateArgs: ASTTemplateArgs) -> None:
        self.identOrOp = identOrOp
        self.templateArgs = templateArgs

    def is_operator(self) -> bool:
        return False

    def get_id(self, version: int) -> str:
        res = self.identOrOp.get_id(version)
        if self.templateArgs:
            res += self.templateArgs.get_id(version)
        return res

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.identOrOp)
        if self.templateArgs:
            res += transform(self.templateArgs)
        return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, prefix: str, symbol: Symbol) -> None:
        tArgs = str(self.templateArgs) if self.templateArgs is not None else ''
        self.identOrOp.describe_signature(signode, mode, env, prefix, tArgs, symbol)
        if self.templateArgs is not None:
            self.templateArgs.describe_signature(signode, 'markType', env, symbol)


class ASTNestedName(ASTBase):
    def __init__(self, names: list[ASTNestedNameElement],
                 templates: list[bool], rooted: bool) -> None:
        assert len(names) > 0
        self.names = names
        self.templates = templates
        assert len(self.names) == len(self.templates)
        self.rooted = rooted

    @property
    def name(self) -> ASTNestedName:
        return self

    def num_templates(self) -> int:
        count = 0
        for n in self.names:
            if n.is_operator():
                continue
            if n.templateArgs:
                count += 1
        return count

    def get_id(self, version: int, modifiers: str = '') -> str:
        if version == 1:
            tt = str(self)
            if tt in _id_shorthands_v1:
                return _id_shorthands_v1[tt]
            else:
                return '::'.join(n.get_id(version) for n in self.names)

        res = []
        if len(self.names) > 1 or len(modifiers) > 0:
            res.append('N')
        res.append(modifiers)
        for n in self.names:
            res.append(n.get_id(version))
        if len(self.names) > 1 or len(modifiers) > 0:
            res.append('E')
        return ''.join(res)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.rooted:
            res.append('')
        for i in range(len(self.names)):
            n = self.names[i]
            if self.templates[i]:
                res.append("template " + transform(n))
            else:
                res.append(transform(n))
        return '::'.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        # just print the name part, with template args, not template params
        if mode == 'noneIsName':
            if self.rooted:
                unreachable = "Can this happen?"
                raise AssertionError(unreachable)  # TODO
                signode += nodes.Text('::')
            for i in range(len(self.names)):
                if i != 0:
                    unreachable = "Can this happen?"
                    raise AssertionError(unreachable)  # TODO
                    signode += nodes.Text('::blah')
                n = self.names[i]
                if self.templates[i]:
                    unreachable = "Can this happen?"
                    raise AssertionError(unreachable)  # TODO
                    signode += nodes.Text("template")
                    signode += nodes.Text(" ")
                n.describe_signature(signode, mode, env, '', symbol)
        elif mode == 'param':
            assert not self.rooted, str(self)
            assert len(self.names) == 1
            assert not self.templates[0]
            self.names[0].describe_signature(signode, 'param', env, '', symbol)
        elif mode in ('markType', 'lastIsName', 'markName'):
            # Each element should be a pending xref targeting the complete
            # prefix. however, only the identifier part should be a link, such
            # that template args can be a link as well.
            # For 'lastIsName' we should also prepend template parameter lists.
            templateParams: list[Any] = []
            if mode == 'lastIsName':
                assert symbol is not None
                if symbol.declaration.templatePrefix is not None:
                    templateParams = symbol.declaration.templatePrefix.templates
            iTemplateParams = 0
            templateParamsPrefix = ''
            prefix = ''
            first = True
            names = self.names[:-1] if mode == 'lastIsName' else self.names
            # If lastIsName, then wrap all of the prefix in a desc_addname,
            # else append directly to signode.
            # NOTE: Breathe previously relied on the prefix being in the desc_addname node,
            #       so it can remove it in inner declarations.
            dest = signode
            if mode == 'lastIsName':
                dest = addnodes.desc_addname()
            if self.rooted:
                prefix += '::'
                if mode == 'lastIsName' and len(names) == 0:
                    signode += addnodes.desc_sig_punctuation('::', '::')
                else:
                    dest += addnodes.desc_sig_punctuation('::', '::')
            for i in range(len(names)):
                nne = names[i]
                template = self.templates[i]
                if not first:
                    dest += addnodes.desc_sig_punctuation('::', '::')
                    prefix += '::'
                if template:
                    dest += addnodes.desc_sig_keyword('template', 'template')
                    dest += addnodes.desc_sig_space()
                first = False
                txt_nne = str(nne)
                if txt_nne != '':
                    if nne.templateArgs and iTemplateParams < len(templateParams):
                        templateParamsPrefix += str(templateParams[iTemplateParams])
                        iTemplateParams += 1
                    nne.describe_signature(dest, 'markType',
                                           env, templateParamsPrefix + prefix, symbol)
                prefix += txt_nne
            if mode == 'lastIsName':
                if len(self.names) > 1:
                    dest += addnodes.desc_sig_punctuation('::', '::')
                    signode += dest
                if self.templates[-1]:
                    signode += addnodes.desc_sig_keyword('template', 'template')
                    signode += addnodes.desc_sig_space()
                self.names[-1].describe_signature(signode, mode, env, '', symbol)
        else:
            raise Exception('Unknown description mode: %s' % mode)


################################################################################
# Expressions
################################################################################

class ASTExpression(ASTBase):
    def get_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))


# Primary expressions
################################################################################

class ASTLiteral(ASTExpression):
    pass


class ASTPointerLiteral(ASTLiteral):
    def _stringify(self, transform: StringifyTransform) -> str:
        return 'nullptr'

    def get_id(self, version: int) -> str:
        return 'LDnE'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('nullptr', 'nullptr')


class ASTBooleanLiteral(ASTLiteral):
    def __init__(self, value: bool) -> None:
        self.value = value

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.value:
            return 'true'
        else:
            return 'false'

    def get_id(self, version: int) -> str:
        if self.value:
            return 'L1E'
        else:
            return 'L0E'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword(str(self), str(self))


class ASTNumberLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data

    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data

    def get_id(self, version: int) -> str:
        # TODO: floats should be mangled by writing the hex of the binary representation
        return "L%sE" % self.data.replace("'", "")

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_literal_number(self.data, self.data)


class ASTStringLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data

    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data

    def get_id(self, version: int) -> str:
        # note: the length is not really correct with escaping
        return "LA%d_KcE" % (len(self.data) - 2)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_literal_string(self.data, self.data)


class ASTCharLiteral(ASTLiteral):
    def __init__(self, prefix: str, data: str) -> None:
        self.prefix = prefix  # may be None when no prefix
        self.data = data
        assert prefix in _id_char_from_prefix
        self.type = _id_char_from_prefix[prefix]
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

    def get_id(self, version: int) -> str:
        # TODO: the ID should be have L E around it
        return self.type + str(self.value)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.prefix is not None:
            signode += addnodes.desc_sig_keyword(self.prefix, self.prefix)
        txt = "'" + self.data + "'"
        signode += addnodes.desc_sig_literal_char(txt, txt)


class ASTUserDefinedLiteral(ASTLiteral):
    def __init__(self, literal: ASTLiteral, ident: ASTIdentifier):
        self.literal = literal
        self.ident = ident

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.literal) + transform(self.ident)

    def get_id(self, version: int) -> str:
        # mangle as if it was a function call: ident(literal)
        return f'clL_Zli{self.ident.get_id(version)}E{self.literal.get_id(version)}E'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.literal.describe_signature(signode, mode, env, symbol)
        self.ident.describe_signature(signode, "udl", env, "", "", symbol)


################################################################################

class ASTThisLiteral(ASTExpression):
    def _stringify(self, transform: StringifyTransform) -> str:
        return "this"

    def get_id(self, version: int) -> str:
        return "fpT"

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('this', 'this')


class ASTFoldExpr(ASTExpression):
    def __init__(self, leftExpr: ASTExpression,
                 op: str, rightExpr: ASTExpression) -> None:
        assert leftExpr is not None or rightExpr is not None
        self.leftExpr = leftExpr
        self.op = op
        self.rightExpr = rightExpr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['(']
        if self.leftExpr:
            res.append(transform(self.leftExpr))
            res.append(' ')
            res.append(self.op)
            res.append(' ')
        res.append('...')
        if self.rightExpr:
            res.append(' ')
            res.append(self.op)
            res.append(' ')
            res.append(transform(self.rightExpr))
        res.append(')')
        return ''.join(res)

    def get_id(self, version: int) -> str:
        assert version >= 3
        if version == 3:
            return str(self)
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
        res.append(_id_operator_v2[self.op])
        if self.leftExpr:
            res.append(self.leftExpr.get_id(version))
        if self.rightExpr:
            res.append(self.rightExpr.get_id(version))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('(', '(')
        if self.leftExpr:
            self.leftExpr.describe_signature(signode, mode, env, symbol)
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_operator(self.op, self.op)
            signode += addnodes.desc_sig_space()
        signode += addnodes.desc_sig_punctuation('...', '...')
        if self.rightExpr:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_operator(self.op, self.op)
            signode += addnodes.desc_sig_space()
            self.rightExpr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTParenExpr(ASTExpression):
    def __init__(self, expr: ASTExpression):
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


# Postfix expressions
################################################################################

class ASTPostfixOp(ASTBase):
    def get_id(self, idPrefix: str, version: int) -> str:
        raise NotImplementedError(repr(self))

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))


class ASTPostfixArray(ASTPostfixOp):
    def __init__(self, expr: ASTExpression):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return '[' + transform(self.expr) + ']'

    def get_id(self, idPrefix: str, version: int) -> str:
        return 'ix' + idPrefix + self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('[', '[')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(']', ']')


class ASTPostfixMember(ASTPostfixOp):
    def __init__(self, name: ASTNestedName):
        self.name = name

    def _stringify(self, transform: StringifyTransform) -> str:
        return '.' + transform(self.name)

    def get_id(self, idPrefix: str, version: int) -> str:
        return 'dt' + idPrefix + self.name.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('.', '.')
        self.name.describe_signature(signode, 'noneIsName', env, symbol)


class ASTPostfixMemberOfPointer(ASTPostfixOp):
    def __init__(self, name: ASTNestedName):
        self.name = name

    def _stringify(self, transform: StringifyTransform) -> str:
        return '->' + transform(self.name)

    def get_id(self, idPrefix: str, version: int) -> str:
        return 'pt' + idPrefix + self.name.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('->', '->')
        self.name.describe_signature(signode, 'noneIsName', env, symbol)


class ASTPostfixInc(ASTPostfixOp):
    def _stringify(self, transform: StringifyTransform) -> str:
        return '++'

    def get_id(self, idPrefix: str, version: int) -> str:
        return 'pp' + idPrefix

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('++', '++')


class ASTPostfixDec(ASTPostfixOp):
    def _stringify(self, transform: StringifyTransform) -> str:
        return '--'

    def get_id(self, idPrefix: str, version: int) -> str:
        return 'mm' + idPrefix

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_operator('--', '--')


class ASTPostfixCallExpr(ASTPostfixOp):
    def __init__(self, lst: ASTParenExprList | ASTBracedInitList) -> None:
        self.lst = lst

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.lst)

    def get_id(self, idPrefix: str, version: int) -> str:
        res = ['cl', idPrefix]
        for e in self.lst.exprs:
            res.append(e.get_id(version))
        res.append('E')
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.lst.describe_signature(signode, mode, env, symbol)


class ASTPostfixExpr(ASTExpression):
    def __init__(self, prefix: ASTType, postFixes: list[ASTPostfixOp]):
        self.prefix = prefix
        self.postFixes = postFixes

    def _stringify(self, transform: StringifyTransform) -> str:
        res = [transform(self.prefix)]
        for p in self.postFixes:
            res.append(transform(p))
        return ''.join(res)

    def get_id(self, version: int) -> str:
        id = self.prefix.get_id(version)
        for p in self.postFixes:
            id = p.get_id(id, version)
        return id

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.prefix.describe_signature(signode, mode, env, symbol)
        for p in self.postFixes:
            p.describe_signature(signode, mode, env, symbol)


class ASTExplicitCast(ASTExpression):
    def __init__(self, cast: str, typ: ASTType, expr: ASTExpression):
        assert cast in _id_explicit_cast
        self.cast = cast
        self.typ = typ
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = [self.cast]
        res.append('<')
        res.append(transform(self.typ))
        res.append('>(')
        res.append(transform(self.expr))
        res.append(')')
        return ''.join(res)

    def get_id(self, version: int) -> str:
        return (_id_explicit_cast[self.cast] +
                self.typ.get_id(version) +
                self.expr.get_id(version))

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword(self.cast, self.cast)
        signode += addnodes.desc_sig_punctuation('<', '<')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation('>', '>')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTTypeId(ASTExpression):
    def __init__(self, typeOrExpr: ASTType | ASTExpression, isType: bool):
        self.typeOrExpr = typeOrExpr
        self.isType = isType

    def _stringify(self, transform: StringifyTransform) -> str:
        return 'typeid(' + transform(self.typeOrExpr) + ')'

    def get_id(self, version: int) -> str:
        prefix = 'ti' if self.isType else 'te'
        return prefix + self.typeOrExpr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('typeid', 'typeid')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typeOrExpr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


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

    def get_id(self, version: int) -> str:
        return _id_operator_unary_v2[self.op] + self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.op[0] in 'cn':
            signode += addnodes.desc_sig_keyword(self.op, self.op)
            signode += addnodes.desc_sig_space()
        else:
            signode += addnodes.desc_sig_operator(self.op, self.op)
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTSizeofParamPack(ASTExpression):
    def __init__(self, identifier: ASTIdentifier):
        self.identifier = identifier

    def _stringify(self, transform: StringifyTransform) -> str:
        return "sizeof...(" + transform(self.identifier) + ")"

    def get_id(self, version: int) -> str:
        return 'sZ' + self.identifier.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('sizeof', 'sizeof')
        signode += addnodes.desc_sig_punctuation('...', '...')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.identifier.describe_signature(signode, 'markType', env,
                                           symbol=symbol, prefix="", templateArgs="")
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTSizeofType(ASTExpression):
    def __init__(self, typ: ASTType):
        self.typ = typ

    def _stringify(self, transform: StringifyTransform) -> str:
        return "sizeof(" + transform(self.typ) + ")"

    def get_id(self, version: int) -> str:
        return 'st' + self.typ.get_id(version)

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

    def get_id(self, version: int) -> str:
        return 'sz' + self.expr.get_id(version)

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

    def get_id(self, version: int) -> str:
        return 'at' + self.typ.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('alignof', 'alignof')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTNoexceptExpr(ASTExpression):
    def __init__(self, expr: ASTExpression):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return 'noexcept(' + transform(self.expr) + ')'

    def get_id(self, version: int) -> str:
        return 'nx' + self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('noexcept', 'noexcept')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTNewExpr(ASTExpression):
    def __init__(self, rooted: bool, isNewTypeId: bool, typ: ASTType,
                 initList: ASTParenExprList | ASTBracedInitList) -> None:
        self.rooted = rooted
        self.isNewTypeId = isNewTypeId
        self.typ = typ
        self.initList = initList

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.rooted:
            res.append('::')
        res.append('new ')
        # TODO: placement
        if self.isNewTypeId:
            res.append(transform(self.typ))
        else:
            raise AssertionError
        if self.initList is not None:
            res.append(transform(self.initList))
        return ''.join(res)

    def get_id(self, version: int) -> str:
        # the array part will be in the type mangling, so na is not used
        res = ['nw']
        # TODO: placement
        res.append('_')
        res.append(self.typ.get_id(version))
        if self.initList is not None:
            res.append(self.initList.get_id(version))
        else:
            res.append('E')
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.rooted:
            signode += addnodes.desc_sig_punctuation('::', '::')
        signode += addnodes.desc_sig_keyword('new', 'new')
        signode += addnodes.desc_sig_space()
        # TODO: placement
        if self.isNewTypeId:
            self.typ.describe_signature(signode, mode, env, symbol)
        else:
            raise AssertionError
        if self.initList is not None:
            self.initList.describe_signature(signode, mode, env, symbol)


class ASTDeleteExpr(ASTExpression):
    def __init__(self, rooted: bool, array: bool, expr: ASTExpression):
        self.rooted = rooted
        self.array = array
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.rooted:
            res.append('::')
        res.append('delete ')
        if self.array:
            res.append('[] ')
        res.append(transform(self.expr))
        return ''.join(res)

    def get_id(self, version: int) -> str:
        if self.array:
            id = "da"
        else:
            id = "dl"
        return id + self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.rooted:
            signode += addnodes.desc_sig_punctuation('::', '::')
        signode += addnodes.desc_sig_keyword('delete', 'delete')
        signode += addnodes.desc_sig_space()
        if self.array:
            signode += addnodes.desc_sig_punctuation('[]', '[]')
            signode += addnodes.desc_sig_space()
        self.expr.describe_signature(signode, mode, env, symbol)


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

    def get_id(self, version: int) -> str:
        return 'cv' + self.typ.get_id(version) + self.expr.get_id(version)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.typ.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')
        self.expr.describe_signature(signode, mode, env, symbol)


class ASTBinOpExpr(ASTExpression):
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

    def get_id(self, version: int) -> str:
        assert version >= 2
        res = []
        for i in range(len(self.ops)):
            res.append(_id_operator_v2[self.ops[i]])
            res.append(self.exprs[i].get_id(version))
        res.append(self.exprs[-1].get_id(version))
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


class ASTConditionalExpr(ASTExpression):
    def __init__(self, ifExpr: ASTExpression, thenExpr: ASTExpression,
                 elseExpr: ASTExpression):
        self.ifExpr = ifExpr
        self.thenExpr = thenExpr
        self.elseExpr = elseExpr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.ifExpr))
        res.append(' ? ')
        res.append(transform(self.thenExpr))
        res.append(' : ')
        res.append(transform(self.elseExpr))
        return ''.join(res)

    def get_id(self, version: int) -> str:
        assert version >= 2
        res = []
        res.append(_id_operator_v2['?'])
        res.append(self.ifExpr.get_id(version))
        res.append(self.thenExpr.get_id(version))
        res.append(self.elseExpr.get_id(version))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.ifExpr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_space()
        signode += addnodes.desc_sig_operator('?', '?')
        signode += addnodes.desc_sig_space()
        self.thenExpr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_space()
        signode += addnodes.desc_sig_operator(':', ':')
        signode += addnodes.desc_sig_space()
        self.elseExpr.describe_signature(signode, mode, env, symbol)


class ASTBracedInitList(ASTBase):
    def __init__(self, exprs: list[ASTExpression | ASTBracedInitList],
                 trailingComma: bool) -> None:
        self.exprs = exprs
        self.trailingComma = trailingComma

    def get_id(self, version: int) -> str:
        return "il%sE" % ''.join(e.get_id(version) for e in self.exprs)

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


class ASTAssignmentExpr(ASTExpression):
    def __init__(self, leftExpr: ASTExpression, op: str,
                 rightExpr: ASTExpression | ASTBracedInitList):
        self.leftExpr = leftExpr
        self.op = op
        self.rightExpr = rightExpr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.leftExpr))
        res.append(' ')
        res.append(self.op)
        res.append(' ')
        res.append(transform(self.rightExpr))
        return ''.join(res)

    def get_id(self, version: int) -> str:
        # we end up generating the ID from left to right, instead of right to left
        res = []
        res.append(_id_operator_v2[self.op])
        res.append(self.leftExpr.get_id(version))
        res.append(self.rightExpr.get_id(version))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.leftExpr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_space()
        if ord(self.op[0]) >= ord('a') and ord(self.op[0]) <= ord('z'):
            signode += addnodes.desc_sig_keyword(self.op, self.op)
        else:
            signode += addnodes.desc_sig_operator(self.op, self.op)
        signode += addnodes.desc_sig_space()
        self.rightExpr.describe_signature(signode, mode, env, symbol)


class ASTCommaExpr(ASTExpression):
    def __init__(self, exprs: list[ASTExpression]):
        assert len(exprs) > 0
        self.exprs = exprs

    def _stringify(self, transform: StringifyTransform) -> str:
        return ', '.join(transform(e) for e in self.exprs)

    def get_id(self, version: int) -> str:
        id_ = _id_operator_v2[',']
        res = []
        for i in range(len(self.exprs) - 1):
            res.append(id_)
            res.append(self.exprs[i].get_id(version))
        res.append(self.exprs[-1].get_id(version))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.exprs[0].describe_signature(signode, mode, env, symbol)
        for i in range(1, len(self.exprs)):
            signode += addnodes.desc_sig_punctuation(',', ',')
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

# Things for ASTNestedName
################################################################################

class ASTOperator(ASTBase):
    def is_anon(self) -> bool:
        return False

    def is_operator(self) -> bool:
        return True

    def get_id(self, version: int) -> str:
        raise NotImplementedError

    def _describe_identifier(self, signode: TextElement, identnode: TextElement,
                             env: BuildEnvironment, symbol: Symbol) -> None:
        """Render the prefix into signode, and the last part into identnode."""
        raise NotImplementedError

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, prefix: str, templateArgs: str,
                           symbol: Symbol) -> None:
        verify_description_mode(mode)
        if mode == 'lastIsName':
            mainName = addnodes.desc_name()
            self._describe_identifier(mainName, mainName, env, symbol)
            signode += mainName
        elif mode == 'markType':
            targetText = prefix + str(self) + templateArgs
            pnode = addnodes.pending_xref('', refdomain='cpp',
                                          reftype='identifier',
                                          reftarget=targetText, modname=None,
                                          classname=None)
            pnode['cpp:parent_key'] = symbol.get_lookup_key()
            # Render the identifier part, but collapse it into a string
            # and make that the a link to this operator.
            # E.g., if it is 'operator SomeType', then 'SomeType' becomes
            # a link to the operator, not to 'SomeType'.
            container = nodes.literal()
            self._describe_identifier(signode, container, env, symbol)
            txt = container.astext()
            pnode += addnodes.desc_name(txt, txt)
            signode += pnode
        else:
            addName = addnodes.desc_addname()
            self._describe_identifier(addName, addName, env, symbol)
            signode += addName


class ASTOperatorBuildIn(ASTOperator):
    def __init__(self, op: str) -> None:
        self.op = op

    def get_id(self, version: int) -> str:
        if version == 1:
            ids = _id_operator_v1
            if self.op not in ids:
                raise NoOldIdError
        else:
            ids = _id_operator_v2
        if self.op not in ids:
            raise Exception('Internal error: Built-in operator "%s" can not '
                            'be mapped to an id.' % self.op)
        return ids[self.op]

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.op in ('new', 'new[]', 'delete', 'delete[]') or self.op[0] in "abcnox":
            return 'operator ' + self.op
        else:
            return 'operator' + self.op

    def _describe_identifier(self, signode: TextElement, identnode: TextElement,
                             env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('operator', 'operator')
        if self.op in ('new', 'new[]', 'delete', 'delete[]') or self.op[0] in "abcnox":
            signode += addnodes.desc_sig_space()
        identnode += addnodes.desc_sig_operator(self.op, self.op)


class ASTOperatorLiteral(ASTOperator):
    def __init__(self, identifier: ASTIdentifier) -> None:
        self.identifier = identifier

    def get_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError
        return 'li' + self.identifier.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return 'operator""' + transform(self.identifier)

    def _describe_identifier(self, signode: TextElement, identnode: TextElement,
                             env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('operator', 'operator')
        signode += addnodes.desc_sig_literal_string('""', '""')
        self.identifier.describe_signature(identnode, 'markType', env, '', '', symbol)


class ASTOperatorType(ASTOperator):
    def __init__(self, type: ASTType) -> None:
        self.type = type

    def get_id(self, version: int) -> str:
        if version == 1:
            return 'castto-%s-operator' % self.type.get_id(version)
        else:
            return 'cv' + self.type.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return ''.join(['operator ', transform(self.type)])

    def get_name_no_template(self) -> str:
        return str(self)

    def _describe_identifier(self, signode: TextElement, identnode: TextElement,
                             env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('operator', 'operator')
        signode += addnodes.desc_sig_space()
        self.type.describe_signature(identnode, 'markType', env, symbol)


class ASTTemplateArgConstant(ASTBase):
    def __init__(self, value: ASTExpression) -> None:
        self.value = value

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.value)

    def get_id(self, version: int) -> str:
        if version == 1:
            return str(self).replace(' ', '-')
        if version == 2:
            return 'X' + str(self) + 'E'
        return 'X' + self.value.get_id(version) + 'E'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.value.describe_signature(signode, mode, env, symbol)


class ASTTemplateArgs(ASTBase):
    def __init__(self, args: list[ASTType | ASTTemplateArgConstant],
                 packExpansion: bool) -> None:
        assert args is not None
        self.args = args
        self.packExpansion = packExpansion

    def get_id(self, version: int) -> str:
        if version == 1:
            res = []
            res.append(':')
            res.append('.'.join(a.get_id(version) for a in self.args))
            res.append(':')
            return ''.join(res)

        res = []
        res.append('I')
        if len(self.args) > 0:
            for a in self.args[:-1]:
                res.append(a.get_id(version))
            if self.packExpansion:
                res.append('J')
            res.append(self.args[-1].get_id(version))
            if self.packExpansion:
                res.append('E')
        res.append('E')
        return ''.join(res)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ', '.join(transform(a) for a in self.args)
        if self.packExpansion:
            res += '...'
        return '<' + res + '>'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('<', '<')
        first = True
        for a in self.args:
            if not first:
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            first = False
            a.describe_signature(signode, 'markType', env, symbol=symbol)
        if self.packExpansion:
            signode += addnodes.desc_sig_punctuation('...', '...')
        signode += addnodes.desc_sig_punctuation('>', '>')


# Main part of declarations
################################################################################

class ASTTrailingTypeSpec(ASTBase):
    def get_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))


class ASTTrailingTypeSpecFundamental(ASTTrailingTypeSpec):
    def __init__(self, names: list[str], canonNames: list[str]) -> None:
        assert len(names) != 0
        assert len(names) == len(canonNames), (names, canonNames)
        self.names = names
        # the canonical name list is for ID lookup
        self.canonNames = canonNames

    def _stringify(self, transform: StringifyTransform) -> str:
        return ' '.join(self.names)

    def get_id(self, version: int) -> str:
        if version == 1:
            res = []
            for a in self.canonNames:
                if a in _id_fundamental_v1:
                    res.append(_id_fundamental_v1[a])
                else:
                    res.append(a)
            return '-'.join(res)

        txt = ' '.join(self.canonNames)
        if txt not in _id_fundamental_v2:
            raise Exception(
                'Semi-internal error: Fundamental type "%s" can not be mapped '
                'to an ID. Is it a true fundamental type? If not so, the '
                'parser should have rejected it.' % txt)
        return _id_fundamental_v2[txt]

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        first = True
        for n in self.names:
            if not first:
                signode += addnodes.desc_sig_space()
            else:
                first = False
            signode += addnodes.desc_sig_keyword_type(n, n)


class ASTTrailingTypeSpecDecltypeAuto(ASTTrailingTypeSpec):
    def _stringify(self, transform: StringifyTransform) -> str:
        return 'decltype(auto)'

    def get_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError
        return 'Dc'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('decltype', 'decltype')
        signode += addnodes.desc_sig_punctuation('(', '(')
        signode += addnodes.desc_sig_keyword('auto', 'auto')
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTTrailingTypeSpecDecltype(ASTTrailingTypeSpec):
    def __init__(self, expr: ASTExpression):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return 'decltype(' + transform(self.expr) + ')'

    def get_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError
        return 'DT' + self.expr.get_id(version) + "E"

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('decltype', 'decltype')
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')


class ASTTrailingTypeSpecName(ASTTrailingTypeSpec):
    def __init__(self, prefix: str, nestedName: ASTNestedName,
                 placeholderType: str | None) -> None:
        self.prefix = prefix
        self.nestedName = nestedName
        self.placeholderType = placeholderType

    @property
    def name(self) -> ASTNestedName:
        return self.nestedName

    def get_id(self, version: int) -> str:
        return self.nestedName.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.prefix:
            res.append(self.prefix)
            res.append(' ')
        res.append(transform(self.nestedName))
        if self.placeholderType is not None:
            res.append(' ')
            res.append(self.placeholderType)
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.prefix:
            signode += addnodes.desc_sig_keyword(self.prefix, self.prefix)
            signode += addnodes.desc_sig_space()
        self.nestedName.describe_signature(signode, mode, env, symbol=symbol)
        if self.placeholderType is not None:
            signode += addnodes.desc_sig_space()
            if self.placeholderType == 'auto':
                signode += addnodes.desc_sig_keyword('auto', 'auto')
            elif self.placeholderType == 'decltype(auto)':
                signode += addnodes.desc_sig_keyword('decltype', 'decltype')
                signode += addnodes.desc_sig_punctuation('(', '(')
                signode += addnodes.desc_sig_keyword('auto', 'auto')
                signode += addnodes.desc_sig_punctuation(')', ')')
            else:
                raise AssertionError(self.placeholderType)


class ASTFunctionParameter(ASTBase):
    def __init__(self, arg: ASTTypeWithInit | ASTTemplateParamConstrainedTypeWithInit,
                 ellipsis: bool = False) -> None:
        self.arg = arg
        self.ellipsis = ellipsis

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=False)
        # else, do the usual
        if self.ellipsis:
            return 'z'
        else:
            return self.arg.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.ellipsis:
            return '...'
        else:
            return transform(self.arg)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.ellipsis:
            signode += addnodes.desc_sig_punctuation('...', '...')
        else:
            self.arg.describe_signature(signode, mode, env, symbol=symbol)


class ASTNoexceptSpec(ASTBase):
    def __init__(self, expr: ASTExpression | None):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.expr:
            return 'noexcept(' + transform(self.expr) + ')'
        return 'noexcept'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('noexcept', 'noexcept')
        if self.expr:
            signode += addnodes.desc_sig_punctuation('(', '(')
            self.expr.describe_signature(signode, 'markType', env, symbol)
            signode += addnodes.desc_sig_punctuation(')', ')')


class ASTParametersQualifiers(ASTBase):
    def __init__(self, args: list[ASTFunctionParameter], volatile: bool, const: bool,
                 refQual: str | None, exceptionSpec: ASTNoexceptSpec,
                 trailingReturn: ASTType,
                 override: bool, final: bool, attrs: ASTAttributeList,
                 initializer: str | None) -> None:
        self.args = args
        self.volatile = volatile
        self.const = const
        self.refQual = refQual
        self.exceptionSpec = exceptionSpec
        self.trailingReturn = trailingReturn
        self.override = override
        self.final = final
        self.attrs = attrs
        self.initializer = initializer

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.args

    def get_modifiers_id(self, version: int) -> str:
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
        return ''.join(res)

    def get_param_id(self, version: int) -> str:
        if version == 1:
            if len(self.args) == 0:
                return ''
            else:
                return '__' + '.'.join(a.get_id(version) for a in self.args)
        if len(self.args) == 0:
            return 'v'
        else:
            return ''.join(a.get_id(version) for a in self.args)

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
        if self.volatile:
            res.append(' volatile')
        if self.const:
            res.append(' const')
        if self.refQual:
            res.append(' ')
            res.append(self.refQual)
        if self.exceptionSpec:
            res.append(' ')
            res.append(transform(self.exceptionSpec))
        if self.trailingReturn:
            res.append(' -> ')
            res.append(transform(self.trailingReturn))
        if self.final:
            res.append(' final')
        if self.override:
            res.append(' override')
        if len(self.attrs) != 0:
            res.append(' ')
            res.append(transform(self.attrs))
        if self.initializer:
            res.append(' = ')
            res.append(self.initializer)
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

        def _add_anno(signode: TextElement, text: str) -> None:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_keyword(text, text)

        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            _add_anno(signode, 'const')
        if self.refQual:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation(self.refQual, self.refQual)
        if self.exceptionSpec:
            signode += addnodes.desc_sig_space()
            self.exceptionSpec.describe_signature(signode, mode, env, symbol)
        if self.trailingReturn:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_operator('->', '->')
            signode += addnodes.desc_sig_space()
            self.trailingReturn.describe_signature(signode, mode, env, symbol)
        if self.final:
            _add_anno(signode, 'final')
        if self.override:
            _add_anno(signode, 'override')
        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
            self.attrs.describe_signature(signode)
        if self.initializer:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('=', '=')
            signode += addnodes.desc_sig_space()
            assert self.initializer in ('0', 'delete', 'default')
            if self.initializer == '0':
                signode += addnodes.desc_sig_literal_number('0', '0')
            else:
                signode += addnodes.desc_sig_keyword(self.initializer, self.initializer)


class ASTExplicitSpec(ASTBase):
    def __init__(self, expr: ASTExpression | None) -> None:
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['explicit']
        if self.expr is not None:
            res.append('(')
            res.append(transform(self.expr))
            res.append(')')
        return ''.join(res)

    def describe_signature(self, signode: TextElement,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('explicit', 'explicit')
        if self.expr is not None:
            signode += addnodes.desc_sig_punctuation('(', '(')
            self.expr.describe_signature(signode, 'markType', env, symbol)
            signode += addnodes.desc_sig_punctuation(')', ')')


class ASTDeclSpecsSimple(ASTBase):
    def __init__(self, storage: str, threadLocal: bool, inline: bool, virtual: bool,
                 explicitSpec: ASTExplicitSpec | None,
                 consteval: bool, constexpr: bool, constinit: bool,
                 volatile: bool, const: bool, friend: bool,
                 attrs: ASTAttributeList) -> None:
        self.storage = storage
        self.threadLocal = threadLocal
        self.inline = inline
        self.virtual = virtual
        self.explicitSpec = explicitSpec
        self.consteval = consteval
        self.constexpr = constexpr
        self.constinit = constinit
        self.volatile = volatile
        self.const = const
        self.friend = friend
        self.attrs = attrs

    def mergeWith(self, other: ASTDeclSpecsSimple) -> ASTDeclSpecsSimple:
        if not other:
            return self
        return ASTDeclSpecsSimple(self.storage or other.storage,
                                  self.threadLocal or other.threadLocal,
                                  self.inline or other.inline,
                                  self.virtual or other.virtual,
                                  self.explicitSpec or other.explicitSpec,
                                  self.consteval or other.consteval,
                                  self.constexpr or other.constexpr,
                                  self.constinit or other.constinit,
                                  self.volatile or other.volatile,
                                  self.const or other.const,
                                  self.friend or other.friend,
                                  self.attrs + other.attrs)

    def _stringify(self, transform: StringifyTransform) -> str:
        res: list[str] = []
        if len(self.attrs) != 0:
            res.append(transform(self.attrs))
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
        if self.explicitSpec:
            res.append(transform(self.explicitSpec))
        if self.consteval:
            res.append('consteval')
        if self.constexpr:
            res.append('constexpr')
        if self.constinit:
            res.append('constinit')
        if self.volatile:
            res.append('volatile')
        if self.const:
            res.append('const')
        return ' '.join(res)

    def describe_signature(self, signode: TextElement,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.attrs.describe_signature(signode)
        addSpace = len(self.attrs) != 0

        def _add(signode: TextElement, text: str) -> bool:
            if addSpace:
                signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_keyword(text, text)
            return True

        if self.storage:
            addSpace = _add(signode, self.storage)
        if self.threadLocal:
            addSpace = _add(signode, 'thread_local')
        if self.inline:
            addSpace = _add(signode, 'inline')
        if self.friend:
            addSpace = _add(signode, 'friend')
        if self.virtual:
            addSpace = _add(signode, 'virtual')
        if self.explicitSpec:
            if addSpace:
                signode += addnodes.desc_sig_space()
            self.explicitSpec.describe_signature(signode, env, symbol)
            addSpace = True
        if self.consteval:
            addSpace = _add(signode, 'consteval')
        if self.constexpr:
            addSpace = _add(signode, 'constexpr')
        if self.constinit:
            addSpace = _add(signode, 'constinit')
        if self.volatile:
            addSpace = _add(signode, 'volatile')
        if self.const:
            addSpace = _add(signode, 'const')


class ASTDeclSpecs(ASTBase):
    def __init__(self, outer: str,
                 leftSpecs: ASTDeclSpecsSimple, rightSpecs: ASTDeclSpecsSimple,
                 trailing: ASTTrailingTypeSpec) -> None:
        # leftSpecs and rightSpecs are used for output
        # allSpecs are used for id generation
        self.outer = outer
        self.leftSpecs = leftSpecs
        self.rightSpecs = rightSpecs
        self.allSpecs = self.leftSpecs.mergeWith(self.rightSpecs)
        self.trailingTypeSpec = trailing

    def get_id(self, version: int) -> str:
        if version == 1:
            res = []
            res.append(self.trailingTypeSpec.get_id(version))
            if self.allSpecs.volatile:
                res.append('V')
            if self.allSpecs.const:
                res.append('C')
            return ''.join(res)
        res = []
        if self.allSpecs.volatile:
            res.append('V')
        if self.allSpecs.const:
            res.append('K')
        if self.trailingTypeSpec is not None:
            res.append(self.trailingTypeSpec.get_id(version))
        return ''.join(res)

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
        numChildren = len(signode)
        self.leftSpecs.describe_signature(signode, env, symbol)
        addSpace = len(signode) != numChildren

        if self.trailingTypeSpec:
            if addSpace:
                signode += addnodes.desc_sig_space()
            numChildren = len(signode)
            self.trailingTypeSpec.describe_signature(signode, mode, env,
                                                     symbol=symbol)
            addSpace = len(signode) != numChildren

            if len(str(self.rightSpecs)) > 0:
                if addSpace:
                    signode += addnodes.desc_sig_space()
                self.rightSpecs.describe_signature(signode, env, symbol)


# Declarator
################################################################################

class ASTArray(ASTBase):
    def __init__(self, size: ASTExpression):
        self.size = size

    def _stringify(self, transform: StringifyTransform) -> str:
        if self.size:
            return '[' + transform(self.size) + ']'
        else:
            return '[]'

    def get_id(self, version: int) -> str:
        if version == 1:
            return 'A'
        if version == 2:
            if self.size:
                return 'A' + str(self.size) + '_'
            else:
                return 'A_'
        if self.size:
            return 'A' + self.size.get_id(version) + '_'
        else:
            return 'A_'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('[', '[')
        if self.size:
            self.size.describe_signature(signode, 'markType', env, symbol)
        signode += addnodes.desc_sig_punctuation(']', ']')


class ASTDeclarator(ASTBase):
    @property
    def name(self) -> ASTNestedName:
        raise NotImplementedError(repr(self))

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        raise NotImplementedError(repr(self))

    @property
    def isPack(self) -> bool:
        raise NotImplementedError(repr(self))

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        raise NotImplementedError(repr(self))

    @property
    def trailingReturn(self) -> ASTType:
        raise NotImplementedError(repr(self))

    def require_space_after_declSpecs(self) -> bool:
        raise NotImplementedError(repr(self))

    def get_modifiers_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def get_param_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def get_ptr_suffix_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        raise NotImplementedError(repr(self))

    def is_function_type(self) -> bool:
        raise NotImplementedError(repr(self))

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))


class ASTDeclaratorNameParamQual(ASTDeclarator):
    def __init__(self, declId: ASTNestedName,
                 arrayOps: list[ASTArray],
                 paramQual: ASTParametersQualifiers) -> None:
        self.declId = declId
        self.arrayOps = arrayOps
        self.paramQual = paramQual

    @property
    def name(self) -> ASTNestedName:
        return self.declId

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.declId = name

    @property
    def isPack(self) -> bool:
        return False

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.paramQual.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.paramQual.trailingReturn

    # only the modifiers for a function, e.g.,
    def get_modifiers_id(self, version: int) -> str:
        # cv-qualifiers
        if self.paramQual:
            return self.paramQual.get_modifiers_id(version)
        raise Exception("This should only be called on a function: %s" % self)

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        if self.paramQual:
            return self.paramQual.get_param_id(version)
        else:
            return ''

    def get_ptr_suffix_id(self, version: int) -> str:  # only the array specifiers
        return ''.join(a.get_id(version) for a in self.arrayOps)

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        assert version >= 2
        res = []
        # TODO: can we actually have both array ops and paramQual?
        res.append(self.get_ptr_suffix_id(version))
        if self.paramQual:
            res.append(self.get_modifiers_id(version))
            res.append('F')
            res.append(returnTypeId)
            res.append(self.get_param_id(version))
            res.append('E')
        else:
            res.append(returnTypeId)
        return ''.join(res)

    # ------------------------------------------------------------------------

    def require_space_after_declSpecs(self) -> bool:
        return self.declId is not None

    def is_function_type(self) -> bool:
        return self.paramQual is not None

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.declId:
            res.append(transform(self.declId))
        for op in self.arrayOps:
            res.append(transform(op))
        if self.paramQual:
            res.append(transform(self.paramQual))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.declId:
            self.declId.describe_signature(signode, mode, env, symbol)
        for op in self.arrayOps:
            op.describe_signature(signode, mode, env, symbol)
        if self.paramQual:
            self.paramQual.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorNameBitField(ASTDeclarator):
    def __init__(self, declId: ASTNestedName, size: ASTExpression):
        self.declId = declId
        self.size = size

    @property
    def name(self) -> ASTNestedName:
        return self.declId

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.declId = name

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        return ''

    def get_ptr_suffix_id(self, version: int) -> str:  # only the array specifiers
        return ''

    # ------------------------------------------------------------------------

    def require_space_after_declSpecs(self) -> bool:
        return self.declId is not None

    def is_function_type(self) -> bool:
        return False

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
    def __init__(self, next: ASTDeclarator, volatile: bool, const: bool,
                 attrs: ASTAttributeList) -> None:
        assert next
        self.next = next
        self.volatile = volatile
        self.const = const
        self.attrs = attrs

    @property
    def name(self) -> ASTNestedName:
        return self.next.name

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.next.name = name

    @property
    def isPack(self) -> bool:
        return self.next.isPack

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.next.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.next.trailingReturn

    def require_space_after_declSpecs(self) -> bool:
        return self.next.require_space_after_declSpecs()

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['*']
        res.append(transform(self.attrs))
        if len(self.attrs) != 0 and (self.volatile or self.const):
            res.append(' ')
        if self.volatile:
            res.append('volatile')
        if self.const:
            if self.volatile:
                res.append(' ')
            res.append('const')
        if self.const or self.volatile or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs():
                res.append(' ')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version: int) -> str:
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version: int) -> str:
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version: int) -> str:
        if version == 1:
            res = ['P']
            if self.volatile:
                res.append('V')
            if self.const:
                res.append('C')
            res.append(self.next.get_ptr_suffix_id(version))
            return ''.join(res)

        res = [self.next.get_ptr_suffix_id(version)]
        res.append('P')
        if self.volatile:
            res.append('V')
        if self.const:
            res.append('C')
        return ''.join(res)

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        # ReturnType *next, so we are part of the return type of 'next
        res = ['P']
        if self.volatile:
            res.append('V')
        if self.const:
            res.append('C')
        res.append(returnTypeId)
        return self.next.get_type_id(version, returnTypeId=''.join(res))

    def is_function_type(self) -> bool:
        return self.next.is_function_type()

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('*', '*')
        self.attrs.describe_signature(signode)
        if len(self.attrs) != 0 and (self.volatile or self.const):
            signode += addnodes.desc_sig_space()

        def _add_anno(signode: TextElement, text: str) -> None:
            signode += addnodes.desc_sig_keyword(text, text)
        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            if self.volatile:
                signode += addnodes.desc_sig_space()
            _add_anno(signode, 'const')
        if self.const or self.volatile or len(self.attrs) > 0:
            if self.next.require_space_after_declSpecs():
                signode += addnodes.desc_sig_space()
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorRef(ASTDeclarator):
    def __init__(self, next: ASTDeclarator, attrs: ASTAttributeList) -> None:
        assert next
        self.next = next
        self.attrs = attrs

    @property
    def name(self) -> ASTNestedName:
        return self.next.name

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.next.name = name

    @property
    def isPack(self) -> bool:
        return self.next.isPack

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.next.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.next.trailingReturn

    def require_space_after_declSpecs(self) -> bool:
        return self.next.require_space_after_declSpecs()

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['&']
        res.append(transform(self.attrs))
        if len(self.attrs) != 0 and self.next.require_space_after_declSpecs():
            res.append(' ')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version: int) -> str:
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version: int) -> str:
        if version == 1:
            return 'R' + self.next.get_ptr_suffix_id(version)
        else:
            return self.next.get_ptr_suffix_id(version) + 'R'

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        assert version >= 2
        # ReturnType &next, so we are part of the return type of 'next
        return self.next.get_type_id(version, returnTypeId='R' + returnTypeId)

    def is_function_type(self) -> bool:
        return self.next.is_function_type()

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('&', '&')
        self.attrs.describe_signature(signode)
        if len(self.attrs) > 0 and self.next.require_space_after_declSpecs():
            signode += addnodes.desc_sig_space()
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorParamPack(ASTDeclarator):
    def __init__(self, next: ASTDeclarator) -> None:
        assert next
        self.next = next

    @property
    def name(self) -> ASTNestedName:
        return self.next.name

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.next.name = name

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.next.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.next.trailingReturn

    @property
    def isPack(self) -> bool:
        return True

    def require_space_after_declSpecs(self) -> bool:
        return False

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.next)
        if self.next.name:
            res = ' ' + res
        return '...' + res

    def get_modifiers_id(self, version: int) -> str:
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version: int) -> str:
        if version == 1:
            return 'Dp' + self.next.get_ptr_suffix_id(version)
        else:
            return self.next.get_ptr_suffix_id(version) + 'Dp'

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        assert version >= 2
        # ReturnType... next, so we are part of the return type of 'next
        return self.next.get_type_id(version, returnTypeId='Dp' + returnTypeId)

    def is_function_type(self) -> bool:
        return self.next.is_function_type()

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('...', '...')
        if self.next.name:
            signode += addnodes.desc_sig_space()
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorMemPtr(ASTDeclarator):
    def __init__(self, className: ASTNestedName,
                 const: bool, volatile: bool, next: ASTDeclarator) -> None:
        assert className
        assert next
        self.className = className
        self.const = const
        self.volatile = volatile
        self.next = next

    @property
    def name(self) -> ASTNestedName:
        return self.next.name

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.next.name = name

    @property
    def isPack(self):
        return self.next.isPack

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.next.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.next.trailingReturn

    def require_space_after_declSpecs(self) -> bool:
        return True

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.className))
        res.append('::*')
        if self.volatile:
            res.append('volatile')
        if self.const:
            if self.volatile:
                res.append(' ')
            res.append('const')
        if self.next.require_space_after_declSpecs():
            res.append(' ')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError
        return self.next.get_modifiers_id(version)

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        if version == 1:
            raise NoOldIdError
        return self.next.get_param_id(version)

    def get_ptr_suffix_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError
        raise NotImplementedError
        return self.next.get_ptr_suffix_id(version) + 'Dp'

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        assert version >= 2
        # ReturnType name::* next, so we are part of the return type of next
        nextReturnTypeId = ''
        if self.volatile:
            nextReturnTypeId += 'V'
        if self.const:
            nextReturnTypeId += 'K'
        nextReturnTypeId += 'M'
        nextReturnTypeId += self.className.get_id(version)
        nextReturnTypeId += returnTypeId
        return self.next.get_type_id(version, nextReturnTypeId)

    def is_function_type(self) -> bool:
        return self.next.is_function_type()

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.className.describe_signature(signode, 'markType', env, symbol)
        signode += addnodes.desc_sig_punctuation('::', '::')
        signode += addnodes.desc_sig_punctuation('*', '*')

        def _add_anno(signode: TextElement, text: str) -> None:
            signode += addnodes.desc_sig_keyword(text, text)
        if self.volatile:
            _add_anno(signode, 'volatile')
        if self.const:
            if self.volatile:
                signode += addnodes.desc_sig_space()
            _add_anno(signode, 'const')
        if self.next.require_space_after_declSpecs():
            signode += addnodes.desc_sig_space()
        self.next.describe_signature(signode, mode, env, symbol)


class ASTDeclaratorParen(ASTDeclarator):
    def __init__(self, inner: ASTDeclarator, next: ASTDeclarator) -> None:
        assert inner
        assert next
        self.inner = inner
        self.next = next
        # TODO: we assume the name, params, and qualifiers are in inner

    @property
    def name(self) -> ASTNestedName:
        return self.inner.name

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.inner.name = name

    @property
    def isPack(self):
        return self.inner.isPack or self.next.isPack

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.inner.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.inner.trailingReturn

    def require_space_after_declSpecs(self) -> bool:
        return True

    def _stringify(self, transform: StringifyTransform) -> str:
        res = ['(']
        res.append(transform(self.inner))
        res.append(')')
        res.append(transform(self.next))
        return ''.join(res)

    def get_modifiers_id(self, version: int) -> str:
        return self.inner.get_modifiers_id(version)

    def get_param_id(self, version: int) -> str:  # only the parameters (if any)
        return self.inner.get_param_id(version)

    def get_ptr_suffix_id(self, version: int) -> str:
        if version == 1:
            raise NoOldIdError  # TODO: was this implemented before?
            return self.next.get_ptr_suffix_id(version) + \
                self.inner.get_ptr_suffix_id(version)
        return self.inner.get_ptr_suffix_id(version) + \
            self.next.get_ptr_suffix_id(version)

    def get_type_id(self, version: int, returnTypeId: str) -> str:
        assert version >= 2
        # ReturnType (inner)next, so 'inner' returns everything outside
        nextId = self.next.get_type_id(version, returnTypeId)
        return self.inner.get_type_id(version, returnTypeId=nextId)

    def is_function_type(self) -> bool:
        return self.inner.is_function_type()

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        signode += addnodes.desc_sig_punctuation('(', '(')
        self.inner.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation(')', ')')
        self.next.describe_signature(signode, "noneIsName", env, symbol)


# Type and initializer stuff
##############################################################################################

class ASTPackExpansionExpr(ASTExpression):
    def __init__(self, expr: ASTExpression | ASTBracedInitList):
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.expr) + '...'

    def get_id(self, version: int) -> str:
        id = self.expr.get_id(version)
        return 'sp' + id

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.expr.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation('...', '...')


class ASTParenExprList(ASTBaseParenExprList):
    def __init__(self, exprs: list[ASTExpression | ASTBracedInitList]) -> None:
        self.exprs = exprs

    def get_id(self, version: int) -> str:
        return "pi%sE" % ''.join(e.get_id(version) for e in self.exprs)

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


class ASTInitializer(ASTBase):
    def __init__(self, value: ASTExpression | ASTBracedInitList,
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

    @name.setter
    def name(self, name: ASTNestedName) -> None:
        self.decl.name = name

    @property
    def isPack(self) -> bool:
        return self.decl.isPack

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        return self.decl.function_params

    @property
    def trailingReturn(self) -> ASTType:
        return self.decl.trailingReturn

    def get_id(self, version: int, objectType: str | None = None,
               symbol: Symbol | None = None) -> str:
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
                    raise AssertionError(objectType)
            else:  # only type encoding
                if self.decl.is_function_type():
                    raise NoOldIdError
                res.append(self.declSpecs.get_id(version))
                res.append(self.decl.get_ptr_suffix_id(version))
                res.append(self.decl.get_param_id(version))
            return ''.join(res)
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
                        if self.trailingReturn:
                            returnTypeId = self.trailingReturn.get_id(version)
                        else:
                            returnTypeId = self.declSpecs.get_id(version)
                        res.append(typeId)
                        res.append(returnTypeId)
                res.append(self.decl.get_param_id(version))
            elif objectType == 'type':  # just the name
                res.append(symbol.get_full_nested_name().get_id(version))
            else:
                raise AssertionError(objectType)
        else:  # only type encoding
            # the 'returnType' of a non-function type is simply just the last
            # type, i.e., for 'int*' it is 'int'
            returnTypeId = self.declSpecs.get_id(version)
            typeId = self.decl.get_type_id(version, returnTypeId)
            res.append(typeId)
        return ''.join(res)

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


class ASTTemplateParamConstrainedTypeWithInit(ASTBase):
    def __init__(self, type: ASTType, init: ASTType) -> None:
        assert type
        self.type = type
        self.init = init

    @property
    def name(self) -> ASTNestedName:
        return self.type.name

    @property
    def isPack(self) -> bool:
        return self.type.isPack

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
        # this is not part of the normal name mangling in C++
        assert version >= 2
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=False)
        else:
            return self.type.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.type)
        if self.init:
            res += " = "
            res += transform(self.init)
        return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.type.describe_signature(signode, mode, env, symbol)
        if self.init:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('=', '=')
            signode += addnodes.desc_sig_space()
            self.init.describe_signature(signode, mode, env, symbol)


class ASTTypeWithInit(ASTBase):
    def __init__(self, type: ASTType, init: ASTInitializer) -> None:
        self.type = type
        self.init = init

    @property
    def name(self) -> ASTNestedName:
        return self.type.name

    @property
    def isPack(self) -> bool:
        return self.type.isPack

    def get_id(self, version: int, objectType: str | None = None,
               symbol: Symbol | None = None) -> str:
        if objectType != 'member':
            return self.type.get_id(version, objectType)
        if version == 1:
            return (symbol.get_full_nested_name().get_id(version) + '__' +
                    self.type.get_id(version))
        return symbol.get_full_nested_name().get_id(version)

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


class ASTTypeUsing(ASTBase):
    def __init__(self, name: ASTNestedName, type: ASTType) -> None:
        self.name = name
        self.type = type

    def get_id(self, version: int, objectType: str | None = None,
               symbol: Symbol | None = None) -> str:
        if version == 1:
            raise NoOldIdError
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.name))
        if self.type:
            res.append(' = ')
            res.append(transform(self.type))
        return ''.join(res)

    def get_type_declaration_prefix(self) -> str:
        return 'using'

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.type:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('=', '=')
            signode += addnodes.desc_sig_space()
            self.type.describe_signature(signode, 'markType', env, symbol=symbol)


# Other declarations
##############################################################################################

class ASTConcept(ASTBase):
    def __init__(self, nestedName: ASTNestedName, initializer: ASTInitializer) -> None:
        self.nestedName = nestedName
        self.initializer = initializer

    @property
    def name(self) -> ASTNestedName:
        return self.nestedName

    def get_id(self, version: int, objectType: str | None = None,
               symbol: Symbol | None = None) -> str:
        if version == 1:
            raise NoOldIdError
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.nestedName)
        if self.initializer:
            res += transform(self.initializer)
        return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.nestedName.describe_signature(signode, mode, env, symbol)
        if self.initializer:
            self.initializer.describe_signature(signode, mode, env, symbol)


class ASTBaseClass(ASTBase):
    def __init__(self, name: ASTNestedName, visibility: str,
                 virtual: bool, pack: bool) -> None:
        self.name = name
        self.visibility = visibility
        self.virtual = virtual
        self.pack = pack

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.visibility is not None:
            res.append(self.visibility)
            res.append(' ')
        if self.virtual:
            res.append('virtual ')
        res.append(transform(self.name))
        if self.pack:
            res.append('...')
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        if self.visibility is not None:
            signode += addnodes.desc_sig_keyword(self.visibility,
                                                 self.visibility)
            signode += addnodes.desc_sig_space()
        if self.virtual:
            signode += addnodes.desc_sig_keyword('virtual', 'virtual')
            signode += addnodes.desc_sig_space()
        self.name.describe_signature(signode, 'markType', env, symbol=symbol)
        if self.pack:
            signode += addnodes.desc_sig_punctuation('...', '...')


class ASTClass(ASTBase):
    def __init__(self, name: ASTNestedName, final: bool, bases: list[ASTBaseClass],
                 attrs: ASTAttributeList) -> None:
        self.name = name
        self.final = final
        self.bases = bases
        self.attrs = attrs

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.attrs))
        if len(self.attrs) != 0:
            res.append(' ')
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
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.attrs.describe_signature(signode)
        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.final:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_keyword('final', 'final')
        if len(self.bases) > 0:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation(':', ':')
            signode += addnodes.desc_sig_space()
            for b in self.bases:
                b.describe_signature(signode, mode, env, symbol=symbol)
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            signode.pop()
            signode.pop()


class ASTUnion(ASTBase):
    def __init__(self, name: ASTNestedName, attrs: ASTAttributeList) -> None:
        self.name = name
        self.attrs = attrs

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        if version == 1:
            raise NoOldIdError
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.attrs))
        if len(self.attrs) != 0:
            res.append(' ')
        res.append(transform(self.name))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        self.attrs.describe_signature(signode)
        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
        self.name.describe_signature(signode, mode, env, symbol=symbol)


class ASTEnum(ASTBase):
    def __init__(self, name: ASTNestedName, scoped: str, underlyingType: ASTType,
                 attrs: ASTAttributeList) -> None:
        self.name = name
        self.scoped = scoped
        self.underlyingType = underlyingType
        self.attrs = attrs

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        if version == 1:
            raise NoOldIdError
        return symbol.get_full_nested_name().get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.scoped:
            res.append(self.scoped)
            res.append(' ')
        res.append(transform(self.attrs))
        if len(self.attrs) != 0:
            res.append(' ')
        res.append(transform(self.name))
        if self.underlyingType:
            res.append(' : ')
            res.append(transform(self.underlyingType))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        verify_description_mode(mode)
        # self.scoped has been done by the CPPEnumObject
        self.attrs.describe_signature(signode)
        if len(self.attrs) != 0:
            signode += addnodes.desc_sig_space()
        self.name.describe_signature(signode, mode, env, symbol=symbol)
        if self.underlyingType:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation(':', ':')
            signode += addnodes.desc_sig_space()
            self.underlyingType.describe_signature(signode, 'noneIsName',
                                                   env, symbol=symbol)


class ASTEnumerator(ASTBase):
    def __init__(self, name: ASTNestedName, init: ASTInitializer | None,
                 attrs: ASTAttributeList) -> None:
        self.name = name
        self.init = init
        self.attrs = attrs

    def get_id(self, version: int, objectType: str, symbol: Symbol) -> str:
        if version == 1:
            raise NoOldIdError
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


################################################################################
# Templates
################################################################################

# Parameters
################################################################################

class ASTTemplateParam(ASTBase):
    def get_identifier(self) -> ASTIdentifier:
        raise NotImplementedError(repr(self))

    def get_id(self, version: int) -> str:
        raise NotImplementedError(repr(self))

    def describe_signature(self, parentNode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        raise NotImplementedError(repr(self))

    @property
    def isPack(self) -> bool:
        raise NotImplementedError(repr(self))

    @property
    def name(self) -> ASTNestedName:
        raise NotImplementedError(repr(self))


class ASTTemplateKeyParamPackIdDefault(ASTTemplateParam):
    def __init__(self, key: str, identifier: ASTIdentifier,
                 parameterPack: bool, default: ASTType) -> None:
        assert key
        if parameterPack:
            assert default is None
        self.key = key
        self.identifier = identifier
        self.parameterPack = parameterPack
        self.default = default

    def get_identifier(self) -> ASTIdentifier:
        return self.identifier

    def get_id(self, version: int) -> str:
        assert version >= 2
        # this is not part of the normal name mangling in C++
        res = []
        if self.parameterPack:
            res.append('Dp')
        else:
            res.append('0')  # we need to put something
        return ''.join(res)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = [self.key]
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

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword(self.key, self.key)
        if self.parameterPack:
            if self.identifier:
                signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('...', '...')
        if self.identifier:
            if not self.parameterPack:
                signode += addnodes.desc_sig_space()
            self.identifier.describe_signature(signode, mode, env, '', '', symbol)
        if self.default:
            signode += addnodes.desc_sig_space()
            signode += addnodes.desc_sig_punctuation('=', '=')
            signode += addnodes.desc_sig_space()
            self.default.describe_signature(signode, 'markType', env, symbol)


class ASTTemplateParamType(ASTTemplateParam):
    def __init__(self, data: ASTTemplateKeyParamPackIdDefault) -> None:
        assert data
        self.data = data

    @property
    def name(self) -> ASTNestedName:
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self) -> bool:
        return self.data.parameterPack

    def get_identifier(self) -> ASTIdentifier:
        return self.data.get_identifier()

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
        # this is not part of the normal name mangling in C++
        assert version >= 2
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=False)
        else:
            return self.data.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.data)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.data.describe_signature(signode, mode, env, symbol)


class ASTTemplateParamTemplateType(ASTTemplateParam):
    def __init__(self, nestedParams: ASTTemplateParams,
                 data: ASTTemplateKeyParamPackIdDefault) -> None:
        assert nestedParams
        assert data
        self.nestedParams = nestedParams
        self.data = data

    @property
    def name(self) -> ASTNestedName:
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self) -> bool:
        return self.data.parameterPack

    def get_identifier(self) -> ASTIdentifier:
        return self.data.get_identifier()

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
        assert version >= 2
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        else:
            return self.nestedParams.get_id(version) + self.data.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        return transform(self.nestedParams) + transform(self.data)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.nestedParams.describe_signature(signode, 'noneIsName', env, symbol)
        signode += addnodes.desc_sig_space()
        self.data.describe_signature(signode, mode, env, symbol)


class ASTTemplateParamNonType(ASTTemplateParam):
    def __init__(self,
                 param: ASTTypeWithInit | ASTTemplateParamConstrainedTypeWithInit,
                 parameterPack: bool = False) -> None:
        assert param
        self.param = param
        self.parameterPack = parameterPack

    @property
    def name(self) -> ASTNestedName:
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self) -> bool:
        return self.param.isPack or self.parameterPack

    def get_identifier(self) -> ASTIdentifier:
        name = self.param.name
        if name:
            assert len(name.names) == 1
            assert name.names[0].identOrOp
            assert not name.names[0].templateArgs
            res = name.names[0].identOrOp
            assert isinstance(res, ASTIdentifier)
            return res
        else:
            return None

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
        assert version >= 2
        # this is not part of the normal name mangling in C++
        if symbol:
            # the anchor will be our parent
            return symbol.parent.declaration.get_id(version, prefixed=None)
        else:
            res = '_'
            if self.parameterPack:
                res += 'Dp'
            return res + self.param.get_id(version)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = transform(self.param)
        if self.parameterPack:
            res += '...'
        return res

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        self.param.describe_signature(signode, mode, env, symbol)
        if self.parameterPack:
            signode += addnodes.desc_sig_punctuation('...', '...')


class ASTTemplateParams(ASTBase):
    def __init__(self, params: list[ASTTemplateParam],
                 requiresClause: ASTRequiresClause | None) -> None:
        assert params is not None
        self.params = params
        self.requiresClause = requiresClause

    def get_id(self, version: int, excludeRequires: bool = False) -> str:
        assert version >= 2
        res = []
        res.append("I")
        for param in self.params:
            res.append(param.get_id(version))
        res.append("E")
        if not excludeRequires and self.requiresClause:
            res.append('IQ')
            res.append(self.requiresClause.expr.get_id(version))
            res.append('E')
        return ''.join(res)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append("template<")
        res.append(", ".join(transform(a) for a in self.params))
        res.append("> ")
        if self.requiresClause is not None:
            res.append(transform(self.requiresClause))
            res.append(" ")
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('template', 'template')
        signode += addnodes.desc_sig_punctuation('<', '<')
        first = True
        for param in self.params:
            if not first:
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            first = False
            param.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation('>', '>')
        if self.requiresClause is not None:
            signode += addnodes.desc_sig_space()
            self.requiresClause.describe_signature(signode, mode, env, symbol)

    def describe_signature_as_introducer(
            self, parentNode: desc_signature, mode: str, env: BuildEnvironment,
            symbol: Symbol, lineSpec: bool) -> None:
        def makeLine(parentNode: desc_signature) -> addnodes.desc_signature_line:
            signode = addnodes.desc_signature_line()
            parentNode += signode
            signode.sphinx_line_type = 'templateParams'
            return signode
        lineNode = makeLine(parentNode)
        lineNode += addnodes.desc_sig_keyword('template', 'template')
        lineNode += addnodes.desc_sig_punctuation('<', '<')
        first = True
        for param in self.params:
            if not first:
                lineNode += addnodes.desc_sig_punctuation(',', ',')
                lineNode += addnodes.desc_sig_space()
            first = False
            if lineSpec:
                lineNode = makeLine(parentNode)
            param.describe_signature(lineNode, mode, env, symbol)
        if lineSpec and not first:
            lineNode = makeLine(parentNode)
        lineNode += addnodes.desc_sig_punctuation('>', '>')
        if self.requiresClause:
            reqNode = addnodes.desc_signature_line()
            reqNode.sphinx_line_type = 'requiresClause'
            parentNode += reqNode
            self.requiresClause.describe_signature(reqNode, 'markType', env, symbol)


# Template introducers
################################################################################

class ASTTemplateIntroductionParameter(ASTBase):
    def __init__(self, identifier: ASTIdentifier, parameterPack: bool) -> None:
        self.identifier = identifier
        self.parameterPack = parameterPack

    @property
    def name(self) -> ASTNestedName:
        id = self.get_identifier()
        return ASTNestedName([ASTNestedNameElement(id, None)], [False], rooted=False)

    @property
    def isPack(self) -> bool:
        return self.parameterPack

    def get_identifier(self) -> ASTIdentifier:
        return self.identifier

    def get_id(
        self, version: int, objectType: str | None = None, symbol: Symbol | None = None,
    ) -> str:
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

    def get_id_as_arg(self, version: int) -> str:
        assert version >= 2
        # used for the implicit requires clause
        res = self.identifier.get_id(version)
        if self.parameterPack:
            return 'sp' + res
        else:
            return res

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.parameterPack:
            res.append('...')
        res.append(transform(self.identifier))
        return ''.join(res)

    def describe_signature(self, signode: TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        if self.parameterPack:
            signode += addnodes.desc_sig_punctuation('...', '...')
        self.identifier.describe_signature(signode, mode, env, '', '', symbol)


class ASTTemplateIntroduction(ASTBase):
    def __init__(self, concept: ASTNestedName,
                 params: list[ASTTemplateIntroductionParameter]) -> None:
        assert len(params) > 0
        self.concept = concept
        self.params = params

    def get_id(self, version: int) -> str:
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

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        res.append(transform(self.concept))
        res.append('{')
        res.append(', '.join(transform(param) for param in self.params))
        res.append('} ')
        return ''.join(res)

    def describe_signature_as_introducer(
            self, parentNode: desc_signature, mode: str,
            env: BuildEnvironment, symbol: Symbol, lineSpec: bool) -> None:
        # Note: 'lineSpec' has no effect on template introductions.
        signode = addnodes.desc_signature_line()
        parentNode += signode
        signode.sphinx_line_type = 'templateIntroduction'
        self.concept.describe_signature(signode, 'markType', env, symbol)
        signode += addnodes.desc_sig_punctuation('{', '{')
        first = True
        for param in self.params:
            if not first:
                signode += addnodes.desc_sig_punctuation(',', ',')
                signode += addnodes.desc_sig_space()
            first = False
            param.describe_signature(signode, mode, env, symbol)
        signode += addnodes.desc_sig_punctuation('}', '}')


################################################################################

class ASTTemplateDeclarationPrefix(ASTBase):
    def __init__(self,
                 templates: list[ASTTemplateParams | ASTTemplateIntroduction]) -> None:
        # templates is None means it's an explicit instantiation of a variable
        self.templates = templates

    def get_requires_clause_in_last(self) -> ASTRequiresClause | None:
        if self.templates is None:
            return None
        lastList = self.templates[-1]
        if not isinstance(lastList, ASTTemplateParams):
            return None
        return lastList.requiresClause  # which may be None

    def get_id_except_requires_clause_in_last(self, version: int) -> str:
        assert version >= 2
        # This is not part of the Itanium ABI mangling system.
        res = []
        lastIndex = len(self.templates) - 1
        for i, t in enumerate(self.templates):
            if isinstance(t, ASTTemplateParams):
                res.append(t.get_id(version, excludeRequires=(i == lastIndex)))
            else:
                res.append(t.get_id(version))
        return ''.join(res)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        for t in self.templates:
            res.append(transform(t))
        return ''.join(res)

    def describe_signature(self, signode: desc_signature, mode: str,
                           env: BuildEnvironment, symbol: Symbol, lineSpec: bool) -> None:
        verify_description_mode(mode)
        for t in self.templates:
            t.describe_signature_as_introducer(signode, 'lastIsName', env, symbol, lineSpec)


class ASTRequiresClause(ASTBase):
    def __init__(self, expr: ASTExpression) -> None:
        self.expr = expr

    def _stringify(self, transform: StringifyTransform) -> str:
        return 'requires ' + transform(self.expr)

    def describe_signature(self, signode: nodes.TextElement, mode: str,
                           env: BuildEnvironment, symbol: Symbol) -> None:
        signode += addnodes.desc_sig_keyword('requires', 'requires')
        signode += addnodes.desc_sig_space()
        self.expr.describe_signature(signode, mode, env, symbol)


################################################################################
################################################################################

class ASTDeclaration(ASTBase):
    def __init__(self, objectType: str, directiveType: str | None = None,
                 visibility: str | None = None,
                 templatePrefix: ASTTemplateDeclarationPrefix | None = None,
                 declaration: Any = None,
                 trailingRequiresClause: ASTRequiresClause | None = None,
                 semicolon: bool = False) -> None:
        self.objectType = objectType
        self.directiveType = directiveType
        self.visibility = visibility
        self.templatePrefix = templatePrefix
        self.declaration = declaration
        self.trailingRequiresClause = trailingRequiresClause
        self.semicolon = semicolon

        self.symbol: Symbol = None
        # set by CPPObject._add_enumerator_to_parent
        self.enumeratorScopedSymbol: Symbol = None

    def clone(self) -> ASTDeclaration:
        templatePrefixClone = self.templatePrefix.clone() if self.templatePrefix else None
        trailingRequiresClasueClone = self.trailingRequiresClause.clone() \
            if self.trailingRequiresClause else None
        return ASTDeclaration(self.objectType, self.directiveType, self.visibility,
                              templatePrefixClone,
                              self.declaration.clone(), trailingRequiresClasueClone,
                              self.semicolon)

    @property
    def name(self) -> ASTNestedName:
        return self.declaration.name

    @property
    def function_params(self) -> list[ASTFunctionParameter]:
        if self.objectType != 'function':
            return None
        return self.declaration.function_params

    def get_id(self, version: int, prefixed: bool = True) -> str:
        if version == 1:
            if self.templatePrefix or self.trailingRequiresClause:
                raise NoOldIdError
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
        # (See also https://github.com/sphinx-doc/sphinx/pull/10286#issuecomment-1168102147)
        # The first implementation of requires clauses only supported a single clause after the
        # template prefix, and no trailing clause. It put the ID after the template parameter
        # list, i.e.,
        #    "I" + template_parameter_list_id + "E" + "IQ" + requires_clause_id + "E"
        # but the second implementation associates the requires clause with each list, i.e.,
        #    "I" + template_parameter_list_id + "IQ" + requires_clause_id + "E" + "E"
        # To avoid making a new ID version, we make an exception for the last requires clause
        # in the template prefix, and still put it in the end.
        # As we now support trailing requires clauses we add that as if it was a conjunction.
        if self.templatePrefix is not None:
            res.append(self.templatePrefix.get_id_except_requires_clause_in_last(version))
            requiresClauseInLast = self.templatePrefix.get_requires_clause_in_last()
        else:
            requiresClauseInLast = None

        if requiresClauseInLast or self.trailingRequiresClause:
            if version < 4:
                raise NoOldIdError
            res.append('IQ')
            if requiresClauseInLast and self.trailingRequiresClause:
                # make a conjunction of them
                res.append('aa')
            if requiresClauseInLast:
                res.append(requiresClauseInLast.expr.get_id(version))
            if self.trailingRequiresClause:
                res.append(self.trailingRequiresClause.expr.get_id(version))
            res.append('E')
        res.append(self.declaration.get_id(version, self.objectType, self.symbol))
        return ''.join(res)

    def get_newest_id(self) -> str:
        return self.get_id(_max_id, True)

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.visibility and self.visibility != "public":
            res.append(self.visibility)
            res.append(' ')
        if self.templatePrefix:
            res.append(transform(self.templatePrefix))
        res.append(transform(self.declaration))
        if self.trailingRequiresClause:
            res.append(' ')
            res.append(transform(self.trailingRequiresClause))
        if self.semicolon:
            res.append(';')
        return ''.join(res)

    def describe_signature(self, signode: desc_signature, mode: str,
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

        if self.templatePrefix:
            self.templatePrefix.describe_signature(signode, mode, env,
                                                   symbol=self.symbol,
                                                   lineSpec=options.get('tparam-line-spec'))
        signode += mainDeclNode
        if self.visibility and self.visibility != "public":
            mainDeclNode += addnodes.desc_sig_keyword(self.visibility, self.visibility)
            mainDeclNode += addnodes.desc_sig_space()
        if self.objectType == 'type':
            prefix = self.declaration.get_type_declaration_prefix()
            mainDeclNode += addnodes.desc_sig_keyword(prefix, prefix)
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'concept':
            mainDeclNode += addnodes.desc_sig_keyword('concept', 'concept')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType in {'member', 'function'}:
            pass
        elif self.objectType == 'class':
            assert self.directiveType in ('class', 'struct')
            mainDeclNode += addnodes.desc_sig_keyword(self.directiveType, self.directiveType)
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'union':
            mainDeclNode += addnodes.desc_sig_keyword('union', 'union')
            mainDeclNode += addnodes.desc_sig_space()
        elif self.objectType == 'enum':
            mainDeclNode += addnodes.desc_sig_keyword('enum', 'enum')
            mainDeclNode += addnodes.desc_sig_space()
            if self.directiveType == 'enum-class':
                mainDeclNode += addnodes.desc_sig_keyword('class', 'class')
                mainDeclNode += addnodes.desc_sig_space()
            elif self.directiveType == 'enum-struct':
                mainDeclNode += addnodes.desc_sig_keyword('struct', 'struct')
                mainDeclNode += addnodes.desc_sig_space()
            else:
                assert self.directiveType == 'enum', self.directiveType
        elif self.objectType == 'enumerator':
            mainDeclNode += addnodes.desc_sig_keyword('enumerator', 'enumerator')
            mainDeclNode += addnodes.desc_sig_space()
        else:
            raise AssertionError(self.objectType)
        self.declaration.describe_signature(mainDeclNode, mode, env, self.symbol)
        lastDeclNode = mainDeclNode
        if self.trailingRequiresClause:
            trailingReqNode = addnodes.desc_signature_line()
            trailingReqNode.sphinx_line_type = 'trailingRequiresClause'
            signode.append(trailingReqNode)
            lastDeclNode = trailingReqNode
            self.trailingRequiresClause.describe_signature(
                trailingReqNode, 'markType', env, self.symbol)
        if self.semicolon:
            lastDeclNode += addnodes.desc_sig_punctuation(';', ';')


class ASTNamespace(ASTBase):
    def __init__(self, nestedName: ASTNestedName,
                 templatePrefix: ASTTemplateDeclarationPrefix) -> None:
        self.nestedName = nestedName
        self.templatePrefix = templatePrefix

    def _stringify(self, transform: StringifyTransform) -> str:
        res = []
        if self.templatePrefix:
            res.append(transform(self.templatePrefix))
        res.append(transform(self.nestedName))
        return ''.join(res)


class SymbolLookupResult:
    def __init__(self, symbols: Iterator[Symbol], parentSymbol: Symbol,
                 identOrOp: ASTIdentifier | ASTOperator, templateParams: Any,
                 templateArgs: ASTTemplateArgs) -> None:
        self.symbols = symbols
        self.parentSymbol = parentSymbol
        self.identOrOp = identOrOp
        self.templateParams = templateParams
        self.templateArgs = templateArgs


class LookupKey:
    def __init__(self, data: list[tuple[ASTNestedNameElement,
                                        ASTTemplateParams | ASTTemplateIntroduction,
                                        str]]) -> None:
        self.data = data


def _is_specialization(templateParams: ASTTemplateParams | ASTTemplateIntroduction,
                       templateArgs: ASTTemplateArgs) -> bool:
    # Checks if `templateArgs` does not exactly match `templateParams`.
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
        paramName = str(param.name)
        argTxt = str(arg)
        isArgPackExpansion = argTxt.endswith('...')
        if param.isPack != isArgPackExpansion:
            return True
        argName = argTxt[:-3] if isArgPackExpansion else argTxt
        if paramName != argName:
            return True
    return False


class Symbol:
    debug_indent = 0
    debug_indent_string = "  "
    debug_lookup = False  # overridden by the corresponding config value
    debug_show_tree = False  # overridden by the corresponding config value

    def __copy__(self):
        raise AssertionError  # shouldn't happen

    def __deepcopy__(self, memo):
        if self.parent:
            raise AssertionError  # shouldn't happen
        # the domain base class makes a copy of the initial data, which is fine
        return Symbol(None, None, None, None, None, None, None)

    @staticmethod
    def debug_print(*args: Any) -> None:
        logger.debug(Symbol.debug_indent_string * Symbol.debug_indent, end="")
        logger.debug(*args)

    def _assert_invariants(self) -> None:
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

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "children":
            raise AssertionError
        return super().__setattr__(key, value)

    def __init__(self, parent: Symbol | None,
                 identOrOp: ASTIdentifier | ASTOperator | None,
                 templateParams: ASTTemplateParams | ASTTemplateIntroduction | None,
                 templateArgs: Any, declaration: ASTDeclaration | None,
                 docname: str | None, line: int | None) -> None:
        self.parent = parent
        # declarations in a single directive are linked together
        self.siblingAbove: Symbol | None = None
        self.siblingBelow: Symbol | None = None
        self.identOrOp = identOrOp
        # Ensure the same symbol for `A` is created for:
        #
        #     .. cpp:class:: template <typename T> class A
        #
        # and
        #
        #     .. cpp:function:: template <typename T> int A<T>::foo()
        if (templateArgs is not None and
                not _is_specialization(templateParams, templateArgs)):
            templateArgs = None
        self.templateParams = templateParams  # template<templateParams>
        self.templateArgs = templateArgs  # identifier<templateArgs>
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
        self._add_template_and_function_params()

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
        self._add_template_and_function_params()

    def _add_template_and_function_params(self) -> None:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_add_template_and_function_params:")
        # Note: we may be called from _fill_empty, so the symbols we want
        #       to add may actually already be present (as empty symbols).

        # add symbols for the template params
        if self.templateParams:
            for tp in self.templateParams.params:
                if not tp.get_identifier():
                    continue
                # only add a declaration if we our self are from a declaration
                if self.declaration:
                    decl = ASTDeclaration(objectType='templateParam', declaration=tp)
                else:
                    decl = None
                nne = ASTNestedNameElement(tp.get_identifier(), None)
                nn = ASTNestedName([nne], [False], rooted=False)
                self._add_symbols(nn, [], decl, self.docname, self.line)
        # add symbols for function parameters, if any
        if self.declaration is not None and self.declaration.function_params is not None:
            for fp in self.declaration.function_params:
                if fp.arg is None:
                    continue
                nn = fp.arg.name
                if nn is None:
                    continue
                # (comparing to the template params: we have checked that we are a declaration)
                decl = ASTDeclaration(objectType='functionParam', declaration=fp)
                assert not nn.rooted
                assert len(nn.names) == 1
                self._add_symbols(nn, [], decl, self.docname, self.line)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1

    def remove(self) -> None:
        if self.parent is None:
            return
        assert self in self.parent._children
        self.parent._children.remove(self)
        self.parent = None

    def clear_doc(self, docname: str) -> None:
        newChildren: list[Symbol] = []
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
            newChildren.append(sChild)
        self._children = newChildren

    def get_all_symbols(self) -> Iterator[Any]:
        yield self
        for sChild in self._children:
            yield from sChild.get_all_symbols()

    @property
    def children_recurse_anon(self) -> Generator[Symbol, None, None]:
        for c in self._children:
            yield c
            if not c.identOrOp.is_anon():
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
            nne = ASTNestedNameElement(s.identOrOp, s.templateArgs)
            if s.declaration is not None:
                key.append((nne, s.templateParams, s.declaration.get_newest_id()))
            else:
                key.append((nne, s.templateParams, None))
        return LookupKey(key)

    def get_full_nested_name(self) -> ASTNestedName:
        symbols = []
        s = self
        while s.parent:
            symbols.append(s)
            s = s.parent
        symbols.reverse()
        names = []
        templates = []
        for s in symbols:
            names.append(ASTNestedNameElement(s.identOrOp, s.templateArgs))
            templates.append(False)
        return ASTNestedName(names, templates, rooted=False)

    def _find_first_named_symbol(self, identOrOp: ASTIdentifier | ASTOperator,
                                 templateParams: Any, templateArgs: ASTTemplateArgs,
                                 templateShorthand: bool, matchSelf: bool,
                                 recurseInAnon: bool, correctPrimaryTemplateArgs: bool,
                                 ) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_print("_find_first_named_symbol ->")
        res = self._find_named_symbols(identOrOp, templateParams, templateArgs,
                                       templateShorthand, matchSelf, recurseInAnon,
                                       correctPrimaryTemplateArgs,
                                       searchInSiblings=False)
        try:
            return next(res)
        except StopIteration:
            return None

    def _find_named_symbols(self, identOrOp: ASTIdentifier | ASTOperator,
                            templateParams: Any, templateArgs: ASTTemplateArgs,
                            templateShorthand: bool, matchSelf: bool,
                            recurseInAnon: bool, correctPrimaryTemplateArgs: bool,
                            searchInSiblings: bool) -> Iterator[Symbol]:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_find_named_symbols:")
            Symbol.debug_indent += 1
            Symbol.debug_print("self:")
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_print("identOrOp:                  ", identOrOp)
            Symbol.debug_print("templateParams:             ", templateParams)
            Symbol.debug_print("templateArgs:               ", templateArgs)
            Symbol.debug_print("templateShorthand:          ", templateShorthand)
            Symbol.debug_print("matchSelf:                  ", matchSelf)
            Symbol.debug_print("recurseInAnon:              ", recurseInAnon)
            Symbol.debug_print("correctPrimaryTemplateAargs:", correctPrimaryTemplateArgs)
            Symbol.debug_print("searchInSiblings:           ", searchInSiblings)

        if correctPrimaryTemplateArgs:
            if templateParams is not None and templateArgs is not None:
                # If both are given, but it's not a specialization, then do lookup as if
                # there is no argument list.
                # For example: template<typename T> int A<T>::var;
                if not _is_specialization(templateParams, templateArgs):
                    templateArgs = None

        def matches(s: Symbol) -> bool:
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
                if str(s.templateParams) != str(templateParams):
                    return False
            if (s.templateArgs is None) != (templateArgs is None):
                return False
            if s.templateArgs:
                # TODO: do better comparison
                if str(s.templateArgs) != str(templateArgs):
                    return False
            return True

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
            if matches(s):
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
        templateDecls: list[Any],
        onMissingQualifiedSymbol: Callable[
            [Symbol, ASTIdentifier | ASTOperator, Any, ASTTemplateArgs], Symbol | None,
        ],
        strictTemplateParamArgLists: bool, ancestorLookupType: str,
        templateShorthand: bool, matchSelf: bool,
        recurseInAnon: bool, correctPrimaryTemplateArgs: bool,
        searchInSiblings: bool,
    ) -> SymbolLookupResult:
        # ancestorLookupType: if not None, specifies the target type of the lookup
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_symbol_lookup:")
            Symbol.debug_indent += 1
            Symbol.debug_print("self:")
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_print("nestedName:        ", nestedName)
            Symbol.debug_print("templateDecls:     ", ",".join(str(t) for t in templateDecls))
            Symbol.debug_print("strictTemplateParamArgLists:", strictTemplateParamArgLists)
            Symbol.debug_print("ancestorLookupType:", ancestorLookupType)
            Symbol.debug_print("templateShorthand: ", templateShorthand)
            Symbol.debug_print("matchSelf:         ", matchSelf)
            Symbol.debug_print("recurseInAnon:     ", recurseInAnon)
            Symbol.debug_print("correctPrimaryTemplateArgs: ", correctPrimaryTemplateArgs)
            Symbol.debug_print("searchInSiblings:  ", searchInSiblings)

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
                                                    recurseInAnon=recurseInAnon,
                                                    searchInSiblings=searchInSiblings):
                        # if we are in the scope of a constructor but wants to
                        # reference the class we need to walk one extra up
                        if (len(names) == 1 and ancestorLookupType == 'class' and matchSelf and
                                parentSymbol.parent and
                                parentSymbol.parent.identOrOp == firstName.identOrOp):
                            pass
                        else:
                            break
                    parentSymbol = parentSymbol.parent

        if Symbol.debug_lookup:
            Symbol.debug_print("starting point:")
            logger.debug(parentSymbol.to_string(Symbol.debug_indent + 1), end="")

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
            recurseInAnon=recurseInAnon, correctPrimaryTemplateArgs=False,
            searchInSiblings=searchInSiblings)
        if Symbol.debug_lookup:
            symbols = list(symbols)  # type: ignore[assignment]
            Symbol.debug_indent -= 2
        return SymbolLookupResult(symbols, parentSymbol,
                                  identOrOp, templateParams, templateArgs)

    def _add_symbols(self, nestedName: ASTNestedName, templateDecls: list[Any],
                     declaration: ASTDeclaration, docname: str, line: int) -> Symbol:
        # Used for adding a whole path of symbols, where the last may or may not
        # be an actual declaration.

        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("_add_symbols:")
            Symbol.debug_indent += 1
            Symbol.debug_print("tdecls:", ",".join(str(t) for t in templateDecls))
            Symbol.debug_print("nn:       ", nestedName)
            Symbol.debug_print("decl:     ", declaration)
            Symbol.debug_print(f"location: {docname}:{line}")

        def onMissingQualifiedSymbol(parentSymbol: Symbol,
                                     identOrOp: ASTIdentifier | ASTOperator,
                                     templateParams: Any, templateArgs: ASTTemplateArgs,
                                     ) -> Symbol | None:
            if Symbol.debug_lookup:
                Symbol.debug_indent += 1
                Symbol.debug_print("_add_symbols, onMissingQualifiedSymbol:")
                Symbol.debug_indent += 1
                Symbol.debug_print("templateParams:", templateParams)
                Symbol.debug_print("identOrOp:     ", identOrOp)
                Symbol.debug_print("templateARgs:  ", templateArgs)
                Symbol.debug_indent -= 2
            return Symbol(parent=parentSymbol, identOrOp=identOrOp,
                          templateParams=templateParams,
                          templateArgs=templateArgs, declaration=None,
                          docname=None, line=None)

        lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                           onMissingQualifiedSymbol,
                                           strictTemplateParamArgLists=True,
                                           ancestorLookupType=None,
                                           templateShorthand=False,
                                           matchSelf=False,
                                           recurseInAnon=False,
                                           correctPrimaryTemplateArgs=True,
                                           searchInSiblings=False)
        assert lookupResult is not None  # we create symbols all the way, so that can't happen
        symbols = list(lookupResult.symbols)
        if len(symbols) == 0:
            if Symbol.debug_lookup:
                Symbol.debug_print("_add_symbols, result, no symbol:")
                Symbol.debug_indent += 1
                Symbol.debug_print("templateParams:", lookupResult.templateParams)
                Symbol.debug_print("identOrOp:     ", lookupResult.identOrOp)
                Symbol.debug_print("templateArgs:  ", lookupResult.templateArgs)
                Symbol.debug_print("declaration:   ", declaration)
                Symbol.debug_print(f"location:      {docname}:{line}")
                Symbol.debug_indent -= 1
            symbol = Symbol(parent=lookupResult.parentSymbol,
                            identOrOp=lookupResult.identOrOp,
                            templateParams=lookupResult.templateParams,
                            templateArgs=lookupResult.templateArgs,
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
                            identOrOp=lookupResult.identOrOp,
                            templateParams=lookupResult.templateParams,
                            templateArgs=lookupResult.templateArgs,
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
                # but all existing must be functions as well,
                # otherwise we declare it to be a duplicate
                if symbol.declaration.objectType != 'function':
                    handleDuplicateDeclaration(symbol, candSymbol)
                    # (not reachable)
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
                Symbol.debug_print("no match, no empty")
                if candSymbol is not None:
                    Symbol.debug_print("result is already created candSymbol")
                else:
                    Symbol.debug_print("result is makeCandSymbol()")
                Symbol.debug_indent -= 2
            if candSymbol is not None:
                return candSymbol
            else:
                return makeCandSymbol()
        else:
            if Symbol.debug_lookup:
                Symbol.debug_print(
                    "no match, but fill an empty declaration, candSybmol is not None?:",
                    candSymbol is not None,
                )
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

        def unconditionalAdd(self, otherChild):
            # TODO: hmm, should we prune by docnames?
            self._children.append(otherChild)
            otherChild.parent = self
            otherChild._assert_invariants()

        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
        for otherChild in other._children:
            if Symbol.debug_lookup:
                Symbol.debug_print("otherChild:\n", otherChild.to_string(Symbol.debug_indent))
                Symbol.debug_indent += 1
            if otherChild.isRedeclaration:
                unconditionalAdd(self, otherChild)
                if Symbol.debug_lookup:
                    Symbol.debug_print("isRedeclaration")
                    Symbol.debug_indent -= 1
                continue
            candiateIter = self._find_named_symbols(
                identOrOp=otherChild.identOrOp,
                templateParams=otherChild.templateParams,
                templateArgs=otherChild.templateArgs,
                templateShorthand=False, matchSelf=False,
                recurseInAnon=False, correctPrimaryTemplateArgs=False,
                searchInSiblings=False)
            candidates = list(candiateIter)

            if Symbol.debug_lookup:
                Symbol.debug_print("raw candidate symbols:", len(candidates))
            symbols = [s for s in candidates if not s.isRedeclaration]
            if Symbol.debug_lookup:
                Symbol.debug_print("non-duplicate candidate symbols:", len(symbols))

            if len(symbols) == 0:
                unconditionalAdd(self, otherChild)
                if Symbol.debug_lookup:
                    Symbol.debug_indent -= 1
                continue

            ourChild = None
            if otherChild.declaration is None:
                if Symbol.debug_lookup:
                    Symbol.debug_print("no declaration in other child")
                ourChild = symbols[0]
            else:
                queryId = otherChild.declaration.get_newest_id()
                if Symbol.debug_lookup:
                    Symbol.debug_print("queryId:  ", queryId)
                for symbol in symbols:
                    if symbol.declaration is None:
                        if Symbol.debug_lookup:
                            Symbol.debug_print("empty candidate")
                        # if in the end we have non-matching, but have an empty one,
                        # then just continue with that
                        ourChild = symbol
                        continue
                    candId = symbol.declaration.get_newest_id()
                    if Symbol.debug_lookup:
                        Symbol.debug_print("candidate:", candId)
                    if candId == queryId:
                        ourChild = symbol
                        break
            if Symbol.debug_lookup:
                Symbol.debug_indent -= 1
            if ourChild is None:
                unconditionalAdd(self, otherChild)
                continue
            if otherChild.declaration and otherChild.docname in docnames:
                if not ourChild.declaration:
                    ourChild._fill_empty(otherChild.declaration,
                                         otherChild.docname, otherChild.line)
                elif ourChild.docname != otherChild.docname:
                    name = str(ourChild.declaration)
                    msg = __("Duplicate C++ declaration, also defined at %s:%s.\n"
                             "Declaration is '.. cpp:%s:: %s'.")
                    msg = msg % (ourChild.docname, ourChild.line,
                                 ourChild.declaration.directiveType, name)
                    logger.warning(msg, location=(otherChild.docname, otherChild.line))
                else:
                    if (otherChild.declaration.objectType ==
                            ourChild.declaration.objectType and
                            otherChild.declaration.objectType in
                            ('templateParam', 'functionParam') and
                            ourChild.parent.declaration == otherChild.parent.declaration):
                        # `ourChild` was just created during merging by the call
                        # to `_fill_empty` on the parent and can be ignored.
                        pass
                    else:
                        # Both have declarations, and in the same docname.
                        # This can apparently happen, it should be safe to
                        # just ignore it, right?
                        # Hmm, only on duplicate declarations, right?
                        msg = "Internal C++ domain error during symbol merging.\n"
                        msg += "ourChild:\n" + ourChild.to_string(1)
                        msg += "\notherChild:\n" + otherChild.to_string(1)
                        logger.warning(msg, location=otherChild.docname)
            ourChild.merge_with(otherChild, docnames, env)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 2

    def add_name(self, nestedName: ASTNestedName,
                 templatePrefix: ASTTemplateDeclarationPrefix | None = None) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("add_name:")
        if templatePrefix:
            templateDecls = templatePrefix.templates
        else:
            templateDecls = []
        res = self._add_symbols(nestedName, templateDecls,
                                declaration=None, docname=None, line=None)
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
        if declaration.templatePrefix:
            templateDecls = declaration.templatePrefix.templates
        else:
            templateDecls = []
        res = self._add_symbols(nestedName, templateDecls, declaration, docname, line)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1
        return res

    def find_identifier(self, identOrOp: ASTIdentifier | ASTOperator,
                        matchSelf: bool, recurseInAnon: bool, searchInSiblings: bool,
                        ) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("find_identifier:")
            Symbol.debug_indent += 1
            Symbol.debug_print("identOrOp:       ", identOrOp)
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
            if matchSelf and current.identOrOp == identOrOp:
                return current
            children = current.children_recurse_anon if recurseInAnon else current._children
            for s in children:
                if s.identOrOp == identOrOp:
                    return s
            if not searchInSiblings:
                break
            current = current.siblingAbove
        return None

    def direct_lookup(self, key: LookupKey) -> Symbol:
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("direct_lookup:")
            Symbol.debug_indent += 1
        s = self
        for name, templateParams, id_ in key.data:
            if id_ is not None:
                res = None
                for cand in s._children:
                    if cand.declaration is None:
                        continue
                    if cand.declaration.get_newest_id() == id_:
                        res = cand
                        break
                s = res
            else:
                identOrOp = name.identOrOp
                templateArgs = name.templateArgs
                s = s._find_first_named_symbol(identOrOp,
                                               templateParams, templateArgs,
                                               templateShorthand=False,
                                               matchSelf=False,
                                               recurseInAnon=False,
                                               correctPrimaryTemplateArgs=False)
            if Symbol.debug_lookup:
                Symbol.debug_print("name:          ", name)
                Symbol.debug_print("templateParams:", templateParams)
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

    def find_name(self, nestedName: ASTNestedName, templateDecls: list[Any],
                  typ: str, templateShorthand: bool, matchSelf: bool,
                  recurseInAnon: bool, searchInSiblings: bool) -> tuple[list[Symbol], str]:
        # templateShorthand: missing template parameter lists for templates is ok
        # If the first component is None,
        # then the second component _may_ be a string explaining why.
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("find_name:")
            Symbol.debug_indent += 1
            Symbol.debug_print("self:")
            logger.debug(self.to_string(Symbol.debug_indent + 1), end="")
            Symbol.debug_print("nestedName:       ", nestedName)
            Symbol.debug_print("templateDecls:    ", templateDecls)
            Symbol.debug_print("typ:              ", typ)
            Symbol.debug_print("templateShorthand:", templateShorthand)
            Symbol.debug_print("matchSelf:        ", matchSelf)
            Symbol.debug_print("recurseInAnon:    ", recurseInAnon)
            Symbol.debug_print("searchInSiblings: ", searchInSiblings)

        class QualifiedSymbolIsTemplateParam(Exception):
            pass

        def onMissingQualifiedSymbol(parentSymbol: Symbol,
                                     identOrOp: ASTIdentifier | ASTOperator,
                                     templateParams: Any,
                                     templateArgs: ASTTemplateArgs) -> Symbol | None:
            # TODO: Maybe search without template args?
            #       Though, the correctPrimaryTemplateArgs does
            #       that for primary templates.
            #       Is there another case where it would be good?
            if parentSymbol.declaration is not None:
                if parentSymbol.declaration.objectType == 'templateParam':
                    raise QualifiedSymbolIsTemplateParam
            return None

        try:
            lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                               onMissingQualifiedSymbol,
                                               strictTemplateParamArgLists=False,
                                               ancestorLookupType=typ,
                                               templateShorthand=templateShorthand,
                                               matchSelf=matchSelf,
                                               recurseInAnon=recurseInAnon,
                                               correctPrimaryTemplateArgs=False,
                                               searchInSiblings=searchInSiblings)
        except QualifiedSymbolIsTemplateParam:
            return None, "templateParamInQualified"

        if lookupResult is None:
            # if it was a part of the qualification that could not be found
            if Symbol.debug_lookup:
                Symbol.debug_indent -= 2
            return None, None

        res = list(lookupResult.symbols)
        if len(res) != 0:
            if Symbol.debug_lookup:
                Symbol.debug_indent -= 2
            return res, None

        if lookupResult.parentSymbol.declaration is not None:
            if lookupResult.parentSymbol.declaration.objectType == 'templateParam':
                return None, "templateParamInQualified"

        # try without template params and args
        symbol = lookupResult.parentSymbol._find_first_named_symbol(
            lookupResult.identOrOp, None, None,
            templateShorthand=templateShorthand, matchSelf=matchSelf,
            recurseInAnon=recurseInAnon, correctPrimaryTemplateArgs=False)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 2
        if symbol is not None:
            return [symbol], None
        else:
            return None, None

    def find_declaration(self, declaration: ASTDeclaration, typ: str, templateShorthand: bool,
                         matchSelf: bool, recurseInAnon: bool) -> Symbol:
        # templateShorthand: missing template parameter lists for templates is ok
        if Symbol.debug_lookup:
            Symbol.debug_indent += 1
            Symbol.debug_print("find_declaration:")
        nestedName = declaration.name
        if declaration.templatePrefix:
            templateDecls = declaration.templatePrefix.templates
        else:
            templateDecls = []

        def onMissingQualifiedSymbol(parentSymbol: Symbol,
                                     identOrOp: ASTIdentifier | ASTOperator,
                                     templateParams: Any,
                                     templateArgs: ASTTemplateArgs) -> Symbol | None:
            return None

        lookupResult = self._symbol_lookup(nestedName, templateDecls,
                                           onMissingQualifiedSymbol,
                                           strictTemplateParamArgLists=False,
                                           ancestorLookupType=typ,
                                           templateShorthand=templateShorthand,
                                           matchSelf=matchSelf,
                                           recurseInAnon=recurseInAnon,
                                           correctPrimaryTemplateArgs=False,
                                           searchInSiblings=False)
        if Symbol.debug_lookup:
            Symbol.debug_indent -= 1
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
                             docname='fakeDocnameForQuery',
                             line=42)
        queryId = declaration.get_newest_id()
        for symbol in symbols:
            if symbol.declaration is None:
                continue
            candId = symbol.declaration.get_newest_id()
            if candId == queryId:
                querySymbol.remove()
                return symbol
        querySymbol.remove()
        return None

    def to_string(self, indent: int) -> str:
        res = [Symbol.debug_indent_string * indent]
        if not self.parent:
            res.append('::')
        else:
            if self.templateParams:
                res.append(str(self.templateParams))
                res.append('\n')
                res.append(Symbol.debug_indent_string * indent)
            if self.identOrOp:
                res.append(str(self.identOrOp))
            else:
                res.append(str(self.declaration))
            if self.templateArgs:
                res.append(str(self.templateArgs))
            if self.declaration:
                res.append(": ")
                if self.isRedeclaration:
                    res.append('!!duplicate!! ')
                res.append("{" + self.declaration.objectType + "} ")
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
        return 'C++'

    @property
    def id_attributes(self):
        return self.config.cpp_id_attributes

    @property
    def paren_attributes(self):
        return self.config.cpp_paren_attributes

    def _parse_string(self) -> str:
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

    def _parse_literal(self) -> ASTLiteral:
        # -> integer-literal
        #  | character-literal
        #  | floating-literal
        #  | string-literal
        #  | boolean-literal -> "false" | "true"
        #  | pointer-literal -> "nullptr"
        #  | user-defined-literal

        def _udl(literal: ASTLiteral) -> ASTLiteral:
            if not self.match(udl_identifier_re):
                return literal
            # hmm, should we care if it's a keyword?
            # it looks like GCC does not disallow keywords
            ident = ASTIdentifier(self.matched_text)
            return ASTUserDefinedLiteral(literal, ident)

        self.skip_ws()
        if self.skip_word('nullptr'):
            return ASTPointerLiteral()
        if self.skip_word('true'):
            return ASTBooleanLiteral(True)
        if self.skip_word('false'):
            return ASTBooleanLiteral(False)
        pos = self.pos
        if self.match(float_literal_re):
            hasSuffix = self.match(float_literal_suffix_re)
            floatLit = ASTNumberLiteral(self.definition[pos:self.pos])
            if hasSuffix:
                return floatLit
            else:
                return _udl(floatLit)
        for regex in [binary_literal_re, hex_literal_re,
                      integer_literal_re, octal_literal_re]:
            if self.match(regex):
                hasSuffix = self.match(integers_literal_suffix_re)
                intLit = ASTNumberLiteral(self.definition[pos:self.pos])
                if hasSuffix:
                    return intLit
                else:
                    return _udl(intLit)

        string = self._parse_string()
        if string is not None:
            return _udl(ASTStringLiteral(string))

        # character-literal
        if self.match(char_literal_re):
            prefix = self.last_match.group(1)  # may be None when no prefix
            data = self.last_match.group(2)
            try:
                charLit = ASTCharLiteral(prefix, data)
            except UnicodeDecodeError as e:
                self.fail("Can not handle character literal. Internal error was: %s" % e)
            except UnsupportedMultiCharacterCharLiteral:
                self.fail("Can not handle character literal"
                          " resulting in multiple decoded characters.")
            return _udl(charLit)
        return None

    def _parse_fold_or_paren_expression(self) -> ASTExpression:
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
                res = self._parse_expression()
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail("Expected ')' in end of parenthesized expression.")
            except DefinitionError as eExpr:
                raise self._make_multi_error([
                    (eFold, "If fold expression"),
                    (eExpr, "If parenthesized expression"),
                ], "Error in fold expression or parenthesized expression.") from eExpr
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

    def _parse_primary_expression(self) -> ASTExpression:
        # literal
        # "this"
        # lambda-expression
        # "(" expression ")"
        # fold-expression
        # id-expression -> we parse this with _parse_nested_name
        self.skip_ws()
        res: ASTExpression = self._parse_literal()
        if res is not None:
            return res
        self.skip_ws()
        if self.skip_word("this"):
            return ASTThisLiteral()
        # TODO: try lambda expression
        res = self._parse_fold_or_paren_expression()
        if res is not None:
            return res
        nn = self._parse_nested_name()
        if nn is not None:
            return ASTIdExpression(nn)
        return None

    def _parse_initializer_list(self, name: str, open: str, close: str,
                                ) -> tuple[list[ASTExpression | ASTBracedInitList],
                                           bool]:
        # Parse open and close with the actual initializer-list in between
        # -> initializer-clause '...'[opt]
        #  | initializer-list ',' initializer-clause '...'[opt]
        self.skip_ws()
        if not self.skip_string_and_ws(open):
            return None, None
        if self.skip_string(close):
            return [], False

        exprs: list[ASTExpression | ASTBracedInitList] = []
        trailingComma = False
        while True:
            self.skip_ws()
            expr = self._parse_initializer_clause()
            self.skip_ws()
            if self.skip_string('...'):
                exprs.append(ASTPackExpansionExpr(expr))
            else:
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

    def _parse_paren_expression_list(self) -> ASTParenExprList:
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

    def _parse_initializer_clause(self) -> ASTExpression | ASTBracedInitList:
        bracedInitList = self._parse_braced_init_list()
        if bracedInitList is not None:
            return bracedInitList
        return self._parse_assignment_expression(inTemplate=False)

    def _parse_braced_init_list(self) -> ASTBracedInitList:
        # -> '{' initializer-list ','[opt] '}'
        #  | '{' '}'
        exprs, trailingComma = self._parse_initializer_list("braced-init-list", '{', '}')
        if exprs is None:
            return None
        return ASTBracedInitList(exprs, trailingComma)

    def _parse_expression_list_or_braced_init_list(
        self,
    ) -> ASTParenExprList | ASTBracedInitList:
        paren = self._parse_paren_expression_list()
        if paren is not None:
            return paren
        return self._parse_braced_init_list()

    def _parse_postfix_expression(self) -> ASTPostfixExpr:
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
        prefix: Any = None
        self.skip_ws()

        cast = None
        for c in _id_explicit_cast:
            if self.skip_word_and_ws(c):
                cast = c
                break
        if cast is not None:
            prefixType = "cast"
            if not self.skip_string("<"):
                self.fail("Expected '<' after '%s'." % cast)
            typ = self._parse_type(False)
            self.skip_ws()
            if not self.skip_string_and_ws(">"):
                self.fail("Expected '>' after type in '%s'." % cast)
            if not self.skip_string("("):
                self.fail("Expected '(' in '%s'." % cast)

            def parser() -> ASTExpression:
                return self._parse_expression()
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

                    def parser() -> ASTExpression:
                        return self._parse_expression()
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
                    raise self._make_multi_error(errors, header) from eExpr
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
                    raise self._make_multi_error(errors, header) from eInner

        # and now parse postfixes
        postFixes: list[ASTPostfixOp] = []
        while True:
            self.skip_ws()
            if prefixType in ('expr', 'cast', 'typeid'):
                if self.skip_string_and_ws('['):
                    expr = self._parse_expression()
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
                        postFixes.append(ASTPostfixMember(name))
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
            lst = self._parse_expression_list_or_braced_init_list()
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
        #  | "sizeof" "..." "(" identifier ")"
        #  | "alignof" "(" type-id ")"
        #  | noexcept-expression -> noexcept "(" expression ")"
        #  | new-expression
        #  | delete-expression
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
            if self.skip_string_and_ws('...'):
                if not self.skip_string_and_ws('('):
                    self.fail("Expecting '(' after 'sizeof...'.")
                if not self.match(identifier_re):
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
            expr = self._parse_expression()
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
            lst = self._parse_expression_list_or_braced_init_list()
            return ASTNewExpr(rooted, isNewTypeId, ASTType(declSpecs, decl), lst)
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

    def _parse_logical_or_expression(self, inTemplate: bool) -> ASTExpression:
        # logical-or     = logical-and      ||
        # logical-and    = inclusive-or     &&
        # inclusive-or   = exclusive-or     |
        # exclusive-or   = and              ^
        # and            = equality         &
        # equality       = relational       ==, !=
        # relational     = shift            <, >, <=, >=, <=>
        # shift          = additive         <<, >>
        # additive       = multiplicative   +, -
        # multiplicative = pm               *, /, %
        # pm             = cast             .*, ->*
        def _parse_bin_op_expr(self: DefinitionParser,
                               opId: int, inTemplate: bool) -> ASTExpression:
            if opId + 1 == len(_expression_bin_ops):
                def parser(inTemplate: bool) -> ASTExpression:
                    return self._parse_cast_expression()
            else:
                def parser(inTemplate: bool) -> ASTExpression:
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

    def _parse_conditional_expression_tail(self, orExprHead: ASTExpression,
                                           inTemplate: bool) -> ASTConditionalExpr | None:
        # Consumes the orExprHead on success.

        # -> "?" expression ":" assignment-expression
        self.skip_ws()
        if not self.skip_string("?"):
            return None
        thenExpr = self._parse_expression()
        self.skip_ws()
        if not self.skip_string(":"):
            self.fail('Expected ":" after then-expression in conditional expression.')
        elseExpr = self._parse_assignment_expression(inTemplate)
        return ASTConditionalExpr(orExprHead, thenExpr, elseExpr)

    def _parse_assignment_expression(self, inTemplate: bool) -> ASTExpression:
        # -> conditional-expression
        #  | logical-or-expression assignment-operator initializer-clause
        #  | yield-expression -> "co_yield" assignment-expression
        #                      | "co_yield" braced-init-list
        #  | throw-expression -> "throw" assignment-expression[opt]
        # TODO: yield-expression
        # TODO: throw-expression

        # Now we have (after expanding conditional-expression:
        #     logical-or-expression
        #   | logical-or-expression "?" expression ":" assignment-expression
        #   | logical-or-expression assignment-operator initializer-clause
        leftExpr = self._parse_logical_or_expression(inTemplate=inTemplate)
        # the ternary operator
        condExpr = self._parse_conditional_expression_tail(leftExpr, inTemplate)
        if condExpr is not None:
            return condExpr
        # and actual assignment
        for op in _expression_assignment_ops:
            if op[0] in 'anox':
                if not self.skip_word(op):
                    continue
            else:
                if not self.skip_string(op):
                    continue
            rightExpr = self._parse_initializer_clause()
            return ASTAssignmentExpr(leftExpr, op, rightExpr)
        # just a logical-or-expression
        return leftExpr

    def _parse_constant_expression(self, inTemplate: bool) -> ASTExpression:
        # -> conditional-expression ->
        #    logical-or-expression
        #  | logical-or-expression "?" expression ":" assignment-expression
        orExpr = self._parse_logical_or_expression(inTemplate=inTemplate)
        condExpr = self._parse_conditional_expression_tail(orExpr, inTemplate)
        if condExpr is not None:
            return condExpr
        return orExpr

    def _parse_expression(self) -> ASTExpression:
        # -> assignment-expression
        #  | expression "," assignment-expression
        exprs = [self._parse_assignment_expression(inTemplate=False)]
        while True:
            self.skip_ws()
            if not self.skip_string(','):
                break
            exprs.append(self._parse_assignment_expression(inTemplate=False))
        if len(exprs) == 1:
            return exprs[0]
        else:
            return ASTCommaExpr(exprs)

    def _parse_expression_fallback(self, end: list[str],
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
            brackets = {'(': ')', '{': '}', '[': ']', '<': '>'}
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

    # ==========================================================================

    def _parse_operator(self) -> ASTOperator:
        self.skip_ws()
        # adapted from the old code
        # yay, a regular operator definition
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
            if not self.match(identifier_re):
                self.fail("Expected user-defined literal suffix.")
            identifier = ASTIdentifier(self.matched_text)
            return ASTOperatorLiteral(identifier)

        # oh well, looks like a cast operator definition.
        # In that case, eat another type.
        type = self._parse_type(named=False, outer="operatorCast")
        return ASTOperatorType(type)

    def _parse_template_argument_list(self) -> ASTTemplateArgs:
        # template-argument-list: (but we include the < and > here
        #    template-argument ...[opt]
        #    template-argument-list, template-argument ...[opt]
        # template-argument:
        #    constant-expression
        #    type-id
        #    id-expression
        self.skip_ws()
        if not self.skip_string_and_ws('<'):
            return None
        if self.skip_string('>'):
            return ASTTemplateArgs([], False)
        prevErrors = []
        templateArgs: list[ASTType | ASTTemplateArgConstant] = []
        packExpansion = False
        while 1:
            pos = self.pos
            parsedComma = False
            parsedEnd = False
            try:
                type = self._parse_type(named=False)
                self.skip_ws()
                if self.skip_string_and_ws('...'):
                    packExpansion = True
                    parsedEnd = True
                    if not self.skip_string('>'):
                        self.fail('Expected ">" after "..." in template argument list.')
                elif self.skip_string('>'):
                    parsedEnd = True
                elif self.skip_string(','):
                    parsedComma = True
                else:
                    self.fail('Expected "...>", ">" or "," in template argument list.')
                templateArgs.append(type)
            except DefinitionError as e:
                prevErrors.append((e, "If type argument"))
                self.pos = pos
                try:
                    value = self._parse_constant_expression(inTemplate=True)
                    self.skip_ws()
                    if self.skip_string_and_ws('...'):
                        packExpansion = True
                        parsedEnd = True
                        if not self.skip_string('>'):
                            self.fail('Expected ">" after "..." in template argument list.')
                    elif self.skip_string('>'):
                        parsedEnd = True
                    elif self.skip_string(','):
                        parsedComma = True
                    else:
                        self.fail('Expected "...>", ">" or "," in template argument list.')
                    templateArgs.append(ASTTemplateArgConstant(value))
                except DefinitionError as e:
                    self.pos = pos
                    prevErrors.append((e, "If non-type argument"))
                    header = "Error in parsing template argument list."
                    raise self._make_multi_error(prevErrors, header) from e
            if parsedEnd:
                assert not parsedComma
                break
            assert not packExpansion
        return ASTTemplateArgs(templateArgs, packExpansion)

    def _parse_nested_name(self, memberPointer: bool = False) -> ASTNestedName:
        names: list[ASTNestedNameElement] = []
        templates: list[bool] = []

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
            identOrOp: ASTIdentifier | ASTOperator = None
            if self.skip_word_and_ws('operator'):
                identOrOp = self._parse_operator()
            else:
                if not self.match(identifier_re):
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

    # ==========================================================================

    def _parse_simple_type_specifiers(self) -> ASTTrailingTypeSpecFundamental:
        modifier: str | None = None
        signedness: str | None = None
        width: list[str] = []
        typ: str | None = None
        names: list[str] = []  # the parsed sequence

        self.skip_ws()
        while self.match(_simple_type_specifiers_re):
            t = self.matched_text
            names.append(t)
            if t in ('auto', 'void', 'bool',
                     'char', 'wchar_t', 'char8_t', 'char16_t', 'char32_t',
                     'int', '__int64', '__int128',
                     'float', 'double',
                     '__float80', '_Float64x', '__float128', '_Float128'):
                if typ is not None:
                    self.fail(f"Can not have both {t} and {typ}.")
                typ = t
            elif t in ('signed', 'unsigned'):
                if signedness is not None:
                    self.fail(f"Can not have both {t} and {signedness}.")
                signedness = t
            elif t == 'short':
                if len(width) != 0:
                    self.fail(f"Can not have both {t} and {width[0]}.")
                width.append(t)
            elif t == 'long':
                if len(width) != 0 and width[0] != 'long':
                    self.fail(f"Can not have both {t} and {width[0]}.")
                width.append(t)
            elif t in ('_Imaginary', '_Complex'):
                if modifier is not None:
                    self.fail(f"Can not have both {t} and {modifier}.")
                modifier = t
            self.skip_ws()
        if len(names) == 0:
            return None

        if typ in ('auto', 'void', 'bool',
                   'wchar_t', 'char8_t', 'char16_t', 'char32_t',
                   '__float80', '_Float64x', '__float128', '_Float128'):
            if modifier is not None:
                self.fail(f"Can not have both {typ} and {modifier}.")
            if signedness is not None:
                self.fail(f"Can not have both {typ} and {signedness}.")
            if len(width) != 0:
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
        elif typ == 'char':
            if modifier is not None:
                self.fail(f"Can not have both {typ} and {modifier}.")
            if len(width) != 0:
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
        elif typ == 'int':
            if modifier is not None:
                self.fail(f"Can not have both {typ} and {modifier}.")
        elif typ in ('__int64', '__int128'):
            if modifier is not None:
                self.fail(f"Can not have both {typ} and {modifier}.")
            if len(width) != 0:
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
        elif typ == 'float':
            if signedness is not None:
                self.fail(f"Can not have both {typ} and {signedness}.")
            if len(width) != 0:
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
        elif typ == 'double':
            if signedness is not None:
                self.fail(f"Can not have both {typ} and {signedness}.")
            if len(width) > 1:
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
            if len(width) == 1 and width[0] != 'long':
                self.fail(f"Can not have both {typ} and {' '.join(width)}.")
        elif typ is None:
            if modifier is not None:
                self.fail(f"Can not have {modifier} without a floating point type.")
        else:
            msg = f'Unhandled type {typ}'
            raise AssertionError(msg)

        canonNames: list[str] = []
        if modifier is not None:
            canonNames.append(modifier)
        if signedness is not None:
            canonNames.append(signedness)
        canonNames.extend(width)
        if typ is not None:
            canonNames.append(typ)
        return ASTTrailingTypeSpecFundamental(names, canonNames)

    def _parse_trailing_type_spec(self) -> ASTTrailingTypeSpec:
        # fundamental types, https://en.cppreference.com/w/cpp/language/type
        # and extensions
        self.skip_ws()
        res = self._parse_simple_type_specifiers()
        if res is not None:
            return res

        # decltype
        self.skip_ws()
        if self.skip_word_and_ws('decltype'):
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after 'decltype'.")
            if self.skip_word_and_ws('auto'):
                if not self.skip_string(')'):
                    self.fail("Expected ')' after 'decltype(auto'.")
                return ASTTrailingTypeSpecDecltypeAuto()
            expr = self._parse_expression()
            self.skip_ws()
            if not self.skip_string(')'):
                self.fail("Expected ')' after 'decltype(<expr>'.")
            return ASTTrailingTypeSpecDecltype(expr)

        # prefixed
        prefix = None
        self.skip_ws()
        for k in ('class', 'struct', 'enum', 'union', 'typename'):
            if self.skip_word_and_ws(k):
                prefix = k
                break
        nestedName = self._parse_nested_name()
        self.skip_ws()
        placeholderType = None
        if self.skip_word('auto'):
            placeholderType = 'auto'
        elif self.skip_word_and_ws('decltype'):
            if not self.skip_string_and_ws('('):
                self.fail("Expected '(' after 'decltype' in placeholder type specifier.")
            if not self.skip_word_and_ws('auto'):
                self.fail("Expected 'auto' after 'decltype(' in placeholder type specifier.")
            if not self.skip_string_and_ws(')'):
                self.fail("Expected ')' after 'decltype(auto' in placeholder type specifier.")
            placeholderType = 'decltype(auto)'
        return ASTTrailingTypeSpecName(prefix, nestedName, placeholderType)

    def _parse_parameters_and_qualifiers(self, paramMode: str) -> ASTParametersQualifiers:
        if paramMode == 'new':
            return None
        self.skip_ws()
        if not self.skip_string('('):
            if paramMode == 'function':
                self.fail('Expecting "(" in parameters-and-qualifiers.')
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
                                  'parameters-and-qualifiers.')
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
                self.fail('Expecting "," or ")" in parameters-and-qualifiers, '
                          f'got "{self.current_char}".')

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
        self.skip_ws()
        if self.skip_string('noexcept'):
            if self.skip_string_and_ws('('):
                expr = self._parse_constant_expression(False)
                self.skip_ws()
                if not self.skip_string(')'):
                    self.fail("Expecting ')' to end 'noexcept'.")
                exceptionSpec = ASTNoexceptSpec(expr)
            else:
                exceptionSpec = ASTNoexceptSpec(None)

        self.skip_ws()
        if self.skip_string('->'):
            trailingReturn = self._parse_type(named=False)
        else:
            trailingReturn = None

        self.skip_ws()
        override = self.skip_word_and_ws('override')
        final = self.skip_word_and_ws('final')
        if not override:
            override = self.skip_word_and_ws(
                'override')  # they can be permuted

        attrs = self._parse_attribute_list()

        self.skip_ws()
        initializer = None
        # if this is a function pointer we should not swallow an initializer
        if paramMode == 'function' and self.skip_string('='):
            self.skip_ws()
            valid = ('0', 'delete', 'default')
            for w in valid:
                if self.skip_word_and_ws(w):
                    initializer = w
                    break
            if not initializer:
                self.fail(
                    'Expected "%s" in initializer-specifier.'
                    % '" or "'.join(valid))

        return ASTParametersQualifiers(
            args, volatile, const, refQual, exceptionSpec, trailingReturn,
            override, final, attrs, initializer)

    def _parse_decl_specs_simple(self, outer: str, typed: bool) -> ASTDeclSpecsSimple:
        """Just parse the simple ones."""
        storage = None
        threadLocal = None
        inline = None
        virtual = None
        explicitSpec = None
        consteval = None
        constexpr = None
        constinit = None
        volatile = None
        const = None
        friend = None
        attrs = []
        while 1:  # accept any permutation of a subset of some decl-specs
            self.skip_ws()
            if not const and typed:
                const = self.skip_word('const')
                if const:
                    continue
            if not volatile and typed:
                volatile = self.skip_word('volatile')
                if volatile:
                    continue
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
            if not inline and outer in ('function', 'member'):
                inline = self.skip_word('inline')
                if inline:
                    continue
            if not constexpr and outer in ('member', 'function'):
                constexpr = self.skip_word("constexpr")
                if constexpr:
                    continue

            if outer == 'member':
                if not constinit:
                    constinit = self.skip_word('constinit')
                    if constinit:
                        continue
                if not threadLocal:
                    threadLocal = self.skip_word('thread_local')
                    if threadLocal:
                        continue
            if outer == 'function':
                if not consteval:
                    consteval = self.skip_word('consteval')
                    if consteval:
                        continue
                if not friend:
                    friend = self.skip_word('friend')
                    if friend:
                        continue
                if not virtual:
                    virtual = self.skip_word('virtual')
                    if virtual:
                        continue
                if not explicitSpec:
                    explicit = self.skip_word_and_ws('explicit')
                    if explicit:
                        expr: ASTExpression = None
                        if self.skip_string('('):
                            expr = self._parse_constant_expression(inTemplate=False)
                            if not expr:
                                self.fail("Expected constant expression after '('" +
                                          " in explicit specifier.")
                            self.skip_ws()
                            if not self.skip_string(')'):
                                self.fail("Expected ')' to end explicit specifier.")
                        explicitSpec = ASTExplicitSpec(expr)
                        continue
            attr = self._parse_attribute()
            if attr:
                attrs.append(attr)
                continue
            break
        return ASTDeclSpecsSimple(storage, threadLocal, inline, virtual,
                                  explicitSpec, consteval, constexpr, constinit,
                                  volatile, const, friend, ASTAttributeList(attrs))

    def _parse_decl_specs(self, outer: str, typed: bool = True) -> ASTDeclSpecs:
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

    def _parse_declarator_name_suffix(
        self, named: bool | str, paramMode: str, typed: bool,
    ) -> ASTDeclaratorNameParamQual | ASTDeclaratorNameBitField:
        # now we should parse the name, and then suffixes
        if named == 'maybe':
            pos = self.pos
            try:
                declId = self._parse_nested_name()
            except DefinitionError:
                self.pos = pos
                declId = None
        elif named == 'single':
            if self.match(identifier_re):
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

                def parser() -> ASTExpression:
                    return self._parse_expression()
                value = self._parse_expression_fallback([']'], parser)
                if not self.skip_string(']'):
                    self.fail("Expected ']' in end of array operator.")
                arrayOps.append(ASTArray(value))
                continue
            break
        paramQual = self._parse_parameters_and_qualifiers(paramMode)
        if paramQual is None and len(arrayOps) == 0:
            # perhaps a bit-field
            if named and paramMode == 'type' and typed:
                self.skip_ws()
                if self.skip_string(':'):
                    size = self._parse_constant_expression(inTemplate=False)
                    return ASTDeclaratorNameBitField(declId=declId, size=size)
        return ASTDeclaratorNameParamQual(declId=declId, arrayOps=arrayOps,
                                          paramQual=paramQual)

    def _parse_declarator(self, named: bool | str, paramMode: str,
                          typed: bool = True,
                          ) -> ASTDeclarator:
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
            attrList = []
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
                    attrList.append(attr)
                    continue
                break
            next = self._parse_declarator(named, paramMode, typed)
            return ASTDeclaratorPtr(next=next, volatile=volatile, const=const,
                                    attrs=ASTAttributeList(attrList))
        # TODO: shouldn't we parse an R-value ref here first?
        if typed and self.skip_string("&"):
            attrs = self._parse_attribute_list()
            next = self._parse_declarator(named, paramMode, typed)
            return ASTDeclaratorRef(next=next, attrs=attrs)
        if typed and self.skip_string("..."):
            next = self._parse_declarator(named, paramMode, False)
            return ASTDeclaratorParamPack(next=next)
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
                res = self._parse_declarator_name_suffix(named, paramMode,
                                                         typed)
                return res
            except DefinitionError as exParamQual:
                prevErrors.append((exParamQual,
                                   "If declarator-id with parameters-and-qualifiers"))
                self.pos = pos
                try:
                    assert self.current_char == '('
                    self.skip_string('(')
                    # TODO: hmm, if there is a name, it must be in inner, right?
                    # TODO: hmm, if there must be parameters, they must be
                    #       inside, right?
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
                    raise self._make_multi_error(prevErrors, header) from exNoPtrParen
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
        pos = self.pos
        try:
            res = self._parse_declarator_name_suffix(named, paramMode, typed)
            # this is a heuristic for error messages, for when there is a < after a
            # nested name, but it was not a successful template argument list
            if self.current_char == '<':
                self.otherErrors.append(self._make_multi_error(prevErrors, ""))
            return res
        except DefinitionError as e:
            self.pos = pos
            prevErrors.append((e, "If declarator-id"))
            header = "Error in declarator or parameters-and-qualifiers"
            raise self._make_multi_error(prevErrors, header) from e

    def _parse_initializer(self, outer: str | None = None, allowFallback: bool = True,
                           ) -> ASTInitializer:
        # initializer                           # global vars
        # -> brace-or-equal-initializer
        #  | '(' expression-list ')'
        #
        # brace-or-equal-initializer            # member vars
        # -> '=' initializer-clause
        #  | braced-init-list
        #
        # initializer-clause  # function params, non-type template params (with '=' in front)
        # -> assignment-expression
        #  | braced-init-list
        #
        # we don't distinguish between global and member vars, so disallow paren:
        #
        # -> braced-init-list             # var only
        #  | '=' assignment-expression
        #  | '=' braced-init-list
        self.skip_ws()
        if outer == 'member':
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
        elif outer == 'templateParam':
            fallbackEnd = [',', '>']
        elif outer is None:  # function parameter
            fallbackEnd = [',', ')']
        else:
            self.fail("Internal error, initializer for outer '%s' not "
                      "implemented." % outer)

        inTemplate = outer == 'templateParam'

        def parser() -> ASTExpression:
            return self._parse_assignment_expression(inTemplate=inTemplate)
        value = self._parse_expression_fallback(fallbackEnd, parser, allow=allowFallback)
        return ASTInitializer(value)

    def _parse_type(self, named: bool | str, outer: str | None = None) -> ASTType:
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
            # destructors, cast operators
            prevErrors = []
            startPos = self.pos
            # first try without the type
            try:
                declSpecs = self._parse_decl_specs(outer=outer, typed=False)
                decl = self._parse_declarator(named=True, paramMode=outer,
                                              typed=False)
                mustEnd = True
                if outer == 'function':
                    # Allow trailing requires on functions.
                    self.skip_ws()
                    if re.compile(r'requires\b').match(self.definition, self.pos):
                        mustEnd = False
                if mustEnd:
                    self.assert_end(allowSemicolon=True)
            except DefinitionError as exUntyped:
                if outer == 'type':
                    desc = "If just a name"
                elif outer == 'function':
                    desc = "If the function has no return type"
                else:
                    raise AssertionError from exUntyped
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
                        raise AssertionError from exUntyped
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
                            raise AssertionError from exUntyped
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
        else:
            paramMode = 'type'
            if outer == 'member':
                named = True
            elif outer == 'operatorCast':
                paramMode = 'operatorCast'
                outer = None
            elif outer == 'templateParam':
                named = 'single'
            declSpecs = self._parse_decl_specs(outer=outer)
            decl = self._parse_declarator(named=named, paramMode=paramMode)
        return ASTType(declSpecs, decl)

    def _parse_type_with_init(
            self, named: bool | str,
            outer: str) -> ASTTypeWithInit | ASTTemplateParamConstrainedTypeWithInit:
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
                raise
            errs = []
            errs.append((eExpr, "If default template argument is an expression"))
            errs.append((eType, "If default template argument is a type"))
            msg = "Error in non-type template parameter"
            msg += " or constrained template parameter."
            raise self._make_multi_error(errs, msg) from eType

    def _parse_type_using(self) -> ASTTypeUsing:
        name = self._parse_nested_name()
        self.skip_ws()
        if not self.skip_string('='):
            return ASTTypeUsing(name, None)
        type = self._parse_type(False, None)
        return ASTTypeUsing(name, type)

    def _parse_concept(self) -> ASTConcept:
        nestedName = self._parse_nested_name()
        self.skip_ws()
        initializer = self._parse_initializer('member')
        return ASTConcept(nestedName, initializer)

    def _parse_class(self) -> ASTClass:
        attrs = self._parse_attribute_list()
        name = self._parse_nested_name()
        self.skip_ws()
        final = self.skip_word_and_ws('final')
        bases = []
        self.skip_ws()
        if self.skip_string(':'):
            while 1:
                self.skip_ws()
                visibility = None
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
                break
        return ASTClass(name, final, bases, attrs)

    def _parse_union(self) -> ASTUnion:
        attrs = self._parse_attribute_list()
        name = self._parse_nested_name()
        return ASTUnion(name, attrs)

    def _parse_enum(self) -> ASTEnum:
        scoped = None  # is set by CPPEnumObject
        attrs = self._parse_attribute_list()
        name = self._parse_nested_name()
        self.skip_ws()
        underlyingType = None
        if self.skip_string(':'):
            underlyingType = self._parse_type(named=False)
        return ASTEnum(name, scoped, underlyingType, attrs)

    def _parse_enumerator(self) -> ASTEnumerator:
        name = self._parse_nested_name()
        attrs = self._parse_attribute_list()
        self.skip_ws()
        init = None
        if self.skip_string('='):
            self.skip_ws()

            def parser() -> ASTExpression:
                return self._parse_constant_expression(inTemplate=False)
            initVal = self._parse_expression_fallback([], parser)
            init = ASTInitializer(initVal)
        return ASTEnumerator(name, init, attrs)

    # ==========================================================================

    def _parse_template_parameter(self) -> ASTTemplateParam:
        self.skip_ws()
        if self.skip_word('template'):
            # declare a template template parameter
            nestedParams = self._parse_template_parameter_list()
        else:
            nestedParams = None

        pos = self.pos
        try:
            # Unconstrained type parameter or template type parameter
            key = None
            self.skip_ws()
            if self.skip_word_and_ws('typename'):
                key = 'typename'
            elif self.skip_word_and_ws('class'):
                key = 'class'
            elif nestedParams:
                self.fail("Expected 'typename' or 'class' after "
                          "template template parameter list.")
            else:
                self.fail("Expected 'typename' or 'class' in the "
                          "beginning of template type parameter.")
            self.skip_ws()
            parameterPack = self.skip_string('...')
            self.skip_ws()
            if self.match(identifier_re):
                identifier = ASTIdentifier(self.matched_text)
            else:
                identifier = None
            self.skip_ws()
            if not parameterPack and self.skip_string('='):
                default = self._parse_type(named=False, outer=None)
            else:
                default = None
                if self.current_char not in ',>':
                    self.fail('Expected "," or ">" after (template) type parameter.')
            data = ASTTemplateKeyParamPackIdDefault(key, identifier,
                                                    parameterPack, default)
            if nestedParams:
                return ASTTemplateParamTemplateType(nestedParams, data)
            else:
                return ASTTemplateParamType(data)
        except DefinitionError as eType:
            if nestedParams:
                raise
            try:
                # non-type parameter or constrained type parameter
                self.pos = pos
                param = self._parse_type_with_init('maybe', 'templateParam')
                self.skip_ws()
                parameterPack = self.skip_string('...')
                return ASTTemplateParamNonType(param, parameterPack)
            except DefinitionError as eNonType:
                self.pos = pos
                header = "Error when parsing template parameter."
                errs = []
                errs.append(
                    (eType, "If unconstrained type parameter or template type parameter"))
                errs.append(
                    (eNonType, "If constrained type parameter or non-type parameter"))
                raise self._make_multi_error(errs, header) from None

    def _parse_template_parameter_list(self) -> ASTTemplateParams:
        # only: '<' parameter-list '>'
        # we assume that 'template' has just been parsed
        templateParams: list[ASTTemplateParam] = []
        self.skip_ws()
        if not self.skip_string("<"):
            self.fail("Expected '<' after 'template'")
        while 1:
            pos = self.pos
            err = None
            try:
                param = self._parse_template_parameter()
                templateParams.append(param)
            except DefinitionError as eParam:
                self.pos = pos
                err = eParam
            self.skip_ws()
            if self.skip_string('>'):
                requiresClause = self._parse_requires_clause()
                return ASTTemplateParams(templateParams, requiresClause)
            elif self.skip_string(','):
                continue
            else:
                header = "Error in template parameter list."
                errs = []
                if err:
                    errs.append((err, "If parameter"))
                try:
                    self.fail('Expected "," or ">".')
                except DefinitionError as e:
                    errs.append((e, "If no parameter"))
                logger.debug(errs)
                raise self._make_multi_error(errs, header)

    def _parse_template_introduction(self) -> ASTTemplateIntroduction:
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
            if not self.match(identifier_re):
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
            if self.skip_string(','):
                continue
            self.fail('Error in template introduction list. Expected ",", or "}".')
        return ASTTemplateIntroduction(concept, params)

    def _parse_requires_clause(self) -> ASTRequiresClause | None:
        # requires-clause -> 'requires' constraint-logical-or-expression
        # constraint-logical-or-expression
        #   -> constraint-logical-and-expression
        #    | constraint-logical-or-expression '||' constraint-logical-and-expression
        # constraint-logical-and-expression
        #   -> primary-expression
        #    | constraint-logical-and-expression '&&' primary-expression
        self.skip_ws()
        if not self.skip_word('requires'):
            return None

        def parse_and_expr(self: DefinitionParser) -> ASTExpression:
            andExprs = []
            ops = []
            andExprs.append(self._parse_primary_expression())
            while True:
                self.skip_ws()
                oneMore = False
                if self.skip_string('&&'):
                    oneMore = True
                    ops.append('&&')
                elif self.skip_word('and'):
                    oneMore = True
                    ops.append('and')
                if not oneMore:
                    break
                andExprs.append(self._parse_primary_expression())
            if len(andExprs) == 1:
                return andExprs[0]
            else:
                return ASTBinOpExpr(andExprs, ops)

        orExprs = []
        ops = []
        orExprs.append(parse_and_expr(self))
        while True:
            self.skip_ws()
            oneMore = False
            if self.skip_string('||'):
                oneMore = True
                ops.append('||')
            elif self.skip_word('or'):
                oneMore = True
                ops.append('or')
            if not oneMore:
                break
            orExprs.append(parse_and_expr(self))
        if len(orExprs) == 1:
            return ASTRequiresClause(orExprs[0])
        else:
            return ASTRequiresClause(ASTBinOpExpr(orExprs, ops))

    def _parse_template_declaration_prefix(self, objectType: str,
                                           ) -> ASTTemplateDeclarationPrefix | None:
        templates: list[ASTTemplateParams | ASTTemplateIntroduction] = []
        while 1:
            self.skip_ws()
            # the saved position is only used to provide a better error message
            params: ASTTemplateParams | ASTTemplateIntroduction = None
            pos = self.pos
            if self.skip_word("template"):
                try:
                    params = self._parse_template_parameter_list()
                except DefinitionError as e:
                    if objectType == 'member' and len(templates) == 0:
                        return ASTTemplateDeclarationPrefix(None)
                    else:
                        raise e
                if objectType == 'concept' and params.requiresClause is not None:
                    self.fail('requires-clause not allowed for concept')
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

    def _check_template_consistency(self, nestedName: ASTNestedName,
                                    templatePrefix: ASTTemplateDeclarationPrefix,
                                    fullSpecShorthand: bool, isMember: bool = False,
                                    ) -> ASTTemplateDeclarationPrefix:
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
                    % (numArgs, numParams, numExtra)
                msg += " Declaration:\n\t"
                if templatePrefix:
                    msg += "%s\n\t" % templatePrefix
                msg += str(nestedName)
                self.warn(msg)

            newTemplates: list[ASTTemplateParams | ASTTemplateIntroduction] = []
            for _i in range(numExtra):
                newTemplates.append(ASTTemplateParams([], requiresClause=None))
            if templatePrefix and not isMemberInstantiation:
                newTemplates.extend(templatePrefix.templates)
            templatePrefix = ASTTemplateDeclarationPrefix(newTemplates)
        return templatePrefix

    def parse_declaration(self, objectType: str, directiveType: str) -> ASTDeclaration:
        if objectType not in ('class', 'union', 'function', 'member', 'type',
                              'concept', 'enum', 'enumerator'):
            raise Exception('Internal error, unknown objectType "%s".' % objectType)
        if directiveType not in ('class', 'struct', 'union', 'function', 'member', 'var',
                                 'type', 'concept',
                                 'enum', 'enum-struct', 'enum-class', 'enumerator'):
            raise Exception('Internal error, unknown directiveType "%s".' % directiveType)
        visibility = None
        templatePrefix = None
        trailingRequiresClause = None
        declaration: Any = None

        self.skip_ws()
        if self.match(_visibility_re):
            visibility = self.matched_text

        if objectType in ('type', 'concept', 'member', 'function', 'class', 'union'):
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
                raise self._make_multi_error(prevErrors, header) from e
        elif objectType == 'concept':
            declaration = self._parse_concept()
        elif objectType == 'member':
            declaration = self._parse_type_with_init(named=True, outer='member')
        elif objectType == 'function':
            declaration = self._parse_type(named=True, outer='function')
            trailingRequiresClause = self._parse_requires_clause()
        elif objectType == 'class':
            declaration = self._parse_class()
        elif objectType == 'union':
            declaration = self._parse_union()
        elif objectType == 'enum':
            declaration = self._parse_enum()
        elif objectType == 'enumerator':
            declaration = self._parse_enumerator()
        else:
            raise AssertionError
        templatePrefix = self._check_template_consistency(declaration.name,
                                                          templatePrefix,
                                                          fullSpecShorthand=False,
                                                          isMember=objectType == 'member')
        self.skip_ws()
        semicolon = self.skip_string(';')
        return ASTDeclaration(objectType, directiveType, visibility,
                              templatePrefix, declaration,
                              trailingRequiresClause, semicolon)

    def parse_namespace_object(self) -> ASTNamespace:
        templatePrefix = self._parse_template_declaration_prefix(objectType="namespace")
        name = self._parse_nested_name()
        templatePrefix = self._check_template_consistency(name, templatePrefix,
                                                          fullSpecShorthand=False)
        res = ASTNamespace(name, templatePrefix)
        res.objectType = 'namespace'  # type: ignore[attr-defined]
        return res

    def parse_xref_object(self) -> tuple[ASTNamespace | ASTDeclaration, bool]:
        pos = self.pos
        try:
            templatePrefix = self._parse_template_declaration_prefix(objectType="xref")
            name = self._parse_nested_name()
            # if there are '()' left, just skip them
            self.skip_ws()
            self.skip_string('()')
            self.assert_end()
            templatePrefix = self._check_template_consistency(name, templatePrefix,
                                                              fullSpecShorthand=True)
            res1 = ASTNamespace(name, templatePrefix)
            res1.objectType = 'xref'  # type: ignore[attr-defined]
            return res1, True
        except DefinitionError as e1:
            try:
                self.pos = pos
                res2 = self.parse_declaration('function', 'function')
                # if there are '()' left, just skip them
                self.skip_ws()
                self.skip_string('()')
                self.assert_end()
                return res2, False
            except DefinitionError as e2:
                errs = []
                errs.append((e1, "If shorthand ref"))
                errs.append((e2, "If full function ref"))
                msg = "Error in cross-reference."
                raise self._make_multi_error(errs, msg) from e2

    def parse_expression(self) -> ASTExpression | ASTType:
        pos = self.pos
        try:
            expr = self._parse_expression()
            self.skip_ws()
            self.assert_end()
            return expr
        except DefinitionError as exExpr:
            self.pos = pos
            try:
                typ = self._parse_type(False)
                self.skip_ws()
                self.assert_end()
                return typ
            except DefinitionError as exType:
                header = "Error when parsing (type) expression."
                errs = []
                errs.append((exExpr, "If expression"))
                errs.append((exType, "If type"))
                raise self._make_multi_error(errs, header) from exType


def _make_phony_error_name() -> ASTNestedName:
    nne = ASTNestedNameElement(ASTIdentifier("PhonyNameDueToError"), None)
    return ASTNestedName([nne], [False], rooted=False)


class CPPObject(ObjectDescription[ASTDeclaration]):
    """Description of a C++ language object."""

    doc_field_types: list[Field] = [
        GroupedField('template parameter', label=_('Template Parameters'),
                     names=('tparam', 'template parameter'),
                     can_collapse=True),
    ]

    option_spec: OptionSpec = {
        'no-index-entry': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindexentry': directives.flag,
        'nocontentsentry': directives.flag,
        'tparam-line-spec': directives.flag,
        'single-line-parameter-list': directives.flag,
    }

    def _add_enumerator_to_parent(self, ast: ASTDeclaration) -> None:
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
        if parentDecl.directiveType != 'enum':
            return

        targetSymbol = parentSymbol.parent
        s = targetSymbol.find_identifier(symbol.identOrOp, matchSelf=False, recurseInAnon=True,
                                         searchInSiblings=False)
        if s is not None:
            # something is already declared with that name
            return
        declClone = symbol.declaration.clone()
        declClone.enumeratorScopedSymbol = symbol
        Symbol(parent=targetSymbol, identOrOp=symbol.identOrOp,
               templateParams=None, templateArgs=None,
               declaration=declClone,
               docname=self.env.docname, line=self.get_source_info()[1])

    def add_target_and_index(self, ast: ASTDeclaration, sig: str,
                             signode: TextElement) -> None:
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
            logger.warning('Index id generation for C++ object "%s" failed, please '
                           'report as bug (id=%s).', ast, newestId,
                           location=self.get_location())

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
        if not isInConcept and 'no-index-entry' not in self.options:
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

    @property
    def object_type(self) -> str:
        raise NotImplementedError

    @property
    def display_object_type(self) -> str:
        return self.object_type

    def get_index_text(self, name: str) -> str:
        return _('%s (C++ %s)') % (name, self.display_object_type)

    def parse_definition(self, parser: DefinitionParser) -> ASTDeclaration:
        return parser.parse_declaration(self.object_type, self.objtype)

    def describe_signature(self, signode: desc_signature,
                           ast: ASTDeclaration, options: dict) -> None:
        ast.describe_signature(signode, 'lastIsName', self.env, options)

    def run(self) -> list[Node]:
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
            msg = ("C++ declarations inside functions are not supported. "
                   f"Parent function: {parentSymbol.get_full_nested_name()}\n"
                   f"Directive name: {self.name}\nDirective arg: {self.arguments[0]}")
            logger.warning(msg, location=self.get_location())
            name = _make_phony_error_name()
            symbol = parentSymbol.add_name(name)
            env.temp_data['cpp:last_symbol'] = symbol
            return []
        # When multiple declarations are made in the same directive
        # they need to know about each other to provide symbol lookup for function parameters.
        # We use last_symbol to store the latest added declaration in a directive.
        env.temp_data['cpp:last_symbol'] = None
        return super().run()

    def handle_signature(self, sig: str, signode: desc_signature) -> ASTDeclaration:
        parentSymbol: Symbol = self.env.temp_data['cpp:parent_symbol']

        max_len = (self.env.config.cpp_maximum_signature_line_length
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
            self.env.temp_data['cpp:last_symbol'] = symbol
            raise ValueError from e

        try:
            symbol = parentSymbol.add_declaration(
                ast, docname=self.env.docname, line=self.get_source_info()[1])
            # append the new declaration to the sibling list
            assert symbol.siblingAbove is None
            assert symbol.siblingBelow is None
            symbol.siblingAbove = self.env.temp_data['cpp:last_symbol']
            if symbol.siblingAbove is not None:
                assert symbol.siblingAbove.siblingBelow is None
                symbol.siblingAbove.siblingBelow = symbol
            self.env.temp_data['cpp:last_symbol'] = symbol
        except _DuplicateSymbolError as e:
            # Assume we are actually in the old symbol,
            # instead of the newly created duplicate.
            self.env.temp_data['cpp:last_symbol'] = e.symbol
            msg = __("Duplicate C++ declaration, also defined at %s:%s.\n"
                     "Declaration is '.. cpp:%s:: %s'.")
            msg = msg % (e.symbol.docname, e.symbol.line,
                         self.display_object_type, sig)
            logger.warning(msg, location=signode)

        if ast.objectType == 'enumerator':
            self._add_enumerator_to_parent(ast)

        # note: handle_signature may be called multiple time per directive,
        # if it has multiple signatures, so don't mess with the original options.
        options = dict(self.options)
        options['tparam-line-spec'] = 'tparam-line-spec' in self.options
        self.describe_signature(signode, ast, options)
        return ast

    def before_content(self) -> None:
        lastSymbol: Symbol = self.env.temp_data['cpp:last_symbol']
        assert lastSymbol
        self.oldParentSymbol = self.env.temp_data['cpp:parent_symbol']
        self.oldParentKey: LookupKey = self.env.ref_context['cpp:parent_key']
        self.env.temp_data['cpp:parent_symbol'] = lastSymbol
        self.env.ref_context['cpp:parent_key'] = lastSymbol.get_lookup_key()
        self.env.temp_data['cpp:domain_name'] = (
            *self.env.temp_data.get('cpp:domain_name', ()),
            lastSymbol.identOrOp._stringify(str),
        )

    def after_content(self) -> None:
        self.env.temp_data['cpp:parent_symbol'] = self.oldParentSymbol
        self.env.ref_context['cpp:parent_key'] = self.oldParentKey
        self.env.temp_data['cpp:domain_name'] = self.env.temp_data['cpp:domain_name'][:-1]

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        return tuple(s.identOrOp._stringify(str) for s in
                     self.env.temp_data['cpp:last_symbol'].get_full_nested_name().names)

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
            return '::'.join((*self.env.temp_data.get('cpp:domain_name', ()), name + parens))
        if config.toc_object_entries_show_parents == 'hide':
            return name + parens
        if config.toc_object_entries_show_parents == 'all':
            return '::'.join(parents + [name + parens])
        return ''


class CPPTypeObject(CPPObject):
    object_type = 'type'


class CPPConceptObject(CPPObject):
    object_type = 'concept'


class CPPMemberObject(CPPObject):
    object_type = 'member'


class CPPFunctionObject(CPPObject):
    object_type = 'function'

    doc_field_types = CPPObject.doc_field_types + [
        GroupedField('parameter', label=_('Parameters'),
                     names=('param', 'parameter', 'arg', 'argument'),
                     can_collapse=True),
        GroupedField('exceptions', label=_('Throws'), rolename='expr',
                     names=('throws', 'throw', 'exception'),
                     can_collapse=True),
        GroupedField('retval', label=_('Return values'),
                     names=('retvals', 'retval'),
                     can_collapse=True),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
    ]


class CPPClassObject(CPPObject):
    object_type = 'class'

    @property
    def display_object_type(self) -> str:
        # the distinction between class and struct is only cosmetic
        assert self.objtype in ('class', 'struct')
        return self.objtype


class CPPUnionObject(CPPObject):
    object_type = 'union'


class CPPEnumObject(CPPObject):
    object_type = 'enum'


class CPPEnumeratorObject(CPPObject):
    object_type = 'enumerator'


class CPPNamespaceObject(SphinxDirective):
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
        rootSymbol = self.env.domaindata['cpp']['root_symbol']
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            symbol = rootSymbol
            stack: list[Symbol] = []
        else:
            parser = DefinitionParser(self.arguments[0],
                                      location=self.get_location(),
                                      config=self.config)
            try:
                ast = parser.parse_namespace_object()
                parser.assert_end()
            except DefinitionError as e:
                logger.warning(e, location=self.get_location())
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
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        if self.arguments[0].strip() in ('NULL', '0', 'nullptr'):
            return []
        parser = DefinitionParser(self.arguments[0],
                                  location=self.get_location(),
                                  config=self.config)
        try:
            ast = parser.parse_namespace_object()
            parser.assert_end()
        except DefinitionError as e:
            logger.warning(e, location=self.get_location())
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
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        stack = self.env.temp_data.get('cpp:namespace_stack', None)
        if not stack or len(stack) == 0:
            logger.warning("C++ namespace pop on empty stack. Defaulting to global scope.",
                           location=self.get_location())
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


class AliasNode(nodes.Element):
    def __init__(self, sig: str, aliasOptions: dict,
                 env: BuildEnvironment | None = None,
                 parentKey: LookupKey | None = None) -> None:
        super().__init__()
        self.sig = sig
        self.aliasOptions = aliasOptions
        if env is not None:
            if 'cpp:parent_symbol' not in env.temp_data:
                root = env.domaindata['cpp']['root_symbol']
                env.temp_data['cpp:parent_symbol'] = root
                env.ref_context['cpp:parent_key'] = root.get_lookup_key()
            self.parentKey = env.ref_context['cpp:parent_key']
        else:
            assert parentKey is not None
            self.parentKey = parentKey

    def copy(self) -> AliasNode:
        return self.__class__(self.sig, self.aliasOptions,
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
                desc['domain'] = 'cpp'
                # 'desctype' is a backwards compatible attribute
                desc['objtype'] = desc['desctype'] = 'alias'
                desc['no-index'] = True
                childContainer = desc

            for sChild in s._children:
                if sChild.declaration is None:
                    continue
                if sChild.declaration.objectType in ("templateParam", "functionParam"):
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
                ast, isShorthand = parser.parse_xref_object()
                parser.assert_end()
            except DefinitionError as e:
                logger.warning(e, location=node)
                ast, isShorthand = None, None

            if ast is None:
                # could not be parsed, so stop here
                signode = addnodes.desc_signature(sig, '')
                signode.clear()
                signode += addnodes.desc_name(sig, sig)
                node.replace_self(signode)
                continue

            rootSymbol: Symbol = self.env.domains['cpp'].data['root_symbol']
            parentSymbol: Symbol = rootSymbol.direct_lookup(parentKey)
            if not parentSymbol:
                logger.debug("Target: %s", sig)
                logger.debug("ParentKey: %s", parentKey)
                logger.debug(rootSymbol.dump(1))
            assert parentSymbol  # should be there

            symbols: list[Symbol] = []
            if isShorthand:
                assert isinstance(ast, ASTNamespace)
                ns = ast
                name = ns.nestedName
                if ns.templatePrefix:
                    templateDecls = ns.templatePrefix.templates
                else:
                    templateDecls = []
                symbols, failReason = parentSymbol.find_name(
                    nestedName=name,
                    templateDecls=templateDecls,
                    typ='any',
                    templateShorthand=True,
                    matchSelf=True, recurseInAnon=True,
                    searchInSiblings=False)
                if symbols is None:
                    symbols = []
            else:
                assert isinstance(ast, ASTDeclaration)
                decl = ast
                name = decl.name
                s = parentSymbol.find_declaration(decl, 'any',
                                                  templateShorthand=True,
                                                  matchSelf=True, recurseInAnon=True)
                if s is not None:
                    symbols.append(s)

            symbols = [s for s in symbols if s.declaration is not None]

            if len(symbols) == 0:
                signode = addnodes.desc_signature(sig, '')
                node.append(signode)
                signode.clear()
                signode += addnodes.desc_name(sig, sig)

                logger.warning("Can not find C++ declaration for alias '%s'." % ast,
                               location=node)
                node.replace_self(signode)
            else:
                nodes = []
                renderOptions = {
                    'tparam-line-spec': False,
                }
                for s in symbols:
                    assert s.declaration is not None
                    res = self._render_symbol(
                        s, maxdepth=node.aliasOptions['maxdepth'],
                        skipThis=node.aliasOptions['noroot'],
                        aliasOptions=node.aliasOptions,
                        renderOptions=renderOptions,
                        document=node.document)
                    nodes.extend(res)
                node.replace_self(nodes)


class CPPAliasObject(ObjectDescription):
    option_spec: OptionSpec = {
        'maxdepth': directives.nonnegative_int,
        'noroot': directives.flag,
    }

    def run(self) -> list[Node]:
        """
        On purpose this doesn't call the ObjectDescription version, but is based on it.
        Each alias signature may expand into multiple real signatures (an overload set).
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

        self.names: list[str] = []
        aliasOptions = {
            'maxdepth': self.options.get('maxdepth', 1),
            'noroot': 'noroot' in self.options,
        }
        if aliasOptions['noroot'] and aliasOptions['maxdepth'] == 1:
            logger.warning("Error in C++ alias declaration."
                           " Requested 'noroot' but 'maxdepth' 1."
                           " When skipping the root declaration,"
                           " need 'maxdepth' 0 for infinite or at least 2.",
                           location=self.get_location())
        signatures = self.get_signatures()
        for sig in signatures:
            node.append(AliasNode(sig, aliasOptions, env=self.env))

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        self.before_content()
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        self.env.temp_data['object'] = None
        self.after_content()
        return [node]


class CPPXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        refnode.attributes.update(env.ref_context)

        if not has_explicit_title:
            # major hax: replace anon names via simple string manipulation.
            # Can this actually fail?
            title = anon_identifier_re.sub("[anonymous]", str(title))

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


class CPPExprRole(SphinxRole):
    def __init__(self, asCode: bool) -> None:
        super().__init__()
        if asCode:
            # render the expression as inline code
            self.class_type = 'cpp-expr'
        else:
            # render the expression as inline text
            self.class_type = 'cpp-texpr'

    def run(self) -> tuple[list[Node], list[system_message]]:
        text = self.text.replace('\n', ' ')
        parser = DefinitionParser(text,
                                  location=self.get_location(),
                                  config=self.config)
        # attempt to mimic XRefRole classes, except that...
        try:
            ast = parser.parse_expression()
        except DefinitionError as ex:
            logger.warning('Unparseable C++ expression: %r\n%s', text, ex,
                           location=self.get_location())
            # see below
            return [addnodes.desc_inline('cpp', text, text, classes=[self.class_type])], []
        parentSymbol = self.env.temp_data.get('cpp:parent_symbol', None)
        if parentSymbol is None:
            parentSymbol = self.env.domaindata['cpp']['root_symbol']
        # ...most if not all of these classes should really apply to the individual references,
        # not the container node
        signode = addnodes.desc_inline('cpp', classes=[self.class_type])
        ast.describe_signature(signode, 'markType', self.env, parentSymbol)
        return [signode], []


class CPPDomain(Domain):
    """C++ language domain.

    There are two 'object type' attributes being used::

    - Each object created from directives gets an assigned .objtype from ObjectDescription.run.
      This is simply the directive name.
    - Each declaration (see the distinction in the directives dict below) has a nested .ast of
      type ASTDeclaration. That object has .objectType which corresponds to the keys in the
      object_types dict below. They are the core different types of declarations in C++ that
      one can document.
    """
    name = 'cpp'
    label = 'C++'
    object_types = {
        'class':      ObjType(_('class'),      'class', 'struct',   'identifier', 'type'),
        'union':      ObjType(_('union'),      'union',             'identifier', 'type'),
        'function':   ObjType(_('function'),   'func',              'identifier', 'type'),
        'member':     ObjType(_('member'),     'member', 'var',     'identifier'),
        'type':       ObjType(_('type'),                            'identifier', 'type'),
        'concept':    ObjType(_('concept'),    'concept',           'identifier'),
        'enum':       ObjType(_('enum'),       'enum',              'identifier', 'type'),
        'enumerator': ObjType(_('enumerator'), 'enumerator',        'identifier'),
        # generated object types
        'functionParam': ObjType(_('function parameter'),           'identifier', 'member', 'var'),  # noqa: E501
        'templateParam': ObjType(_('template parameter'),
                                 'identifier', 'class', 'struct', 'union', 'member', 'var', 'type'),  # noqa: E501
    }

    directives = {
        # declarations
        'class': CPPClassObject,
        'struct': CPPClassObject,
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
        # scope control
        'namespace': CPPNamespaceObject,
        'namespace-push': CPPNamespacePushObject,
        'namespace-pop': CPPNamespacePopObject,
        # other
        'alias': CPPAliasObject,
    }
    roles = {
        'any': CPPXRefRole(),
        'class': CPPXRefRole(),
        'struct': CPPXRefRole(),
        'union': CPPXRefRole(),
        'func': CPPXRefRole(fix_parens=True),
        'member': CPPXRefRole(),
        'var': CPPXRefRole(),
        'type': CPPXRefRole(),
        'concept': CPPXRefRole(),
        'enum': CPPXRefRole(),
        'enumerator': CPPXRefRole(),
        'expr': CPPExprRole(asCode=True),
        'texpr': CPPExprRole(asCode=False),
    }
    initial_data = {
        'root_symbol': Symbol(None, None, None, None, None, None, None),
        'names': {},  # full name for indexing -> docname
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
        for name, nDocname in list(self.data['names'].items()):
            if nDocname == docname:
                del self.data['names'][name]

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

        self.data['root_symbol'].merge_with(otherdata['root_symbol'],
                                            docnames, self.env)
        ourNames = self.data['names']
        for name, docname in otherdata['names'].items():
            if docname in docnames:
                if name not in ourNames:
                    ourNames[name] = docname
                # no need to warn on duplicates, the symbol merge already does that
        if Symbol.debug_show_tree:
            logger.debug("\tresult:")
            logger.debug(self.data['root_symbol'].dump(1))
            logger.debug("\tresult end")
            logger.debug("merge_domaindata end")

    def _resolve_xref_inner(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                            typ: str, target: str, node: pending_xref,
                            contnode: Element) -> tuple[Element | None, str | None]:
        # add parens again for those that could be functions
        if typ in ('any', 'func'):
            target += '()'
        parser = DefinitionParser(target, location=node, config=env.config)
        try:
            ast, isShorthand = parser.parse_xref_object()
        except DefinitionError as e:
            # as arg to stop flake8 from complaining
            def findWarning(e: Exception) -> tuple[str, Exception]:
                if typ != 'any' and typ != 'func':
                    return target, e
                # hax on top of the paren hax to try to get correct errors
                parser2 = DefinitionParser(target[:-2],
                                           location=node,
                                           config=env.config)
                try:
                    parser2.parse_xref_object()
                except DefinitionError as e2:
                    return target[:-2], e2
                # strange, that we don't get the error now, use the original
                return target, e
            t, ex = findWarning(e)
            logger.warning('Unparseable C++ cross-reference: %r\n%s', t, ex,
                           location=node)
            return None, None
        parentKey: LookupKey = node.get("cpp:parent_key", None)
        rootSymbol = self.data['root_symbol']
        if parentKey:
            parentSymbol: Symbol = rootSymbol.direct_lookup(parentKey)
            if not parentSymbol:
                logger.debug("Target: %s", target)
                logger.debug("ParentKey: %s", parentKey.data)
                logger.debug(rootSymbol.dump(1))
            assert parentSymbol  # should be there
        else:
            parentSymbol = rootSymbol

        if isShorthand:
            assert isinstance(ast, ASTNamespace)
            ns = ast
            name = ns.nestedName
            if ns.templatePrefix:
                templateDecls = ns.templatePrefix.templates
            else:
                templateDecls = []
            # let's be conservative with the sibling lookup for now
            searchInSiblings = (not name.rooted) and len(name.names) == 1
            symbols, failReason = parentSymbol.find_name(
                name, templateDecls, typ,
                templateShorthand=True,
                matchSelf=True, recurseInAnon=True,
                searchInSiblings=searchInSiblings)
            if symbols is None:
                if typ == 'identifier':
                    if failReason == 'templateParamInQualified':
                        # this is an xref we created as part of a signature,
                        # so don't warn for names nested in template parameters
                        raise NoUri(str(name), typ)
                s = None
            else:
                # just refer to the arbitrarily first symbol
                s = symbols[0]
        else:
            assert isinstance(ast, ASTDeclaration)
            decl = ast
            name = decl.name
            s = parentSymbol.find_declaration(decl, typ,
                                              templateShorthand=True,
                                              matchSelf=True, recurseInAnon=True)
        if s is None or s.declaration is None:
            txtName = str(name)
            if txtName.startswith('std::') or txtName == 'std':
                raise NoUri(txtName, typ)
            return None, None

        if typ.startswith('cpp:'):
            typ = typ[4:]
        declTyp = s.declaration.objectType

        def checkType() -> bool:
            if typ == 'any':
                return True
            objtypes = self.objtypes_for_role(typ)
            if objtypes:
                return declTyp in objtypes
            logger.debug(f"Type is {typ}, declaration type is {declTyp}")  # NoQA: G004
            raise AssertionError
        if not checkType():
            logger.warning("cpp:%s targets a %s (%s).",
                           typ, s.declaration.objectType,
                           s.get_full_nested_name(),
                           location=node)

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
                    if (env.config.add_function_parentheses and typ == 'func' and
                            title.endswith('operator()')):
                        addParen += 1
                    if (typ in ('any', 'func') and
                            title.endswith('operator') and
                            displayName.endswith('operator()')):
                        addParen += 1
                else:
                    # our job here is to essentially nullify add_function_parentheses
                    if env.config.add_function_parentheses:
                        if typ == 'any' and displayName.endswith('()'):
                            addParen += 1
                        elif typ == 'func':
                            if title.endswith('()') and not displayName.endswith('()'):
                                title = title[:-2]
                    else:
                        if displayName.endswith('()'):
                            addParen += 1
            if addParen > 0:
                title += '()' * addParen
            # and reconstruct the title again
            contnode += nodes.Text(title)
        res = make_refnode(builder, fromdocname, docname,
                           declaration.get_newest_id(), contnode, displayName,
                           ), declaration.objectType
        return res

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
        return self._resolve_xref_inner(env, fromdocname, builder, typ,
                                        target, node, contnode)[0]

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        with logging.suppress_logging():
            retnode, objtype = self._resolve_xref_inner(env, fromdocname, builder,
                                                        'any', target, node, contnode)
        if retnode:
            if objtype == 'templateParam':
                return [('cpp:templateParam', retnode)]
            else:
                return [('cpp:' + self.role_for_objtype(objtype), retnode)]
        return []

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        rootSymbol = self.data['root_symbol']
        for symbol in rootSymbol.get_all_symbols():
            if symbol.declaration is None:
                continue
            assert symbol.docname
            fullNestedName = symbol.get_full_nested_name()
            name = str(fullNestedName).lstrip(':')
            dispname = fullNestedName.get_display_string().lstrip(':')
            objectType = symbol.declaration.objectType
            docname = symbol.docname
            newestId = symbol.declaration.get_newest_id()
            yield (name, dispname, objectType, docname, newestId, 1)

    def get_full_qualified_name(self, node: Element) -> str:
        target = node.get('reftarget', None)
        if target is None:
            return None
        parentKey: LookupKey = node.get("cpp:parent_key", None)
        if parentKey is None or len(parentKey.data) <= 0:
            return None

        rootSymbol = self.data['root_symbol']
        parentSymbol = rootSymbol.direct_lookup(parentKey)
        parentName = parentSymbol.get_full_nested_name()
        return '::'.join([str(parentName), target])


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(CPPDomain)
    app.add_config_value("cpp_index_common_prefix", [], 'env')
    app.add_config_value("cpp_id_attributes", [], 'env')
    app.add_config_value("cpp_paren_attributes", [], 'env')
    app.add_config_value("cpp_maximum_signature_line_length", None, 'env', types={int, None})
    app.add_post_transform(AliasTransform)

    # debug stuff
    app.add_config_value("cpp_debug_lookup", False, '')
    app.add_config_value("cpp_debug_show_tree", False, '')

    def initStuff(app):
        Symbol.debug_lookup = app.config.cpp_debug_lookup
        Symbol.debug_show_tree = app.config.cpp_debug_show_tree
        app.config.cpp_index_common_prefix.sort(reverse=True)
    app.connect("builder-inited", initStuff)

    return {
        'version': 'builtin',
        'env_version': 9,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
