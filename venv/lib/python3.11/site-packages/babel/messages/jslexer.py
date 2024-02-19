"""
    babel.messages.jslexer
    ~~~~~~~~~~~~~~~~~~~~~~

    A simple JavaScript 1.5 lexer which is used for the JavaScript
    extractor.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import re
from collections.abc import Generator
from typing import NamedTuple

operators: list[str] = sorted([
    '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
    '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=',
    '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
    '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':',
], key=len, reverse=True)

escapes: dict[str, str] = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}

name_re = re.compile(r'[\w$_][\w\d$_]*', re.UNICODE)
dotted_name_re = re.compile(r'[\w$_][\w\d$_.]*[\w\d$_.]', re.UNICODE)
division_re = re.compile(r'/=?')
regex_re = re.compile(r'/(?:[^/\\]*(?:\\.[^/\\]*)*)/[a-zA-Z]*', re.DOTALL)
line_re = re.compile(r'(\r\n|\n|\r)')
line_join_re = re.compile(r'\\' + line_re.pattern)
uni_escape_re = re.compile(r'[a-fA-F0-9]{1,4}')
hex_escape_re = re.compile(r'[a-fA-F0-9]{1,2}')


class Token(NamedTuple):
    type: str
    value: str
    lineno: int


_rules: list[tuple[str | None, re.Pattern[str]]] = [
    (None, re.compile(r'\s+', re.UNICODE)),
    (None, re.compile(r'<!--.*')),
    ('linecomment', re.compile(r'//.*')),
    ('multilinecomment', re.compile(r'/\*.*?\*/', re.UNICODE | re.DOTALL)),
    ('dotted_name', dotted_name_re),
    ('name', name_re),
    ('number', re.compile(r'''(
        (?:0|[1-9]\d*)
        (\.\d+)?
        ([eE][-+]?\d+)? |
        (0x[a-fA-F0-9]+)
    )''', re.VERBOSE)),
    ('jsx_tag', re.compile(r'(?:</?[^>\s]+|/>)', re.I)),  # May be mangled in `get_rules`
    ('operator', re.compile(r'(%s)' % '|'.join(map(re.escape, operators)))),
    ('template_string', re.compile(r'''`(?:[^`\\]*(?:\\.[^`\\]*)*)`''', re.UNICODE)),
    ('string', re.compile(r'''(
        '(?:[^'\\]*(?:\\.[^'\\]*)*)'  |
        "(?:[^"\\]*(?:\\.[^"\\]*)*)"
    )''', re.VERBOSE | re.DOTALL)),
]


def get_rules(jsx: bool, dotted: bool, template_string: bool) -> list[tuple[str | None, re.Pattern[str]]]:
    """
    Get a tokenization rule list given the passed syntax options.

    Internal to this module.
    """
    rules = []
    for token_type, rule in _rules:
        if not jsx and token_type and 'jsx' in token_type:
            continue
        if not template_string and token_type == 'template_string':
            continue
        if token_type == 'dotted_name':
            if not dotted:
                continue
            token_type = 'name'
        rules.append((token_type, rule))
    return rules


def indicates_division(token: Token) -> bool:
    """A helper function that helps the tokenizer to decide if the current
    token may be followed by a division operator.
    """
    if token.type == 'operator':
        return token.value in (')', ']', '}', '++', '--')
    return token.type in ('name', 'number', 'string', 'regexp')


def unquote_string(string: str) -> str:
    """Unquote a string with JavaScript rules.  The string has to start with
    string delimiters (``'``, ``"`` or the back-tick/grave accent (for template strings).)
    """
    assert string and string[0] == string[-1] and string[0] in '"\'`', \
        'string provided is not properly delimited'
    string = line_join_re.sub('\\1', string[1:-1])
    result: list[str] = []
    add = result.append
    pos = 0

    while True:
        # scan for the next escape
        escape_pos = string.find('\\', pos)
        if escape_pos < 0:
            break
        add(string[pos:escape_pos])

        # check which character is escaped
        next_char = string[escape_pos + 1]
        if next_char in escapes:
            add(escapes[next_char])

        # unicode escapes.  trie to consume up to four characters of
        # hexadecimal characters and try to interpret them as unicode
        # character point.  If there is no such character point, put
        # all the consumed characters into the string.
        elif next_char in 'uU':
            escaped = uni_escape_re.match(string, escape_pos + 2)
            if escaped is not None:
                escaped_value = escaped.group()
                if len(escaped_value) == 4:
                    try:
                        add(chr(int(escaped_value, 16)))
                    except ValueError:
                        pass
                    else:
                        pos = escape_pos + 6
                        continue
                add(next_char + escaped_value)
                pos = escaped.end()
                continue
            else:
                add(next_char)

        # hex escapes. conversion from 2-digits hex to char is infallible
        elif next_char in 'xX':
            escaped = hex_escape_re.match(string, escape_pos + 2)
            if escaped is not None:
                escaped_value = escaped.group()
                add(chr(int(escaped_value, 16)))
                pos = escape_pos + 2 + len(escaped_value)
                continue
            else:
                add(next_char)

        # bogus escape.  Just remove the backslash.
        else:
            add(next_char)
        pos = escape_pos + 2

    if pos < len(string):
        add(string[pos:])

    return ''.join(result)


def tokenize(source: str, jsx: bool = True, dotted: bool = True, template_string: bool = True, lineno: int = 1) -> Generator[Token, None, None]:
    """
    Tokenize JavaScript/JSX source.  Returns a generator of tokens.

    :param jsx: Enable (limited) JSX parsing.
    :param dotted: Read dotted names as single name token.
    :param template_string: Support ES6 template strings
    :param lineno: starting line number (optional)
    """
    may_divide = False
    pos = 0
    end = len(source)
    rules = get_rules(jsx=jsx, dotted=dotted, template_string=template_string)

    while pos < end:
        # handle regular rules first
        for token_type, rule in rules:  # noqa: B007
            match = rule.match(source, pos)
            if match is not None:
                break
        # if we don't have a match we don't give up yet, but check for
        # division operators or regular expression literals, based on
        # the status of `may_divide` which is determined by the last
        # processed non-whitespace token using `indicates_division`.
        else:
            if may_divide:
                match = division_re.match(source, pos)
                token_type = 'operator'
            else:
                match = regex_re.match(source, pos)
                token_type = 'regexp'
            if match is None:
                # woops. invalid syntax. jump one char ahead and try again.
                pos += 1
                continue

        token_value = match.group()
        if token_type is not None:
            token = Token(token_type, token_value, lineno)
            may_divide = indicates_division(token)
            yield token
        lineno += len(line_re.findall(token_value))
        pos = match.end()
