"""
    babel.numbers
    ~~~~~~~~~~~~~

    CLDR Plural support.  See UTS #35.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import decimal
import re
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from typing_extensions import Literal

_plural_tags = ('zero', 'one', 'two', 'few', 'many', 'other')
_fallback_tag = 'other'


def extract_operands(source: float | decimal.Decimal) -> tuple[decimal.Decimal | int, int, int, int, int, int, Literal[0], Literal[0]]:
    """Extract operands from a decimal, a float or an int, according to `CLDR rules`_.

    The result is an 8-tuple (n, i, v, w, f, t, c, e), where those symbols are as follows:

    ====== ===============================================================
    Symbol Value
    ------ ---------------------------------------------------------------
    n      absolute value of the source number (integer and decimals).
    i      integer digits of n.
    v      number of visible fraction digits in n, with trailing zeros.
    w      number of visible fraction digits in n, without trailing zeros.
    f      visible fractional digits in n, with trailing zeros.
    t      visible fractional digits in n, without trailing zeros.
    c      compact decimal exponent value: exponent of the power of 10 used in compact decimal formatting.
    e      currently, synonym for ‘c’. however, may be redefined in the future.
    ====== ===============================================================

    .. _`CLDR rules`: https://www.unicode.org/reports/tr35/tr35-61/tr35-numbers.html#Operands

    :param source: A real number
    :type source: int|float|decimal.Decimal
    :return: A n-i-v-w-f-t-c-e tuple
    :rtype: tuple[decimal.Decimal, int, int, int, int, int, int, int]
    """
    n = abs(source)
    i = int(n)
    if isinstance(n, float):
        if i == n:
            n = i
        else:
            # Cast the `float` to a number via the string representation.
            # This is required for Python 2.6 anyway (it will straight out fail to
            # do the conversion otherwise), and it's highly unlikely that the user
            # actually wants the lossless conversion behavior (quoting the Python
            # documentation):
            # > If value is a float, the binary floating point value is losslessly
            # > converted to its exact decimal equivalent.
            # > This conversion can often require 53 or more digits of precision.
            # Should the user want that behavior, they can simply pass in a pre-
            # converted `Decimal` instance of desired accuracy.
            n = decimal.Decimal(str(n))

    if isinstance(n, decimal.Decimal):
        dec_tuple = n.as_tuple()
        exp = dec_tuple.exponent
        fraction_digits = dec_tuple.digits[exp:] if exp < 0 else ()
        trailing = ''.join(str(d) for d in fraction_digits)
        no_trailing = trailing.rstrip('0')
        v = len(trailing)
        w = len(no_trailing)
        f = int(trailing or 0)
        t = int(no_trailing or 0)
    else:
        v = w = f = t = 0
    c = e = 0  # TODO: c and e are not supported
    return n, i, v, w, f, t, c, e


class PluralRule:
    """Represents a set of language pluralization rules.  The constructor
    accepts a list of (tag, expr) tuples or a dict of `CLDR rules`_. The
    resulting object is callable and accepts one parameter with a positive or
    negative number (both integer and float) for the number that indicates the
    plural form for a string and returns the tag for the format:

    >>> rule = PluralRule({'one': 'n is 1'})
    >>> rule(1)
    'one'
    >>> rule(2)
    'other'

    Currently the CLDR defines these tags: zero, one, two, few, many and
    other where other is an implicit default.  Rules should be mutually
    exclusive; for a given numeric value, only one rule should apply (i.e.
    the condition should only be true for one of the plural rule elements.

    .. _`CLDR rules`: https://www.unicode.org/reports/tr35/tr35-33/tr35-numbers.html#Language_Plural_Rules
    """

    __slots__ = ('abstract', '_func')

    def __init__(self, rules: Mapping[str, str] | Iterable[tuple[str, str]]) -> None:
        """Initialize the rule instance.

        :param rules: a list of ``(tag, expr)``) tuples with the rules
                      conforming to UTS #35 or a dict with the tags as keys
                      and expressions as values.
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, Mapping):
            rules = rules.items()
        found = set()
        self.abstract: list[tuple[str, Any]] = []
        for key, expr in sorted(rules):
            if key not in _plural_tags:
                raise ValueError(f"unknown tag {key!r}")
            elif key in found:
                raise ValueError(f"tag {key!r} defined twice")
            found.add(key)
            ast = _Parser(expr).ast
            if ast:
                self.abstract.append((key, ast))

    def __repr__(self) -> str:
        rules = self.rules
        args = ", ".join([f"{tag}: {rules[tag]}" for tag in _plural_tags if tag in rules])
        return f"<{type(self).__name__} {args!r}>"

    @classmethod
    def parse(cls, rules: Mapping[str, str] | Iterable[tuple[str, str]] | PluralRule) -> PluralRule:
        """Create a `PluralRule` instance for the given rules.  If the rules
        are a `PluralRule` object, that object is returned.

        :param rules: the rules as list or dict, or a `PluralRule` object
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, PluralRule):
            return rules
        return cls(rules)

    @property
    def rules(self) -> Mapping[str, str]:
        """The `PluralRule` as a dict of unicode plural rules.

        >>> rule = PluralRule({'one': 'n is 1'})
        >>> rule.rules
        {'one': 'n is 1'}
        """
        _compile = _UnicodeCompiler().compile
        return {tag: _compile(ast) for tag, ast in self.abstract}

    @property
    def tags(self) -> frozenset[str]:
        """A set of explicitly defined tags in this rule.  The implicit default
        ``'other'`` rules is not part of this set unless there is an explicit
        rule for it.
        """
        return frozenset(i[0] for i in self.abstract)

    def __getstate__(self) -> list[tuple[str, Any]]:
        return self.abstract

    def __setstate__(self, abstract: list[tuple[str, Any]]) -> None:
        self.abstract = abstract

    def __call__(self, n: float | decimal.Decimal) -> str:
        if not hasattr(self, '_func'):
            self._func = to_python(self)
        return self._func(n)


def to_javascript(rule: Mapping[str, str] | Iterable[tuple[str, str]] | PluralRule) -> str:
    """Convert a list/dict of rules or a `PluralRule` object into a JavaScript
    function.  This function depends on no external library:

    >>> to_javascript({'one': 'n is 1'})
    "(function(n) { return (n == 1) ? 'one' : 'other'; })"

    Implementation detail: The function generated will probably evaluate
    expressions involved into range operations multiple times.  This has the
    advantage that external helper functions are not required and is not a
    big performance hit for these simple calculations.

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    to_js = _JavaScriptCompiler().compile
    result = ['(function(n) { return ']
    for tag, ast in PluralRule.parse(rule).abstract:
        result.append(f"{to_js(ast)} ? {tag!r} : ")
    result.append('%r; })' % _fallback_tag)
    return ''.join(result)


def to_python(rule: Mapping[str, str] | Iterable[tuple[str, str]] | PluralRule) -> Callable[[float | decimal.Decimal], str]:
    """Convert a list/dict of rules or a `PluralRule` object into a regular
    Python function.  This is useful in situations where you need a real
    function and don't are about the actual rule object:

    >>> func = to_python({'one': 'n is 1', 'few': 'n in 2..4'})
    >>> func(1)
    'one'
    >>> func(3)
    'few'
    >>> func = to_python({'one': 'n in 1,11', 'few': 'n in 3..10,13..19'})
    >>> func(11)
    'one'
    >>> func(15)
    'few'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    namespace = {
        'IN': in_range_list,
        'WITHIN': within_range_list,
        'MOD': cldr_modulo,
        'extract_operands': extract_operands,
    }
    to_python_func = _PythonCompiler().compile
    result = [
        'def evaluate(n):',
        ' n, i, v, w, f, t, c, e = extract_operands(n)',
    ]
    for tag, ast in PluralRule.parse(rule).abstract:
        # the str() call is to coerce the tag to the native string.  It's
        # a limited ascii restricted set of tags anyways so that is fine.
        result.append(f" if ({to_python_func(ast)}): return {str(tag)!r}")
    result.append(f" return {_fallback_tag!r}")
    code = compile('\n'.join(result), '<rule>', 'exec')
    eval(code, namespace)
    return namespace['evaluate']


def to_gettext(rule: Mapping[str, str] | Iterable[tuple[str, str]] | PluralRule) -> str:
    """The plural rule as gettext expression.  The gettext expression is
    technically limited to integers and returns indices rather than tags.

    >>> to_gettext({'one': 'n is 1', 'two': 'n is 2'})
    'nplurals=3; plural=((n == 1) ? 0 : (n == 2) ? 1 : 2);'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    rule = PluralRule.parse(rule)

    used_tags = rule.tags | {_fallback_tag}
    _compile = _GettextCompiler().compile
    _get_index = [tag for tag in _plural_tags if tag in used_tags].index

    result = [f"nplurals={len(used_tags)}; plural=("]
    for tag, ast in rule.abstract:
        result.append(f"{_compile(ast)} ? {_get_index(tag)} : ")
    result.append(f"{_get_index(_fallback_tag)});")
    return ''.join(result)


def in_range_list(num: float | decimal.Decimal, range_list: Iterable[Iterable[float | decimal.Decimal]]) -> bool:
    """Integer range list test.  This is the callback for the "in" operator
    of the UTS #35 pluralization rule language:

    >>> in_range_list(1, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3), (5, 8)])
    True
    >>> in_range_list(1.2, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4), (6, 8)])
    False
    """
    return num == int(num) and within_range_list(num, range_list)


def within_range_list(num: float | decimal.Decimal, range_list: Iterable[Iterable[float | decimal.Decimal]]) -> bool:
    """Float range test.  This is the callback for the "within" operator
    of the UTS #35 pluralization rule language:

    >>> within_range_list(1, [(1, 3)])
    True
    >>> within_range_list(1.0, [(1, 3)])
    True
    >>> within_range_list(1.2, [(1, 4)])
    True
    >>> within_range_list(8.8, [(1, 4), (7, 15)])
    True
    >>> within_range_list(10, [(1, 4)])
    False
    >>> within_range_list(10.5, [(1, 4), (20, 30)])
    False
    """
    return any(num >= min_ and num <= max_ for min_, max_ in range_list)


def cldr_modulo(a: float, b: float) -> float:
    """Javaish modulo.  This modulo operator returns the value with the sign
    of the dividend rather than the divisor like Python does:

    >>> cldr_modulo(-3, 5)
    -3
    >>> cldr_modulo(-3, -5)
    -3
    >>> cldr_modulo(3, 5)
    3
    """
    reverse = 0
    if a < 0:
        a *= -1
        reverse = 1
    if b < 0:
        b *= -1
    rv = a % b
    if reverse:
        rv *= -1
    return rv


class RuleError(Exception):
    """Raised if a rule is malformed."""


_VARS = {
    'n',  # absolute value of the source number.
    'i',  # integer digits of n.
    'v',  # number of visible fraction digits in n, with trailing zeros.*
    'w',  # number of visible fraction digits in n, without trailing zeros.*
    'f',  # visible fraction digits in n, with trailing zeros.*
    't',  # visible fraction digits in n, without trailing zeros.*
    'c',  # compact decimal exponent value: exponent of the power of 10 used in compact decimal formatting.
    'e',  # currently, synonym for `c`. however, may be redefined in the future.
}

_RULES: list[tuple[str | None, re.Pattern[str]]] = [
    (None, re.compile(r'\s+', re.UNICODE)),
    ('word', re.compile(fr'\b(and|or|is|(?:with)?in|not|mod|[{"".join(_VARS)}])\b')),
    ('value', re.compile(r'\d+')),
    ('symbol', re.compile(r'%|,|!=|=')),
    ('ellipsis', re.compile(r'\.{2,3}|\u2026', re.UNICODE)),  # U+2026: ELLIPSIS
]


def tokenize_rule(s: str) -> list[tuple[str, str]]:
    s = s.split('@')[0]
    result: list[tuple[str, str]] = []
    pos = 0
    end = len(s)
    while pos < end:
        for tok, rule in _RULES:
            match = rule.match(s, pos)
            if match is not None:
                pos = match.end()
                if tok:
                    result.append((tok, match.group()))
                break
        else:
            raise RuleError('malformed CLDR pluralization rule.  '
                            'Got unexpected %r' % s[pos])
    return result[::-1]


def test_next_token(
    tokens: list[tuple[str, str]],
    type_: str,
    value: str | None = None,
) -> list[tuple[str, str]] | bool:
    return tokens and tokens[-1][0] == type_ and \
        (value is None or tokens[-1][1] == value)


def skip_token(tokens: list[tuple[str, str]], type_: str, value: str | None = None):
    if test_next_token(tokens, type_, value):
        return tokens.pop()


def value_node(value: int) -> tuple[Literal['value'], tuple[int]]:
    return 'value', (value, )


def ident_node(name: str) -> tuple[str, tuple[()]]:
    return name, ()


def range_list_node(
    range_list: Iterable[Iterable[float | decimal.Decimal]],
) -> tuple[Literal['range_list'], Iterable[Iterable[float | decimal.Decimal]]]:
    return 'range_list', range_list


def negate(rv: tuple[Any, ...]) -> tuple[Literal['not'], tuple[tuple[Any, ...]]]:
    return 'not', (rv,)


class _Parser:
    """Internal parser.  This class can translate a single rule into an abstract
    tree of tuples. It implements the following grammar::

        condition     = and_condition ('or' and_condition)*
                        ('@integer' samples)?
                        ('@decimal' samples)?
        and_condition = relation ('and' relation)*
        relation      = is_relation | in_relation | within_relation
        is_relation   = expr 'is' ('not')? value
        in_relation   = expr (('not')? 'in' | '=' | '!=') range_list
        within_relation = expr ('not')? 'within' range_list
        expr          = operand (('mod' | '%') value)?
        operand       = 'n' | 'i' | 'f' | 't' | 'v' | 'w'
        range_list    = (range | value) (',' range_list)*
        value         = digit+
        digit         = 0|1|2|3|4|5|6|7|8|9
        range         = value'..'value
        samples       = sampleRange (',' sampleRange)* (',' ('…'|'...'))?
        sampleRange   = decimalValue '~' decimalValue
        decimalValue  = value ('.' value)?

    - Whitespace can occur between or around any of the above tokens.
    - Rules should be mutually exclusive; for a given numeric value, only one
      rule should apply (i.e. the condition should only be true for one of
      the plural rule elements).
    - The in and within relations can take comma-separated lists, such as:
      'n in 3,5,7..15'.
    - Samples are ignored.

    The translator parses the expression on instantiation into an attribute
    called `ast`.
    """

    def __init__(self, string):
        self.tokens = tokenize_rule(string)
        if not self.tokens:
            # If the pattern is only samples, it's entirely possible
            # no stream of tokens whatsoever is generated.
            self.ast = None
            return
        self.ast = self.condition()
        if self.tokens:
            raise RuleError(f"Expected end of rule, got {self.tokens[-1][1]!r}")

    def expect(self, type_, value=None, term=None):
        token = skip_token(self.tokens, type_, value)
        if token is not None:
            return token
        if term is None:
            term = repr(value is None and type_ or value)
        if not self.tokens:
            raise RuleError(f"expected {term} but end of rule reached")
        raise RuleError(f"expected {term} but got {self.tokens[-1][1]!r}")

    def condition(self):
        op = self.and_condition()
        while skip_token(self.tokens, 'word', 'or'):
            op = 'or', (op, self.and_condition())
        return op

    def and_condition(self):
        op = self.relation()
        while skip_token(self.tokens, 'word', 'and'):
            op = 'and', (op, self.relation())
        return op

    def relation(self):
        left = self.expr()
        if skip_token(self.tokens, 'word', 'is'):
            return skip_token(self.tokens, 'word', 'not') and 'isnot' or 'is', \
                (left, self.value())
        negated = skip_token(self.tokens, 'word', 'not')
        method = 'in'
        if skip_token(self.tokens, 'word', 'within'):
            method = 'within'
        else:
            if not skip_token(self.tokens, 'word', 'in'):
                if negated:
                    raise RuleError('Cannot negate operator based rules.')
                return self.newfangled_relation(left)
        rv = 'relation', (method, left, self.range_list())
        return negate(rv) if negated else rv

    def newfangled_relation(self, left):
        if skip_token(self.tokens, 'symbol', '='):
            negated = False
        elif skip_token(self.tokens, 'symbol', '!='):
            negated = True
        else:
            raise RuleError('Expected "=" or "!=" or legacy relation')
        rv = 'relation', ('in', left, self.range_list())
        return negate(rv) if negated else rv

    def range_or_value(self):
        left = self.value()
        if skip_token(self.tokens, 'ellipsis'):
            return left, self.value()
        else:
            return left, left

    def range_list(self):
        range_list = [self.range_or_value()]
        while skip_token(self.tokens, 'symbol', ','):
            range_list.append(self.range_or_value())
        return range_list_node(range_list)

    def expr(self):
        word = skip_token(self.tokens, 'word')
        if word is None or word[1] not in _VARS:
            raise RuleError('Expected identifier variable')
        name = word[1]
        if skip_token(self.tokens, 'word', 'mod'):
            return 'mod', ((name, ()), self.value())
        elif skip_token(self.tokens, 'symbol', '%'):
            return 'mod', ((name, ()), self.value())
        return ident_node(name)

    def value(self):
        return value_node(int(self.expect('value')[1]))


def _binary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, left, right: tmpl % (self.compile(left), self.compile(right))


def _unary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, x: tmpl % self.compile(x)


compile_zero = lambda x: '0'


class _Compiler:
    """The compilers are able to transform the expressions into multiple
    output formats.
    """

    def compile(self, arg):
        op, args = arg
        return getattr(self, f"compile_{op}")(*args)

    compile_n = lambda x: 'n'
    compile_i = lambda x: 'i'
    compile_v = lambda x: 'v'
    compile_w = lambda x: 'w'
    compile_f = lambda x: 'f'
    compile_t = lambda x: 't'
    compile_c = lambda x: 'c'
    compile_e = lambda x: 'e'
    compile_value = lambda x, v: str(v)
    compile_and = _binary_compiler('(%s && %s)')
    compile_or = _binary_compiler('(%s || %s)')
    compile_not = _unary_compiler('(!%s)')
    compile_mod = _binary_compiler('(%s %% %s)')
    compile_is = _binary_compiler('(%s == %s)')
    compile_isnot = _binary_compiler('(%s != %s)')

    def compile_relation(self, method, expr, range_list):
        raise NotImplementedError()


class _PythonCompiler(_Compiler):
    """Compiles an expression to Python."""

    compile_and = _binary_compiler('(%s and %s)')
    compile_or = _binary_compiler('(%s or %s)')
    compile_not = _unary_compiler('(not %s)')
    compile_mod = _binary_compiler('MOD(%s, %s)')

    def compile_relation(self, method, expr, range_list):
        ranges = ",".join([f"({self.compile(a)}, {self.compile(b)})" for (a, b) in range_list[1]])
        return f"{method.upper()}({self.compile(expr)}, [{ranges}])"


class _GettextCompiler(_Compiler):
    """Compile into a gettext plural expression."""

    compile_i = _Compiler.compile_n
    compile_v = compile_zero
    compile_w = compile_zero
    compile_f = compile_zero
    compile_t = compile_zero

    def compile_relation(self, method, expr, range_list):
        rv = []
        expr = self.compile(expr)
        for item in range_list[1]:
            if item[0] == item[1]:
                rv.append(f"({expr} == {self.compile(item[0])})")
            else:
                min, max = map(self.compile, item)
                rv.append(f"({expr} >= {min} && {expr} <= {max})")
        return f"({' || '.join(rv)})"


class _JavaScriptCompiler(_GettextCompiler):
    """Compiles the expression to plain of JavaScript."""

    # XXX: presently javascript does not support any of the
    # fraction support and basically only deals with integers.
    compile_i = lambda x: 'parseInt(n, 10)'
    compile_v = compile_zero
    compile_w = compile_zero
    compile_f = compile_zero
    compile_t = compile_zero

    def compile_relation(self, method, expr, range_list):
        code = _GettextCompiler.compile_relation(
            self, method, expr, range_list)
        if method == 'in':
            expr = self.compile(expr)
            code = f"(parseInt({expr}, 10) == {expr} && {code})"
        return code


class _UnicodeCompiler(_Compiler):
    """Returns a unicode pluralization rule again."""

    # XXX: this currently spits out the old syntax instead of the new
    # one.  We can change that, but it will break a whole bunch of stuff
    # for users I suppose.

    compile_is = _binary_compiler('%s is %s')
    compile_isnot = _binary_compiler('%s is not %s')
    compile_and = _binary_compiler('%s and %s')
    compile_or = _binary_compiler('%s or %s')
    compile_mod = _binary_compiler('%s mod %s')

    def compile_not(self, relation):
        return self.compile_relation(*relation[1], negated=True)

    def compile_relation(self, method, expr, range_list, negated=False):
        ranges = []
        for item in range_list[1]:
            if item[0] == item[1]:
                ranges.append(self.compile(item[0]))
            else:
                ranges.append(f"{self.compile(item[0])}..{self.compile(item[1])}")
        return f"{self.compile(expr)}{' not' if negated else ''} {method} {','.join(ranges)}"
