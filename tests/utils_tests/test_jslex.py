"""Tests for jslex."""

# originally from https://bitbucket.org/ned/jslex

from django.test import SimpleTestCase
from django.utils.jslex import JsLexer


class JsTokensTest(SimpleTestCase):
    LEX_CASES = [
        # ids
        ("a ABC $ _ a123", ["id a", "id ABC", "id $", "id _", "id a123"]),
        (
            "\\u1234 abc\\u0020 \\u0065_\\u0067",
            ["id \\u1234", "id abc\\u0020", "id \\u0065_\\u0067"],
        ),
        # numbers
        (
            "123 1.234 0.123e-3 0 1E+40 1e1 .123",
            [
                "dnum 123",
                "dnum 1.234",
                "dnum 0.123e-3",
                "dnum 0",
                "dnum 1E+40",
                "dnum 1e1",
                "dnum .123",
            ],
        ),
        ("0x1 0xabCD 0XABcd", ["hnum 0x1", "hnum 0xabCD", "hnum 0XABcd"]),
        ("010 0377 090", ["onum 010", "onum 0377", "dnum 0", "dnum 90"]),
        ("0xa123ghi", ["hnum 0xa123", "id ghi"]),
        # keywords
        (
            "function Function FUNCTION",
            ["keyword function", "id Function", "id FUNCTION"],
        ),
        (
            "const constructor in inherits",
            ["keyword const", "id constructor", "keyword in", "id inherits"],
        ),
        ("true true_enough", ["reserved true", "id true_enough"]),
        # strings
        (""" 'hello' "hello" """, ["string 'hello'", 'string "hello"']),
        (
            r""" 'don\'t' "don\"t" '"' "'" '\'' "\"" """,
            [
                r"""string 'don\'t'""",
                r'''string "don\"t"''',
                r"""string '"'""",
                r'''string "'"''',
                r"""string '\''""",
                r'''string "\""''',
            ],
        ),
        (r'"ƃuıxǝ⅂ ʇdıɹɔsɐʌɐſ\""', [r'string "ƃuıxǝ⅂ ʇdıɹɔsɐʌɐſ\""']),
        # comments
        ("a//b", ["id a", "linecomment //b"]),
        (
            "/****/a/=2//hello",
            ["comment /****/", "id a", "punct /=", "dnum 2", "linecomment //hello"],
        ),
        (
            "/*\n * Header\n */\na=1;",
            ["comment /*\n * Header\n */", "id a", "punct =", "dnum 1", "punct ;"],
        ),
        # punctuation
        ("a+++b", ["id a", "punct ++", "punct +", "id b"]),
        # regex
        (r"a=/a*/,1", ["id a", "punct =", "regex /a*/", "punct ,", "dnum 1"]),
        (r"a=/a*[^/]+/,1", ["id a", "punct =", "regex /a*[^/]+/", "punct ,", "dnum 1"]),
        (r"a=/a*\[^/,1", ["id a", "punct =", r"regex /a*\[^/", "punct ,", "dnum 1"]),
        (r"a=/\//,1", ["id a", "punct =", r"regex /\//", "punct ,", "dnum 1"]),
        # next two are from https://www-archive.mozilla.org/js/language/js20-2002-04/rationale/syntax.html#regular-expressions  # NOQA
        (
            'for (var x = a in foo && "</x>" || mot ? z:/x:3;x<5;y</g/i) {xyz(x++);}',
            [
                "keyword for",
                "punct (",
                "keyword var",
                "id x",
                "punct =",
                "id a",
                "keyword in",
                "id foo",
                "punct &&",
                'string "</x>"',
                "punct ||",
                "id mot",
                "punct ?",
                "id z",
                "punct :",
                "regex /x:3;x<5;y</g",
                "punct /",
                "id i",
                "punct )",
                "punct {",
                "id xyz",
                "punct (",
                "id x",
                "punct ++",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        (
            'for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y</g/i) {xyz(x++);}',
            [
                "keyword for",
                "punct (",
                "keyword var",
                "id x",
                "punct =",
                "id a",
                "keyword in",
                "id foo",
                "punct &&",
                'string "</x>"',
                "punct ||",
                "id mot",
                "punct ?",
                "id z",
                "punct /",
                "id x",
                "punct :",
                "dnum 3",
                "punct ;",
                "id x",
                "punct <",
                "dnum 5",
                "punct ;",
                "id y",
                "punct <",
                "regex /g/i",
                "punct )",
                "punct {",
                "id xyz",
                "punct (",
                "id x",
                "punct ++",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        # Various "illegal" regexes that are valid according to the std.
        (
            r"""/????/, /++++/, /[----]/ """,
            ["regex /????/", "punct ,", "regex /++++/", "punct ,", "regex /[----]/"],
        ),
        # Stress cases from https://stackoverflow.com/questions/5533925/what-javascript-constructs-does-jslex-incorrectly-lex/5573409#5573409  # NOQA
        (r"""/\[/""", [r"""regex /\[/"""]),
        (r"""/[i]/""", [r"""regex /[i]/"""]),
        (r"""/[\]]/""", [r"""regex /[\]]/"""]),
        (r"""/a[\]]/""", [r"""regex /a[\]]/"""]),
        (r"""/a[\]]b/""", [r"""regex /a[\]]b/"""]),
        (r"""/[\]/]/gi""", [r"""regex /[\]/]/gi"""]),
        (r"""/\[[^\]]+\]/gi""", [r"""regex /\[[^\]]+\]/gi"""]),
        (
            r"""
                rexl.re = {
                NAME: /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/,
                UNQUOTED_LITERAL: /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
                QUOTED_LITERAL: /^'(?:[^']|'')*'/,
                NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
                SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
                };
            """,  # NOQA
            [
                "id rexl",
                "punct .",
                "id re",
                "punct =",
                "punct {",
                "id NAME",
                "punct :",
                r"""regex /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/""",
                "punct ,",
                "id UNQUOTED_LITERAL",
                "punct :",
                r"""regex /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
                "punct ,",
                "id QUOTED_LITERAL",
                "punct :",
                r"""regex /^'(?:[^']|'')*'/""",
                "punct ,",
                "id NUMERIC_LITERAL",
                "punct :",
                r"""regex /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""",
                "punct ,",
                "id SYMBOL",
                "punct :",
                r"""regex /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",  # NOQA
                "punct }",
                "punct ;",
            ],
        ),
        (
            r"""
                rexl.re = {
                NAME: /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/,
                UNQUOTED_LITERAL: /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
                QUOTED_LITERAL: /^'(?:[^']|'')*'/,
                NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
                SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
                };
                str = '"';
            """,  # NOQA
            [
                "id rexl",
                "punct .",
                "id re",
                "punct =",
                "punct {",
                "id NAME",
                "punct :",
                r"""regex /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/""",
                "punct ,",
                "id UNQUOTED_LITERAL",
                "punct :",
                r"""regex /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
                "punct ,",
                "id QUOTED_LITERAL",
                "punct :",
                r"""regex /^'(?:[^']|'')*'/""",
                "punct ,",
                "id NUMERIC_LITERAL",
                "punct :",
                r"""regex /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""",
                "punct ,",
                "id SYMBOL",
                "punct :",
                r"""regex /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",  # NOQA
                "punct }",
                "punct ;",
                "id str",
                "punct =",
                """string '"'""",
                "punct ;",
            ],
        ),
        (
            r' this._js = "e.str(\"" + this.value.replace(/\\/g, "\\\\")'
            r'.replace(/"/g, "\\\"") + "\")"; ',
            [
                "keyword this",
                "punct .",
                "id _js",
                "punct =",
                r'''string "e.str(\""''',
                "punct +",
                "keyword this",
                "punct .",
                "id value",
                "punct .",
                "id replace",
                "punct (",
                r"regex /\\/g",
                "punct ,",
                r'string "\\\\"',
                "punct )",
                "punct .",
                "id replace",
                "punct (",
                r'regex /"/g',
                "punct ,",
                r'string "\\\""',
                "punct )",
                "punct +",
                r'string "\")"',
                "punct ;",
            ],
        ),
        # Template literals
        ("`hello world`", ["string `hello world`"]),
        ("`hello ${name}!`", ["string `hello ${name}!`"]),
        ("`multiline\\nstring`", ["string `multiline\\nstring`"]),
        # Arrow functions
        ("() => x", ["punct (", "punct )", "punct =>", "id x"]),
        ("a => a * 2", ["id a", "punct =>", "id a", "punct *", "dnum 2"]),
        # Let keyword
        ("let x = 5", ["keyword let", "id x", "punct =", "dnum 5"]),
        (
            "let let_var = true",
            ["keyword let", "id let_var", "punct =", "reserved true"],
        ),
        # Binary literals
        ("0b1010 0B1111 0b0", ["bnum 0b1010", "bnum 0B1111", "bnum 0b0"]),
        ("0b1010abc", ["bnum 0b1010", "id abc"]),
        # New octal literals
        ("0o755 0O644 0o17", ["onum 0o755", "onum 0O644", "onum 0o17"]),
        ("0o755abc", ["onum 0o755", "id abc"]),
        # Async/await keywords
        (
            "async function test() {}",
            [
                "keyword async",
                "keyword function",
                "id test",
                "punct (",
                "punct )",
                "punct {",
                "punct }",
            ],
        ),
        ("await promise", ["keyword await", "id promise"]),
        (
            "async () => await fetch()",
            [
                "keyword async",
                "punct (",
                "punct )",
                "punct =>",
                "keyword await",
                "id fetch",
                "punct (",
                "punct )",
            ],
        ),
        # Exponentiation operator
        ("2 ** 3", ["dnum 2", "punct **", "dnum 3"]),
        ("x **= 2", ["id x", "punct **=", "dnum 2"]),
        ("2**3**4", ["dnum 2", "punct **", "dnum 3", "punct **", "dnum 4"]),
        # Nullish coalescing
        ("x ?? y", ["id x", "punct ??", "id y"]),
        ("x ??= y", ["id x", "punct ??=", "id y"]),
        ("null ?? 'default'", ["reserved null", "punct ??", "string 'default'"]),
        # Optional chaining
        ("obj?.prop", ["id obj", "punct ?.", "id prop"]),
        (
            "obj?.method?.()",
            ["id obj", "punct ?.", "id method", "punct ?.", "punct (", "punct )"],
        ),
        ("arr?.[0]", ["id arr", "punct ?.", "punct [", "dnum 0", "punct ]"]),
        # Logical assignment
        ("x &&= y", ["id x", "punct &&=", "id y"]),
        ("x ||= y", ["id x", "punct ||=", "id y"]),
        (
            "flag &&= isValid()",
            ["id flag", "punct &&=", "id isValid", "punct (", "punct )"],
        ),
        # Numeric separators
        ("1_000_000", ["dnum 1_000_000"]),
        ("3.14_159", ["dnum 3.14_159"]),
        ("0xFF_EC_DE_5E", ["hnum 0xFF_EC_DE_5E"]),
        ("0b1010_0001", ["bnum 0b1010_0001"]),
        ("0o755_644", ["onum 0o755_644"]),
        # BigInt literals
        ("123n", ["dbigint 123n"]),
        ("0xFFn", ["hbigint 0xFFn"]),
        ("0b1010n", ["bbigint 0b1010n"]),
        ("0o755n", ["obigint 0o755n"]),
        ("1_000_000n", ["dbigint 1_000_000n"]),
        ("0xFF_EC_DE_5En", ["hbigint 0xFF_EC_DE_5En"]),
        # Yield keyword
        ("yield x", ["keyword yield", "id x"]),
        (
            "yield* generator()",
            ["keyword yield", "punct *", "id generator", "punct (", "punct )"],
        ),
        (
            "function* gen() { yield 1; }",
            [
                "keyword function",
                "punct *",
                "id gen",
                "punct (",
                "punct )",
                "punct {",
                "keyword yield",
                "dnum 1",
                "punct ;",
                "punct }",
            ],
        ),
        # Static keyword
        (
            "static method() {}",
            ["keyword static", "id method", "punct (", "punct )", "punct {", "punct }"],
        ),
        ("static prop = 5", ["keyword static", "id prop", "punct =", "dnum 5"]),
        # Complex combinations
        (
            "const fn = async (x) => await x?.result ?? 'default'",
            [
                "keyword const",
                "id fn",
                "punct =",
                "keyword async",
                "punct (",
                "id x",
                "punct )",
                "punct =>",
                "keyword await",
                "id x",
                "punct ?.",
                "id result",
                "punct ??",
                "string 'default'",
            ],
        ),
        (
            "let big = 1_000n ** 2n",
            [
                "keyword let",
                "id big",
                "punct =",
                "dbigint 1_000n",
                "punct **",
                "dbigint 2n",
            ],
        ),
        (
            "obj.prop ||= `default ${value}`",
            ["id obj", "punct .", "id prop", "punct ||=", "string `default ${value}`"],
        ),
        # Edge cases
        (
            "0b1010 + 0o755 + 0xFF",
            ["bnum 0b1010", "punct +", "onum 0o755", "punct +", "hnum 0xFF"],
        ),
        ("x?.y?.z", ["id x", "punct ?.", "id y", "punct ?.", "id z"]),
        ("a ?? b ?? c", ["id a", "punct ??", "id b", "punct ??", "id c"]),
        ("**=", ["punct **="]),
        ("?.??", ["punct ?.", "punct ??"]),
        # Regex with new flags (should still work with existing pattern)
        ("/test/gimsuy", ["regex /test/gimsuy"]),
        ("/pattern/u", ["regex /pattern/u"]),
        ("/sticky/y", ["regex /sticky/y"]),
        ("/dotall/s", ["regex /dotall/s"]),
        # Mixed old and new features
        (
            "var old = 5; let x = 0b101;",
            [
                "keyword var",
                "id old",
                "punct =",
                "dnum 5",
                "punct ;",
                "keyword let",
                "id x",
                "punct =",
                "bnum 0b101",
                "punct ;",
            ],
        ),
    ]


def make_function(input, toks):
    def test_func(self):
        lexer = JsLexer()
        result = [
            "%s %s" % (name, tok) for name, tok, _ in lexer.lex(input) if name != "ws"
        ]
        self.assertEqual(result, toks)

    return test_func


for i, (input, toks) in enumerate(JsTokensTest.LEX_CASES):
    setattr(JsTokensTest, "test_case_%d" % i, make_function(input, toks))
