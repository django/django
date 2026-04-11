# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006 Python Software Foundation.
# All rights reserved.

# mypy: allow-untyped-defs, allow-untyped-calls

"""Tokenization help for Python programs.

generate_tokens(readline) is a generator that breaks a stream of
text into Python tokens.  It accepts a readline-like method which is called
repeatedly to get the next line of input (or "" for EOF).  It generates
5-tuples with these members:

    the token type (see token.py)
    the token (a string)
    the starting (row, column) indices of the token (a 2-tuple of ints)
    the ending (row, column) indices of the token (a 2-tuple of ints)
    the original line (string)

It is designed to match the working of the Python tokenizer exactly, except
that it produces COMMENT tokens for comments and gives type OP for all
operators

Older entry points
    tokenize_loop(readline, tokeneater)
    tokenize(readline, tokeneater=printtoken)
are the same, except instead of generating tokens, tokeneater is a callback
function to which the 5 fields described above are passed as 5 arguments,
each time a new token is found."""

import sys
from collections.abc import Iterator

from blib2to3.pgen2.grammar import Grammar
from blib2to3.pgen2.token import (
    ASYNC,
    AWAIT,
    COMMENT,
    DEDENT,
    ENDMARKER,
    FSTRING_END,
    FSTRING_MIDDLE,
    FSTRING_START,
    INDENT,
    NAME,
    NEWLINE,
    NL,
    NUMBER,
    OP,
    STRING,
    TSTRING_END,
    TSTRING_MIDDLE,
    TSTRING_START,
    tok_name,
)

__author__ = "Ka-Ping Yee <ping@lfw.org>"
__credits__ = "GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, Skip Montanaro"

import pytokens
from pytokens import TokenType

from . import token as _token

__all__ = [x for x in dir(_token) if x[0] != "_"] + [
    "tokenize",
    "generate_tokens",
    "untokenize",
]
del _token

Coord = tuple[int, int]
TokenInfo = tuple[int, str, Coord, Coord, str]

TOKEN_TYPE_MAP = {
    TokenType.indent: INDENT,
    TokenType.dedent: DEDENT,
    TokenType.newline: NEWLINE,
    TokenType.nl: NL,
    TokenType.comment: COMMENT,
    TokenType.semicolon: OP,
    TokenType.lparen: OP,
    TokenType.rparen: OP,
    TokenType.lbracket: OP,
    TokenType.rbracket: OP,
    TokenType.lbrace: OP,
    TokenType.rbrace: OP,
    TokenType.colon: OP,
    TokenType.op: OP,
    TokenType.identifier: NAME,
    TokenType.number: NUMBER,
    TokenType.string: STRING,
    TokenType.fstring_start: FSTRING_START,
    TokenType.fstring_middle: FSTRING_MIDDLE,
    TokenType.fstring_end: FSTRING_END,
    TokenType.tstring_start: TSTRING_START,
    TokenType.tstring_middle: TSTRING_MIDDLE,
    TokenType.tstring_end: TSTRING_END,
    TokenType.endmarker: ENDMARKER,
}


class TokenError(Exception): ...


def transform_whitespace(
    token: pytokens.Token, source: str, prev_token: pytokens.Token | None
) -> pytokens.Token:
    r"""
    Black treats `\\\n` at the end of a line as a 'NL' token, while it
    is ignored as whitespace in the regular Python parser.
    But, only the first one. If there's a `\\\n` following it
    (as in, a \ just by itself on a line), that is not made into NL.
    """
    if (
        token.type == TokenType.whitespace
        and prev_token is not None
        and prev_token.type not in (TokenType.nl, TokenType.newline)
    ):
        token_str = source[token.start_index : token.end_index]
        if token_str.startswith("\\\r\n"):
            return pytokens.Token(
                TokenType.nl,
                token.start_index,
                token.start_index + 3,
                token.start_line,
                token.start_col,
                token.start_line,
                token.start_col + 3,
            )
        elif token_str.startswith("\\\n") or token_str.startswith("\\\r"):
            return pytokens.Token(
                TokenType.nl,
                token.start_index,
                token.start_index + 2,
                token.start_line,
                token.start_col,
                token.start_line,
                token.start_col + 2,
            )

    return token


def tokenize(source: str, grammar: Grammar | None = None) -> Iterator[TokenInfo]:
    lines = source.split("\n")
    lines += [""]  # For newline tokens in files that don't end in a newline
    line, column = 1, 0

    prev_token: pytokens.Token | None = None
    try:
        for token in pytokens.tokenize(source):
            token = transform_whitespace(token, source, prev_token)

            line, column = token.start_line, token.start_col
            if token.type == TokenType.whitespace:
                continue

            token_str = source[token.start_index : token.end_index]

            if token.type == TokenType.newline and token_str == "":
                # Black doesn't yield empty newline tokens at the end of a file
                # if there's no newline at the end of a file.
                prev_token = token
                continue

            source_line = lines[token.start_line - 1]

            if token.type == TokenType.identifier and token_str in ("async", "await"):
                # Black uses `async` and `await` token types just for those two keywords
                yield (
                    ASYNC if token_str == "async" else AWAIT,
                    token_str,
                    (token.start_line, token.start_col),
                    (token.end_line, token.end_col),
                    source_line,
                )
            elif token.type == TokenType.op and token_str == "...":
                # Black doesn't have an ellipsis token yet, yield 3 DOTs instead
                assert token.start_line == token.end_line
                assert token.end_col == token.start_col + 3

                token_str = "."
                for start_col in range(token.start_col, token.start_col + 3):
                    end_col = start_col + 1
                    yield (
                        TOKEN_TYPE_MAP[token.type],
                        token_str,
                        (token.start_line, start_col),
                        (token.end_line, end_col),
                        source_line,
                    )
            else:
                token_type = TOKEN_TYPE_MAP.get(token.type)
                if token_type is None:
                    raise ValueError(f"Unknown token type: {token.type!r}")
                yield (
                    TOKEN_TYPE_MAP[token.type],
                    token_str,
                    (token.start_line, token.start_col),
                    (token.end_line, token.end_col),
                    source_line,
                )
            prev_token = token

    except pytokens.UnexpectedEOF:
        raise TokenError("Unexpected EOF in multi-line statement", (line, column))
    except pytokens.TokenizeError as exc:
        raise TokenError(f"Failed to parse: {type(exc).__name__}", (line, column))


def printtoken(
    type: int, token: str, srow_col: Coord, erow_col: Coord, line: str
) -> None:  # for testing
    srow, scol = srow_col
    erow, ecol = erow_col
    print(f"{srow},{scol}-{erow},{ecol}:\t{tok_name[type]}\t{token!r}")


if __name__ == "__main__":  # testing
    if len(sys.argv) > 1:
        token_iterator = tokenize(open(sys.argv[1]).read())
    else:
        token_iterator = tokenize(sys.stdin.read())

    for tok in token_iterator:
        printtoken(*tok)
