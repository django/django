"""JsLex: a lexer for JavaScript"""

# Originally from https://bitbucket.org/ned/jslex
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
                           break case catch class const continue debugger
                           default delete do else enum export extends
                           finally for function if import in instanceof
                           new return super switch this throw try typeof
                           var void while with
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
        Tok("hnum", r"0[xX][0-9a-fA-F]+", next="div"),
        Tok("onum", r"0[0-7]+"),
        Tok(
            "dnum",
            r"""
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
                    """,
            next="div",
        ),
        Tok(
            "punct",
            literals(
                """
                         >>>= === !== >>> <<= >>= <= >= == != << >> &&
                         || += -= *= %= &= |= ^=
                         """
            ),
            next="reg",
        ),
        Tok("punct", literals("++ -- ) ]"), next="div"),
        Tok("punct", literals("{ } ( [ . ; , < > + - * % & | ^ ! ~ ? : ="), next="reg"),
        Tok("string", r'"([^"\\]|(\\(.|\n)))*?"', next="div"),
        Tok("string", r"'([^'\\]|(\\(.|\n)))*?'", next="div"),
        Tok("string", r"`([^'\\]|(\\(.|\n)))*?`", next="div"),
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


"""CssLex: a lexer for CSS"""


class CssLexer(Lexer):
    """
    A CSS lexer

    >>> lexer = CssLexer()
    >>> list(lexer.lex("body { color: red; }"))
    [('selector', 'body'), ('ws', ' '), ('punct', '{'), ('ws', ' '),
     ('property', 'color'), ('punct', ':'), ('ws', ' '), ('ident', 'red'),
     ('punct', ';'), ('ws', ' '), ('punct', '}')]

    This handles CSS3 syntax including modern selectors, properties, and values.
    """

    # Define common token groups that are reused across states
    COMMON_TOKENS = [
        Tok("comment", r"/\*(.|\n)*?\*/"),
        Tok("ws", r"\s+"),
        Tok("string", r'"([^"\\]|\\(.|\n))*?"'),
        Tok("string", r"'([^'\\]|\\(.|\n))*?'"),
    ]

    SELECTOR_TOKENS = [
        Tok("pseudo", r"::?[a-zA-Z-]+(\([^)]*\))?"),
        Tok("class", r"\.[a-zA-Z_-][a-zA-Z0-9_-]*"),
        Tok("id-selector", r"\#[a-zA-Z_-][a-zA-Z0-9_-]*"),
        Tok("attribute", r"\[[^\]]*\]"),
        Tok("selector", r"[a-zA-Z][a-zA-Z0-9_-]*"),
    ]

    URL_TOKEN = Tok(
        "url",
        r"""
            (?i:url)\(                 # url(
            \s*                        # optional whitespace
            (?:                        # start URL content group
                (?:                    # either:
                    "[^"]*"            # double-quoted string
                    |                  # or
                    '[^']*'            # single-quoted string
                    |                  # or
                    [^)]*              # unquoted chars
                )+                     # one or more of the above
            )                          # end URL content group
            \s*                        # optional whitespace
            \)                         # closing )
        """,
    )

    _dimensions = [
        "px",
        "em",
        "rem",
        "ex",
        "ch",
        "vw",
        "vh",
        "vmin",
        "vmax",
        "cm",
        "mm",
        "in",
        "pt",
        "pc",
        "deg",
        "rad",
        "grad",
        "turn",
        "s",
        "ms",
        "Hz",
        "kHz",
        "dpi",
        "dpcm",
        "dppx",
    ]

    DIMENSION_TOKEN = Tok(
        "dimension",
        r"-?(\d+\.?\d*|\.\d+)(" + "|".join(_dimensions) + ")",
    )

    VALUE_TOKENS = [
        Tok("important", r"!important\b"),
        URL_TOKEN,
        Tok("function", r"[a-zA-Z-]+\(", next="function-args"),
        Tok("hash", r"\#[0-9a-fA-F]{3,8}"),
        Tok("percentage", r"-?(\d+\.?\d*|\.\d+)%"),
        DIMENSION_TOKEN,
        Tok("number", r"-?(\d+\.?\d*|\.\d+)"),
        Tok("ident", r"[a-zA-Z_-][a-zA-Z0-9_-]*"),
    ]

    CATCHALL = [Tok("other", r".")]

    # Build states by combining token groups
    states = {
        "default": COMMON_TOKENS
        + [
            Tok("at-rule", r"@[a-zA-Z-]+", next="at-rule-body"),
        ]
        + SELECTOR_TOKENS
        + [
            Tok("punct", r"\{", next="rule-body"),
            Tok("punct", literals(", > + ~ *")),
            Tok("punct", r"\}"),
        ]
        + CATCHALL,
        "rule-body": COMMON_TOKENS
        + [
            # Property MUST come before selector since property has lookahead for ':'
            Tok("property", r"[a-zA-Z-]+(?=\s*:)"),
        ]
        + SELECTOR_TOKENS
        + [
            Tok("punct", r":", next="property-value"),
            Tok("punct", r"\{", next="rule-body"),  # Allow nested braces
            Tok("punct", r"\}", next="default"),
        ]
        + CATCHALL,
        "property-value": COMMON_TOKENS
        + VALUE_TOKENS
        + [
            Tok("punct", r";", next="rule-body"),
            Tok("punct", r"\}", next="default"),
            Tok("punct", literals(", /")),
        ]
        + CATCHALL,
        "function-args": COMMON_TOKENS
        + [
            Tok("percentage", r"-?(\d+\.?\d*|\.\d+)%"),
            DIMENSION_TOKEN,
            Tok("number", r"-?(\d+\.?\d*|\.\d+)"),
            Tok("ident", r"[a-zA-Z_-][a-zA-Z0-9_-]*"),
            Tok("punct", r"\)", next="property-value"),
            Tok("punct", literals(",")),
        ]
        + CATCHALL,
        "at-rule-body": COMMON_TOKENS
        + [
            URL_TOKEN,
            Tok("punct", r"\{", next="rule-body"),
            Tok("punct", r";", next="default"),
            Tok("ident", r"[a-zA-Z_-][a-zA-Z0-9_-]*"),
        ]
        + CATCHALL,
    }

    def __init__(self):
        super().__init__(self.states, "default")


def extract_css_urls(css_content):
    """
    Extract all URLs from CSS content and return their positions.

    Args:
        css_content (str): The CSS content as a string

    Returns:
        list: List of tuples (url, start_position) where url is the cleaned URL
              and start_position is the character position of the actual URL content
              in the original string
    """
    lexer = CssLexer()
    urls = []
    tokens = list(lexer.lex(css_content))

    for i, (token_name, token_text, position) in enumerate(tokens):
        if token_name == "url":
            # Extract the actual URL from the url() function
            # token_text looks like: url('image.jpg') or url(image.jpg)
            # or url("image.jpg")

            # Remove 'url(' from start and ')' from end
            url_content = token_text[4:-1].strip()

            # Calculate the position of the URL content
            # position + "url(".length + any whitespace before content
            url_start_pos = position + 4  # Skip "url("

            # Skip any whitespace after "url("
            while (
                url_start_pos < len(css_content)
                and css_content[url_start_pos].isspace()
            ):
                url_start_pos += 1

            # Remove quotes if present and adjust position accordingly
            if (url_content.startswith('"') and url_content.endswith('"')) or (
                url_content.startswith("'") and url_content.endswith("'")
            ):
                # URL is quoted - keep it as-is (comments are literal)
                clean_url = url_content[1:-1]
                url_start_pos += 1  # Skip the opening quote
            else:
                # URL is unquoted - remove CSS comments
                import re

                clean_url = re.sub(r"/\*.*?\*/", "", url_content).strip()
                # For unquoted URLs, position stays the same (no quote to skip)

            urls.append((clean_url, url_start_pos))
        elif token_name == "string" and i > 0:
            # Check if this string follows an @import
            # Look back through whitespace and comments to find @import
            j = i - 1
            while j >= 0 and tokens[j][0] in ("ws", "comment"):
                j -= 1

            if j >= 0 and tokens[j][0] == "at-rule" and tokens[j][1] == "@import":
                # This string is an @import URL
                clean_url = token_text[1:-1]  # Remove quotes
                url_start_pos = position + 1  # Position after opening quote
                urls.append((clean_url, url_start_pos))
    return urls
