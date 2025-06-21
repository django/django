"""JsLex: a lexer for JavaScript"""

# originally contributed by Ned Batchelder, the author of jslex
# See https://github.com/django/django/commit/64e19ffb4ee32767861d25c874f0d2dfc75618b7
# jslex is also published at https://github.com/nedbat/jslex
import re


class Tok:
    """
    A specification for a token class.
    """

    num = 0

    def __init__(self, name, regex, next=None):
        self.id = Tok.num
        Tok.num += 1
        self.name = name
        self.regex = regex
        self.next = next


def literals(choices, prefix="", suffix=""):
    """
    Create a regex from a space-separated list of literal `choices`.

    If provided, `prefix` and `suffix` will be attached to each choice
    individually.
    """
    return "|".join(prefix + re.escape(c) + suffix for c in choices.split())


class Lexer:
    """
    A generic multi-state regex-based lexer.
    """

    def __init__(self, states, first):
        self.regexes = {}
        self.toks = {}

        for state, rules in states.items():
            parts = []
            for tok in rules:
                groupid = "t%d" % tok.id
                self.toks[groupid] = tok
                parts.append("(?P<%s>%s)" % (groupid, tok.regex))
            self.regexes[state] = re.compile("|".join(parts), re.MULTILINE | re.VERBOSE)

        self.state = first

    def lex(self, text):
        """
        Lexically analyze `text`.

        Yield tuples (`name`, `tokentext`, `position`).
        """
        end = len(text)
        state = self.state
        regexes = self.regexes
        toks = self.toks
        start = 0

        while start < end:
            for match in regexes[state].finditer(text, start):
                name = match.lastgroup
                tok = toks[name]
                toktext = match[name]
                yield (tok.name, toktext, start)
                start += len(toktext)

                if tok.next:
                    state = tok.next
                    break

        self.state = state


class JsLexer(Lexer):
    """
    A JavaScript lexer

    >>> lexer = JsLexer()
    >>> list(lexer.lex("a = 1"))
    [('id', 'a'), ('ws', ' '), ('punct', '='), ('ws', ' '), ('dnum', '1')]

    This doesn't properly handle non-ASCII characters in the JavaScript source.
    """

    # Because these tokens are matched as alternatives in a regex, longer
    # possibilities must appear in the list before shorter ones, for example,
    # '>>' before '>'.
    #
    # Note that we don't have to detect malformed JavaScript, only properly
    # lex correct JavaScript, so much of this is simplified.

    # Details of JavaScript lexical structure are taken from
    # https://www.ecma-international.org/publications-and-standards/standards/ecma-262/

    # A useful explanation of automatic semicolon insertion is at
    # http://inimino.org/~inimino/blog/javascript_semicolons

    both_before = [
        Tok("comment", r"/\*(.|\n)*?\*/"),
        Tok("linecomment", r"//.*?$"),
        Tok("ws", r"\s+"),
        Tok(
            "keyword",
            literals(
                """
                           async await break case catch class const continue debugger
                           default delete do else enum export extends
                           finally for function if import in instanceof
                           let new return static super switch this throw try typeof
                           var void while with yield
                           """,
                suffix=r"\b",
            ),
            next="reg",
        ),
        Tok("reserved", literals("null true false", suffix=r"\b"), next="div"),
        Tok(
            "id",
            r"""
                  ([a-zA-Z_$   ]|\\u[0-9a-fA-Z]{4})   # first char
                  ([a-zA-Z_$0-9]|\\u[0-9a-fA-F]{4})*  # rest chars
                  """,
            next="div",
        ),
        Tok("hbigint", r"0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*n", next="div"),
        Tok("hnum", r"0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*", next="div"),
        Tok("bbigint", r"0[bB][01]+(_[01]+)*n", next="div"),
        Tok("bnum", r"0[bB][01]+(_[01]+)*", next="div"),
        Tok("obigint", r"0[oO][0-7]+(_[0-7]+)*n", next="div"),
        Tok("onum", r"0[oO][0-7]+(_[0-7]+)*", next="div"),
        Tok("dbigint", r"(0|[1-9][0-9]*(_[0-9]+)*)n", next="div"),
        Tok("onum", r"0[0-7]+"),
        Tok(
            "dnum",
            r"""
                    (   (0|[1-9][0-9]*(_[0-9]+)*)     # DecimalIntegerLiteral
                        \.                  # dot
                        [0-9]*(_[0-9]+)*    # DecimalDigits-opt
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    |
                        \.                  # dot
                        [0-9]+(_[0-9]+)*    # DecimalDigits
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    |
                        (0|[1-9][0-9]*(_[0-9]+)*)     # DecimalIntegerLiteral
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    )
                    """,
            next="div",
        ),
        Tok(
            "punct",
            literals(
                """
                >>>= === !== >>> <<= >>= <= >= == != << >> &&= && => ?. ??= ??
                **=  ** ||= || += -= *= %= &= |= ^=
                """
            ),
            next="reg",
        ),
        Tok("punct", literals("++ -- ) ]"), next="div"),
        Tok("punct", literals("{ } ( [ . ; , < > + - * % & | ^ ! ~ ? : ="), next="reg"),
        Tok("string", r'"([^"\\]|(\\(.|\n)))*?"', next="div"),
        Tok("string", r"'([^'\\]|(\\(.|\n)))*?'", next="div"),
        Tok("string", r"`([^`\\]|(\\(.|\n))|\$\{[^}]*\})*?`", next="div"),
    ]

    both_after = [
        Tok("other", r"."),
    ]

    states = {
        # slash will mean division
        "div": both_before
        + [
            Tok("punct", literals("/= /"), next="reg"),
        ]
        + both_after,
        # slash will mean regex
        "reg": both_before
        + [
            Tok(
                "regex",
                r"""
                    /                       # opening slash
                    # First character is..
                    (   [^*\\/[]            # anything but * \ / or [
                    |   \\.                 # or an escape sequence
                    |   \[                  # or a class, which has
                            (   [^\]\\]     #   anything but \ or ]
                            |   \\.         #   or an escape sequence
                            )*              #   many times
                        \]
                    )
                    # Following characters are same, except for excluding a star
                    (   [^\\/[]             # anything but \ / or [
                    |   \\.                 # or an escape sequence
                    |   \[                  # or a class, which has
                            (   [^\]\\]     #   anything but \ or ]
                            |   \\.         #   or an escape sequence
                            )*              #   many times
                        \]
                    )*                      # many times
                    /                       # closing slash
                    [a-zA-Z0-9]*            # trailing flags
                """,
                next="div",
            ),
        ]
        + both_after,
    }

    def __init__(self):
        super().__init__(self.states, "reg")


def find_import_export_strings(file_contents):
    lexer = JsLexer()
    tokens = list(lexer.lex(file_contents))
    # remove all whitespace
    tokens = [token_tuple for token_tuple in tokens if token_tuple[0] != "ws"]

    matches = []

    def _append_match(token_tuple):
        # the lex parser returns the string, with the wrapping quotes, remove them
        matches.append((token_tuple[1][1:-1], token_tuple[2] + 1))

    for i, (name, value, _) in enumerate(tokens):
        if name == "keyword" and value == "import":
            # check for plain import and function imports first
            # import "module-name";
            if i + 1 < len(tokens) and tokens[i + 1][0] == "string":
                _append_match(tokens[i + 1])
            # import("module-name");
            elif (
                i + 2 < len(tokens)
                and tokens[i + 1][0] == "punct"
                and tokens[i + 1][1] == "("
            ):
                _append_match(tokens[i + 2])
            # or we keep going till we see from
            # import { export1 } from "module-name";
            # import { export1 as alias1 } from "module-name";
            # import { default as alias } from "module-name";
            # import { export1, export2 } from "module-name";
            # import { export1, export2 as alias2, /* … */ } from "module-name";
            # import { "string name" as alias } from "module-name";
            # import defaultExport, { export1, /* … */ } from "module-name";
            # import defaultExport, * as name from "module-name";
            else:
                for j in range(i + 1, len(tokens)):
                    if (
                        tokens[j][0] == "id"
                        and tokens[j][1] == "from"
                        and j + 1 < len(tokens)
                    ):
                        _append_match(tokens[j + 1])
                        break

        elif name == "keyword" and value == "export":
            # export is used within modules as well as aggregation
            # we need to distinguish between them by looking for the from keyword
            # also from is an id not a reserved keyword
            # case 1
            # export * from "module-name";
            # export * as name1 from "module-name";

            if i + 1 < len(tokens) and tokens[i + 1][1] == "*":
                for j in range(i + 1, len(tokens)):
                    if (
                        tokens[j][0] == "id"
                        and tokens[j][1] == "from"
                        and j + 1 < len(tokens)
                    ):
                        _append_match(tokens[j + 1])
                        break

            # export { name1, /* …, */ nameN } from "module-name";
            # export { import1 as name1, /* …, */ nameN } from "module-name";
            # export { default, /* …, */ } from "module-name";
            # export { default as name1 } from "module-name";
            # find the end of the } and check if there is a from module statement
            elif (
                i + 1 < len(tokens) and i + 1 < len(tokens) and tokens[i + 1][1] == "{"
            ):
                for j in range(i + 1, len(tokens)):
                    if (
                        tokens[j][0] == "punct"
                        and tokens[j][1] == "}"
                        and j + 2 < len(tokens)
                        and tokens[j + 1][0] == "id"
                        and tokens[j + 1][1] == "from"
                    ):
                        _append_match(tokens[j + 2])
                        break

    return matches
