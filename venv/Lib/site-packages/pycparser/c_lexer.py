# ------------------------------------------------------------------------------
# pycparser: c_lexer.py
#
# CLexer class: lexer for the C language
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# ------------------------------------------------------------------------------
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


@dataclass(slots=True)
class _Token:
    type: str
    value: str
    lineno: int
    column: int


class CLexer:
    """A standalone lexer for C.

    Parameters for construction:
        error_func:
            Called with (msg, line, column) on lexing errors.
        on_lbrace_func:
            Called when an LBRACE token is produced (used for scope tracking).
        on_rbrace_func:
            Called when an RBRACE token is produced (used for scope tracking).
        type_lookup_func:
            Called with an identifier name; expected to return True if it is
            a typedef name and should be tokenized as TYPEID.

    Call input(text) to initialize lexing, and then keep calling token() to
    get the next token, until it returns None (at end of input).
    """

    def __init__(
        self,
        error_func: Callable[[str, int, int], None],
        on_lbrace_func: Callable[[], None],
        on_rbrace_func: Callable[[], None],
        type_lookup_func: Callable[[str], bool],
    ) -> None:
        self.error_func = error_func
        self.on_lbrace_func = on_lbrace_func
        self.on_rbrace_func = on_rbrace_func
        self.type_lookup_func = type_lookup_func
        self._init_state()

    def input(self, text: str, filename: str = "") -> None:
        """Initialize the lexer to the given input text.

        filename is an optional name identifying the file from which the input
        comes. The lexer can modify it if #line directives are encountered.
        """
        self._init_state()
        self._lexdata = text
        self._filename = filename

    def _init_state(self) -> None:
        self._lexdata = ""
        self._filename = ""
        self._pos = 0
        self._line_start = 0
        self._pending_tok: Optional[_Token] = None
        self._lineno = 1

    @property
    def filename(self) -> str:
        return self._filename

    def token(self) -> Optional[_Token]:
        # Lexing strategy overview:
        #
        # - We maintain a current position (self._pos), line number, and the
        #   byte offset of the current line start. The lexer is a simple loop
        #   that skips whitespace/newlines and emits one token per call.
        # - A small amount of logic is handled manually before regex matching:
        #
        #   * Preprocessor-style directives: if we see '#', we check whether
        #     it's a #line or #pragma directive and consume it inline. #line
        #     updates lineno/filename and produces no tokens. #pragma can yield
        #     both PPPRAGMA and PPPRAGMASTR, but token() returns a single token,
        #     so we stash the PPPRAGMASTR as _pending_tok to return on the next
        #     token() call. Otherwise we return PPHASH.
        #   * Newlines update lineno/line-start tracking so tokens can record
        #     accurate columns.
        #
        # - The bulk of tokens are recognized in _match_token:
        #
        #   * _regex_rules: regex patterns for identifiers, literals, and other
        #     complex tokens (including error-producing patterns). The lexer
        #     uses a combined _regex_master to scan options at the same time.
        #   * _fixed_tokens: exact string matches for operators and punctuation,
        #     resolved by longest match.
        #
        # - Error patterns call the error callback and advance minimally, which
        #   keeps lexing resilient while reporting useful diagnostics.
        text = self._lexdata
        n = len(text)

        if self._pending_tok is not None:
            tok = self._pending_tok
            self._pending_tok = None
            return tok

        while self._pos < n:
            match text[self._pos]:
                case " " | "\t":
                    self._pos += 1
                case "\n":
                    self._lineno += 1
                    self._pos += 1
                    self._line_start = self._pos
                case "#":
                    if _line_pattern.match(text, self._pos + 1):
                        self._pos += 1
                        self._handle_ppline()
                        continue
                    if _pragma_pattern.match(text, self._pos + 1):
                        self._pos += 1
                        toks = self._handle_pppragma()
                        if len(toks) > 1:
                            self._pending_tok = toks[1]
                        if len(toks) > 0:
                            return toks[0]
                        continue
                    tok = self._make_token("PPHASH", "#", self._pos)
                    self._pos += 1
                    return tok
                case _:
                    if tok := self._match_token():
                        return tok
                    else:
                        continue

    def _match_token(self) -> Optional[_Token]:
        """Match one token at the current position.

        Returns a Token on success, or None if no token could be matched and
        an error was reported. This method always advances _pos by the matched
        length, or by 1 on error/no-match.
        """
        text = self._lexdata
        pos = self._pos
        # We pick the longest match between:
        # - the master regex (identifiers, literals, error patterns, etc.)
        # - fixed operator/punctuator literals from the bucket for text[pos]
        #
        # The longest match is required to ensure we properly lex something
        # like ".123" (a floating-point constant) as a single entity (with
        # FLOAT_CONST), rather than a PERIOD followed by a number.
        #
        # The fixed-literal buckets are already length-sorted, so within that
        # bucket we can take the first match. However, we still compare its
        # length to the regex match because the regex may have matched a longer
        # token that should take precedence.
        best = None

        if m := _regex_master.match(text, pos):
            tok_type = m.lastgroup
            # All master-regex alternatives are named; lastgroup shouldn't be None.
            assert tok_type is not None
            value = m.group(tok_type)
            length = len(value)
            action, msg = _regex_actions[tok_type]
            best = (length, tok_type, value, action, msg)

        if bucket := _fixed_tokens_by_first.get(text[pos]):
            for entry in bucket:
                if text.startswith(entry.literal, pos):
                    length = len(entry.literal)
                    if best is None or length > best[0]:
                        best = (
                            length,
                            entry.tok_type,
                            entry.literal,
                            _RegexAction.TOKEN,
                            None,
                        )
                    break

        if best is None:
            msg = f"Illegal character {repr(text[pos])}"
            self._error(msg, pos)
            self._pos += 1
            return None

        length, tok_type, value, action, msg = best
        if action == _RegexAction.ERROR:
            if tok_type == "BAD_CHAR_CONST":
                msg = f"Invalid char constant {value}"
            # All other ERROR rules provide a message.
            assert msg is not None
            self._error(msg, pos)
            self._pos += max(1, length)
            return None

        if action == _RegexAction.ID:
            tok_type = _keyword_map.get(value, "ID")
            if tok_type == "ID" and self.type_lookup_func(value):
                tok_type = "TYPEID"

        tok = self._make_token(tok_type, value, pos)
        self._pos += length

        if tok.type == "LBRACE":
            self.on_lbrace_func()
        elif tok.type == "RBRACE":
            self.on_rbrace_func()

        return tok

    def _make_token(self, tok_type: str, value: str, pos: int) -> _Token:
        """Create a Token at an absolute input position.

        Expects tok_type/value and the absolute byte offset pos in the current
        input. Does not advance lexer state; callers manage _pos themselves.
        Returns a Token with lineno/column computed from current line tracking.
        """
        column = pos - self._line_start + 1
        tok = _Token(tok_type, value, self._lineno, column)
        return tok

    def _error(self, msg: str, pos: int) -> None:
        column = pos - self._line_start + 1
        self.error_func(msg, self._lineno, column)

    def _handle_ppline(self) -> None:
        # Since #line directives aren't supposed to return tokens but should
        # only affect the lexer's state (update line/filename for coords), this
        # method does a bit of parsing on its own. It doesn't return anything,
        # but its side effect is to update self._pos past the directive, and
        # potentially update self._lineno and self._filename, based on the
        # directive's contents.
        #
        # Accepted #line forms from preprocessors:
        # - "#line 66 \"kwas\\df.h\""
        # - "# 9"
        # - "#line 10 \"include/me.h\" 1 2 3" (extra numeric flags)
        # - "# 1 \"file.h\" 3"
        # Errors we must report:
        # - "#line \"file.h\"" (filename before line number)
        # - "#line df" (garbage instead of number/string)
        #
        # We scan the directive line once (after an optional 'line' keyword),
        # validating the order: NUMBER, optional STRING, then any NUMBERs.
        # The NUMBERs tail is only accepted if a filename STRING was present.
        text = self._lexdata
        n = len(text)
        line_end = text.find("\n", self._pos)
        if line_end == -1:
            line_end = n
        line = text[self._pos : line_end]
        pos = 0
        line_len = len(line)

        def skip_ws() -> None:
            nonlocal pos
            while pos < line_len and line[pos] in " \t":
                pos += 1

        skip_ws()
        if line.startswith("line", pos):
            pos += 4

        def success(pp_line: Optional[str], pp_filename: Optional[str]) -> None:
            if pp_line is None:
                self._error("line number missing in #line", self._pos + line_len)
            else:
                self._lineno = int(pp_line)
                if pp_filename is not None:
                    self._filename = pp_filename
            self._pos = line_end + 1
            self._line_start = self._pos

        def fail(msg: str, offset: int) -> None:
            self._error(msg, self._pos + offset)
            self._pos = line_end + 1
            self._line_start = self._pos

        skip_ws()
        if pos >= line_len:
            success(None, None)
            return
        if line[pos] == '"':
            fail("filename before line number in #line", pos)
            return

        m = re.match(_decimal_constant, line[pos:])
        if not m:
            fail("invalid #line directive", pos)
            return

        pp_line = m.group(0)
        pos += len(pp_line)
        skip_ws()
        if pos >= line_len:
            success(pp_line, None)
            return

        if line[pos] != '"':
            fail("invalid #line directive", pos)
            return

        m = re.match(_string_literal, line[pos:])
        if not m:
            fail("invalid #line directive", pos)
            return

        pp_filename = m.group(0).lstrip('"').rstrip('"')
        pos += len(m.group(0))

        # Consume arbitrary sequence of numeric flags after the directive
        while True:
            skip_ws()
            if pos >= line_len:
                break
            m = re.match(_decimal_constant, line[pos:])
            if not m:
                fail("invalid #line directive", pos)
                return
            pos += len(m.group(0))

        success(pp_line, pp_filename)

    def _handle_pppragma(self) -> List[_Token]:
        # Parse a full #pragma line; returns a list of tokens with 1 or 2
        # tokens - PPPRAGMA and an optional PPPRAGMASTR. If an empty list is
        # returned, it means an error occurred, or we're at the end of input.
        #
        # Examples:
        # - "#pragma" -> PPPRAGMA only
        # - "#pragma once" -> PPPRAGMA, PPPRAGMASTR("once")
        # - "# pragma omp parallel private(th_id)" -> PPPRAGMA, PPPRAGMASTR("omp parallel private(th_id)")
        # - "#\tpragma {pack: 2, smack: 3}" -> PPPRAGMA, PPPRAGMASTR("{pack: 2, smack: 3}")
        text = self._lexdata
        n = len(text)
        pos = self._pos

        while pos < n and text[pos] in " \t":
            pos += 1
        if pos >= n:
            self._pos = pos
            return []

        if not text.startswith("pragma", pos):
            self._error("invalid #pragma directive", pos)
            self._pos = pos + 1
            return []

        pragma_pos = pos
        pos += len("pragma")
        toks = [self._make_token("PPPRAGMA", "pragma", pragma_pos)]

        while pos < n and text[pos] in " \t":
            pos += 1

        start = pos
        while pos < n and text[pos] != "\n":
            pos += 1
        if pos > start:
            toks.append(self._make_token("PPPRAGMASTR", text[start:pos], start))
        if pos < n and text[pos] == "\n":
            self._lineno += 1
            pos += 1
            self._line_start = pos
        self._pos = pos
        return toks


##
## Reserved keywords
##
_keywords: Tuple[str, ...] = (
    "AUTO",
    "BREAK",
    "CASE",
    "CHAR",
    "CONST",
    "CONTINUE",
    "DEFAULT",
    "DO",
    "DOUBLE",
    "ELSE",
    "ENUM",
    "EXTERN",
    "FLOAT",
    "FOR",
    "GOTO",
    "IF",
    "INLINE",
    "INT",
    "LONG",
    "REGISTER",
    "OFFSETOF",
    "RESTRICT",
    "RETURN",
    "SHORT",
    "SIGNED",
    "SIZEOF",
    "STATIC",
    "STRUCT",
    "SWITCH",
    "TYPEDEF",
    "UNION",
    "UNSIGNED",
    "VOID",
    "VOLATILE",
    "WHILE",
    "__INT128",
    "_BOOL",
    "_COMPLEX",
    "_NORETURN",
    "_THREAD_LOCAL",
    "_STATIC_ASSERT",
    "_ATOMIC",
    "_ALIGNOF",
    "_ALIGNAS",
    "_PRAGMA",
)

_keyword_map: Dict[str, str] = {}

for keyword in _keywords:
    # Keywords from new C standard are mixed-case, like _Bool, _Alignas, etc.
    if keyword.startswith("_") and len(keyword) > 1 and keyword[1].isalpha():
        _keyword_map[keyword[:2].upper() + keyword[2:].lower()] = keyword
    else:
        _keyword_map[keyword.lower()] = keyword

##
## Regexes for use in tokens
##

# valid C identifiers (K&R2: A.2.3), plus '$' (supported by some compilers)
_identifier = r"[a-zA-Z_$][0-9a-zA-Z_$]*"

_hex_prefix = "0[xX]"
_hex_digits = "[0-9a-fA-F]+"
_bin_prefix = "0[bB]"
_bin_digits = "[01]+"

# integer constants (K&R2: A.2.5.1)
_integer_suffix_opt = (
    r"(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?"
)
_decimal_constant = (
    "(0" + _integer_suffix_opt + ")|([1-9][0-9]*" + _integer_suffix_opt + ")"
)
_octal_constant = "0[0-7]*" + _integer_suffix_opt
_hex_constant = _hex_prefix + _hex_digits + _integer_suffix_opt
_bin_constant = _bin_prefix + _bin_digits + _integer_suffix_opt

_bad_octal_constant = "0[0-7]*[89]"

# comments are not supported
_unsupported_c_style_comment = r"\/\*"
_unsupported_cxx_style_comment = r"\/\/"

# character constants (K&R2: A.2.5.2)
# Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
# directives with Windows paths as filenames (..\..\dir\file)
# For the same reason, decimal_escape allows all digit sequences. We want to
# parse all correct code, even if it means to sometimes parse incorrect
# code.
#
# The original regexes were taken verbatim from the C syntax definition,
# and were later modified to avoid worst-case exponential running time.
#
#   simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
#   decimal_escape = r"""(\d+)"""
#   hex_escape = r"""(x[0-9a-fA-F]+)"""
#   bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""
#
# The following modifications were made to avoid the ambiguity that allowed
# backtracking: (https://github.com/eliben/pycparser/issues/61)
#
# - \x was removed from simple_escape, unless it was not followed by a hex
#   digit, to avoid ambiguity with hex_escape.
# - hex_escape allows one or more hex characters, but requires that the next
#   character(if any) is not hex
# - decimal_escape allows one or more decimal characters, but requires that the
#   next character(if any) is not a decimal
# - bad_escape does not allow any decimals (8-9), to avoid conflicting with the
#   permissive decimal_escape.
#
# Without this change, python's `re` module would recursively try parsing each
# ambiguous escape sequence in multiple ways. e.g. `\123` could be parsed as
# `\1`+`23`, `\12`+`3`, and `\123`.

_simple_escape = r"""([a-wyzA-Z._~!=&\^\-\\?'"]|x(?![0-9a-fA-F]))"""
_decimal_escape = r"""(\d+)(?!\d)"""
_hex_escape = r"""(x[0-9a-fA-F]+)(?![0-9a-fA-F])"""
_bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-9])"""

_escape_sequence = (
    r"""(\\(""" + _simple_escape + "|" + _decimal_escape + "|" + _hex_escape + "))"
)

# This complicated regex with lookahead might be slow for strings, so because
# all of the valid escapes (including \x) allowed
# 0 or more non-escaped characters after the first character,
# simple_escape+decimal_escape+hex_escape got simplified to

_escape_sequence_start_in_string = r"""(\\[0-9a-zA-Z._~!=&\^\-\\?'"])"""

_cconst_char = r"""([^'\\\n]|""" + _escape_sequence + ")"
_char_const = "'" + _cconst_char + "'"
_wchar_const = "L" + _char_const
_u8char_const = "u8" + _char_const
_u16char_const = "u" + _char_const
_u32char_const = "U" + _char_const
_multicharacter_constant = "'" + _cconst_char + "{2,4}'"
_unmatched_quote = "('" + _cconst_char + "*\\n)|('" + _cconst_char + "*$)"
_bad_char_const = (
    r"""('""" + _cconst_char + """[^'\n]+')|('')|('""" + _bad_escape + r"""[^'\n]*')"""
)

# string literals (K&R2: A.2.6)
_string_char = r"""([^"\\\n]|""" + _escape_sequence_start_in_string + ")"
_string_literal = '"' + _string_char + '*"'
_wstring_literal = "L" + _string_literal
_u8string_literal = "u8" + _string_literal
_u16string_literal = "u" + _string_literal
_u32string_literal = "U" + _string_literal
_bad_string_literal = '"' + _string_char + "*" + _bad_escape + _string_char + '*"'

# floating constants (K&R2: A.2.5.3)
_exponent_part = r"""([eE][-+]?[0-9]+)"""
_fractional_constant = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
_floating_constant = (
    "(((("
    + _fractional_constant
    + ")"
    + _exponent_part
    + "?)|([0-9]+"
    + _exponent_part
    + "))[FfLl]?)"
)
_binary_exponent_part = r"""([pP][+-]?[0-9]+)"""
_hex_fractional_constant = (
    "(((" + _hex_digits + r""")?\.""" + _hex_digits + ")|(" + _hex_digits + r"""\.))"""
)
_hex_floating_constant = (
    "("
    + _hex_prefix
    + "("
    + _hex_digits
    + "|"
    + _hex_fractional_constant
    + ")"
    + _binary_exponent_part
    + "[FfLl]?)"
)


class _RegexAction(Enum):
    TOKEN = 0
    ID = 1
    ERROR = 2


@dataclass(frozen=True)
class _RegexRule:
    # tok_type: name of the token emitted for a match
    # regex_pattern: the raw regex (no anchors) to match at the current position
    # action: TOKEN for normal tokens, ID for identifiers, ERROR to report
    # error_message: message used for ERROR entries
    tok_type: str
    regex_pattern: str
    action: _RegexAction
    error_message: Optional[str]


_regex_rules: List[_RegexRule] = [
    _RegexRule(
        "UNSUPPORTED_C_STYLE_COMMENT",
        _unsupported_c_style_comment,
        _RegexAction.ERROR,
        "Comments are not supported, see https://github.com/eliben/pycparser#3using.",
    ),
    _RegexRule(
        "UNSUPPORTED_CXX_STYLE_COMMENT",
        _unsupported_cxx_style_comment,
        _RegexAction.ERROR,
        "Comments are not supported, see https://github.com/eliben/pycparser#3using.",
    ),
    _RegexRule(
        "BAD_STRING_LITERAL",
        _bad_string_literal,
        _RegexAction.ERROR,
        "String contains invalid escape code",
    ),
    _RegexRule("WSTRING_LITERAL", _wstring_literal, _RegexAction.TOKEN, None),
    _RegexRule("U8STRING_LITERAL", _u8string_literal, _RegexAction.TOKEN, None),
    _RegexRule("U16STRING_LITERAL", _u16string_literal, _RegexAction.TOKEN, None),
    _RegexRule("U32STRING_LITERAL", _u32string_literal, _RegexAction.TOKEN, None),
    _RegexRule("STRING_LITERAL", _string_literal, _RegexAction.TOKEN, None),
    _RegexRule("HEX_FLOAT_CONST", _hex_floating_constant, _RegexAction.TOKEN, None),
    _RegexRule("FLOAT_CONST", _floating_constant, _RegexAction.TOKEN, None),
    _RegexRule("INT_CONST_HEX", _hex_constant, _RegexAction.TOKEN, None),
    _RegexRule("INT_CONST_BIN", _bin_constant, _RegexAction.TOKEN, None),
    _RegexRule(
        "BAD_CONST_OCT",
        _bad_octal_constant,
        _RegexAction.ERROR,
        "Invalid octal constant",
    ),
    _RegexRule("INT_CONST_OCT", _octal_constant, _RegexAction.TOKEN, None),
    _RegexRule("INT_CONST_DEC", _decimal_constant, _RegexAction.TOKEN, None),
    _RegexRule("INT_CONST_CHAR", _multicharacter_constant, _RegexAction.TOKEN, None),
    _RegexRule("CHAR_CONST", _char_const, _RegexAction.TOKEN, None),
    _RegexRule("WCHAR_CONST", _wchar_const, _RegexAction.TOKEN, None),
    _RegexRule("U8CHAR_CONST", _u8char_const, _RegexAction.TOKEN, None),
    _RegexRule("U16CHAR_CONST", _u16char_const, _RegexAction.TOKEN, None),
    _RegexRule("U32CHAR_CONST", _u32char_const, _RegexAction.TOKEN, None),
    _RegexRule("UNMATCHED_QUOTE", _unmatched_quote, _RegexAction.ERROR, "Unmatched '"),
    _RegexRule("BAD_CHAR_CONST", _bad_char_const, _RegexAction.ERROR, None),
    _RegexRule("ID", _identifier, _RegexAction.ID, None),
]

_regex_actions: Dict[str, Tuple[_RegexAction, Optional[str]]] = {}
_regex_pattern_parts: List[str] = []
for _rule in _regex_rules:
    _regex_actions[_rule.tok_type] = (_rule.action, _rule.error_message)
    _regex_pattern_parts.append(f"(?P<{_rule.tok_type}>{_rule.regex_pattern})")
# The master regex is a single alternation of all token patterns, each wrapped
# in a named group. We match once at the current position and then use
# `lastgroup` to recover which token kind fired; this avoids iterating over all
# regexes on every character while keeping the same token-level semantics.
_regex_master: re.Pattern[str] = re.compile("|".join(_regex_pattern_parts))


@dataclass(frozen=True)
class _FixedToken:
    tok_type: str
    literal: str


_fixed_tokens: List[_FixedToken] = [
    _FixedToken("ELLIPSIS", "..."),
    _FixedToken("LSHIFTEQUAL", "<<="),
    _FixedToken("RSHIFTEQUAL", ">>="),
    _FixedToken("PLUSPLUS", "++"),
    _FixedToken("MINUSMINUS", "--"),
    _FixedToken("ARROW", "->"),
    _FixedToken("LAND", "&&"),
    _FixedToken("LOR", "||"),
    _FixedToken("LSHIFT", "<<"),
    _FixedToken("RSHIFT", ">>"),
    _FixedToken("LE", "<="),
    _FixedToken("GE", ">="),
    _FixedToken("EQ", "=="),
    _FixedToken("NE", "!="),
    _FixedToken("TIMESEQUAL", "*="),
    _FixedToken("DIVEQUAL", "/="),
    _FixedToken("MODEQUAL", "%="),
    _FixedToken("PLUSEQUAL", "+="),
    _FixedToken("MINUSEQUAL", "-="),
    _FixedToken("ANDEQUAL", "&="),
    _FixedToken("OREQUAL", "|="),
    _FixedToken("XOREQUAL", "^="),
    _FixedToken("EQUALS", "="),
    _FixedToken("PLUS", "+"),
    _FixedToken("MINUS", "-"),
    _FixedToken("TIMES", "*"),
    _FixedToken("DIVIDE", "/"),
    _FixedToken("MOD", "%"),
    _FixedToken("OR", "|"),
    _FixedToken("AND", "&"),
    _FixedToken("NOT", "~"),
    _FixedToken("XOR", "^"),
    _FixedToken("LNOT", "!"),
    _FixedToken("LT", "<"),
    _FixedToken("GT", ">"),
    _FixedToken("CONDOP", "?"),
    _FixedToken("LPAREN", "("),
    _FixedToken("RPAREN", ")"),
    _FixedToken("LBRACKET", "["),
    _FixedToken("RBRACKET", "]"),
    _FixedToken("LBRACE", "{"),
    _FixedToken("RBRACE", "}"),
    _FixedToken("COMMA", ","),
    _FixedToken("PERIOD", "."),
    _FixedToken("SEMI", ";"),
    _FixedToken("COLON", ":"),
]

# To avoid scanning all fixed tokens on every character, we bucket them by the
# first character. When matching at position i, we only look at the bucket for
# text[i], and we pre-sort that bucket by token length so the first match is
# also the longest. This preserves longest-match semantics (e.g. '>>=' before
# '>>' before '>') while reducing the number of comparisons.
_fixed_tokens_by_first: Dict[str, List[_FixedToken]] = {}
for _entry in _fixed_tokens:
    _fixed_tokens_by_first.setdefault(_entry.literal[0], []).append(_entry)
for _bucket in _fixed_tokens_by_first.values():
    _bucket.sort(key=lambda item: len(item.literal), reverse=True)

_line_pattern: re.Pattern[str] = re.compile(r"([ \t]*line\W)|([ \t]*\d+)")
_pragma_pattern: re.Pattern[str] = re.compile(r"[ \t]*pragma\W")
