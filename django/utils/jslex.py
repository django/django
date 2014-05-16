"""JsLex: a lexer for Javascript"""
# Originally from https://bitbucket.org/ned/jslex
import re


class Tok(object):
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


class Lexer(object):
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

        Yields pairs (`name`, `tokentext`).
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
                toktext = match.group(name)
                start += len(toktext)
                yield (tok.name, toktext)

                if tok.next:
                    state = tok.next
                    break

        self.state = state


class JsLexer(Lexer):
    """
    A Javascript lexer

    >>> lexer = JsLexer()
    >>> list(lexer.lex("a = 1"))
    [('id', 'a'), ('ws', ' '), ('punct', '='), ('ws', ' '), ('dnum', '1')]

    This doesn't properly handle non-ASCII characters in the Javascript source.
    """

    # Because these tokens are matched as alternatives in a regex, longer
    # possibilities must appear in the list before shorter ones, for example,
    # '>>' before '>'.
    #
    # Note that we don't have to detect malformed Javascript, only properly
    # lex correct Javascript, so much of this is simplified.

    # Details of Javascript lexical structure are taken from
    # http://www.ecma-international.org/publications/files/ECMA-ST/ECMA-262.pdf

    # A useful explanation of automatic semicolon insertion is at
    # http://inimino.org/~inimino/blog/javascript_semicolons

    both_before = [
        Tok("comment", r"/\*(.|\n)*?\*/"),
        Tok("linecomment", r"//.*?$"),
        Tok("ws", r"\s+"),
        Tok("keyword", literals("""
                           break case catch class const continue debugger
                           default delete do else enum export extends
                           finally for function if import in instanceof
                           new return super switch this throw try typeof
                           var void while with
                           """, suffix=r"\b"), next='reg'),
        Tok("reserved", literals("null true false", suffix=r"\b"), next='div'),
        Tok("id", r"""
                  ([a-zA-Z_$   ]|\\u[0-9a-fA-Z]{4})   # first char
                  ([a-zA-Z_$0-9]|\\u[0-9a-fA-F]{4})*  # rest chars
                  """, next='div'),
        Tok("hnum", r"0[xX][0-9a-fA-F]+", next='div'),
        Tok("onum", r"0[0-7]+"),
        Tok("dnum", r"""
                    (   (0|[1-9][0-9]*)     # DecimalIntegerLiteral
                        \.                  # dot
                        [0-9]*              # DecimalDigits-opt
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    |
                        \.                  # dot
                        [0-9]+              # DecimalDigits
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    |
                        (0|[1-9][0-9]*)     # DecimalIntegerLiteral
                        ([eE][-+]?[0-9]+)?  # ExponentPart-opt
                    )
                    """, next='div'),
        Tok("punct", literals("""
                         >>>= === !== >>> <<= >>= <= >= == != << >> &&
                         || += -= *= %= &= |= ^=
                         """), next="reg"),
        Tok("punct", literals("++ -- ) ]"), next='div'),
        Tok("punct", literals("{ } ( [ . ; , < > + - * % & | ^ ! ~ ? : ="), next='reg'),
        Tok("string", r'"([^"\\]|(\\(.|\n)))*?"', next='div'),
        Tok("string", r"'([^'\\]|(\\(.|\n)))*?'", next='div'),
    ]

    both_after = [
        Tok("other", r"."),
    ]

    states = {
        # slash will mean division
        'div': both_before + [
            Tok("punct", literals("/= /"), next='reg'),
        ] + both_after,

        # slash will mean regex
        'reg': both_before + [
            Tok("regex",
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
                """, next='div'),
        ] + both_after,
    }

    def __init__(self):
        super(JsLexer, self).__init__(self.states, 'reg')


def prepare_js_for_gettext(js):
    """
    Convert the Javascript source `js` into something resembling C for
    xgettext.

    What actually happens is that all the regex literals are replaced with
    "REGEX".
    """
    def escape_quotes(m):
        """Used in a regex to properly escape double quotes."""
        s = m.group(0)
        if s == '"':
            return r'\"'
        else:
            return s

    lexer = JsLexer()
    c = []
    for name, tok in lexer.lex(js):
        if name == 'regex':
            # C doesn't grok regexes, and they aren't needed for gettext,
            # so just output a string instead.
            tok = '"REGEX"'
        elif name == 'string':
            # C doesn't have single-quoted strings, so make all strings
            # double-quoted.
            if tok.startswith("'"):
                guts = re.sub(r"\\.|.", escape_quotes, tok[1:-1])
                tok = '"' + guts + '"'
        elif name == 'id':
            # C can't deal with Unicode escapes in identifiers.  We don't
            # need them for gettext anyway, so replace them with something
            # innocuous
            tok = tok.replace("\\", "U")
        c.append(tok)
    return ''.join(c)
