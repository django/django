"""Tests for jslex."""

# originally from https://bitbucket.org/ned/jslex

from django.test import SimpleTestCase
from django.utils.jslex import CssLexer, JsLexer


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


class CssTokensTest(SimpleTestCase):
    LEX_CASES = [
        # Basic selectors
        ("body", ["selector body"]),
        ("h1 h2 h3", ["selector h1", "selector h2", "selector h3"]),
        ("div-class test_name", ["selector div-class", "selector test_name"]),
        # Class and ID selectors
        (".class", ["class .class"]),
        ("#id", ["id-selector #id"]),
        (".my-class #my-id", ["class .my-class", "id-selector #my-id"]),
        # Attribute selectors
        ("[type]", ["attribute [type]"]),
        ("[type='text']", ["attribute [type='text']"]),
        ("[href^='https']", ["attribute [href^='https']"]),
        # Pseudo-classes and pseudo-elements
        (":hover", ["pseudo :hover"]),
        ("::before", ["pseudo ::before"]),
        (":nth-child(2n+1)", ["pseudo :nth-child(2n+1)"]),
        # Basic rules
        (
            "body { color: red; }",
            [
                "selector body",
                "punct {",
                "property color",
                "punct :",
                "ident red",
                "punct ;",
                "punct }",
            ],
        ),
        # Properties and values
        (
            "div { margin: 10px; }",
            [
                "selector div",
                "punct {",
                "property margin",
                "punct :",
                "dimension 10px",
                "punct ;",
                "punct }",
            ],
        ),
        # Numbers and dimensions
        (
            "div { width: 100px; height: 50%; opacity: 0.5; }",
            [
                "selector div",
                "punct {",
                "property width",
                "punct :",
                "dimension 100px",
                "punct ;",
                "property height",
                "punct :",
                "percentage 50%",
                "punct ;",
                "property opacity",
                "punct :",
                "number 0.5",
                "punct ;",
                "punct }",
            ],
        ),
        # Various units
        (
            "div { font-size: 1.5em; margin: 2rem; width: 100vw; }",
            [
                "selector div",
                "punct {",
                "property font-size",
                "punct :",
                "dimension 1.5em",
                "punct ;",
                "property margin",
                "punct :",
                "dimension 2rem",
                "punct ;",
                "property width",
                "punct :",
                "dimension 100vw",
                "punct ;",
                "punct }",
            ],
        ),
        # Colors
        (
            "div { color: #fff; background: #123abc; }",
            [
                "selector div",
                "punct {",
                "property color",
                "punct :",
                "hash #fff",
                "punct ;",
                "property background",
                "punct :",
                "hash #123abc",
                "punct ;",
                "punct }",
            ],
        ),
        # Strings
        (
            "div { content: 'hello'; font-family: \"Arial\"; }",
            [
                "selector div",
                "punct {",
                "property content",
                "punct :",
                "string 'hello'",
                "punct ;",
                "property font-family",
                "punct :",
                'string "Arial"',
                "punct ;",
                "punct }",
            ],
        ),
        # URLs
        (
            "div { background: url('image.jpg'); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "url url('image.jpg')",
                "punct ;",
                "punct }",
            ],
        ),
        (
            "div { background: url(image.png); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "url url(image.png)",
                "punct ;",
                "punct }",
            ],
        ),
        # Functions
        (
            "div { transform: rotate(45deg); }",
            [
                "selector div",
                "punct {",
                "property transform",
                "punct :",
                "function rotate(",
                "dimension 45deg",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        (
            "div { color: rgb(255, 0, 128); }",
            [
                "selector div",
                "punct {",
                "property color",
                "punct :",
                "function rgb(",
                "number 255",
                "punct ,",
                "number 0",
                "punct ,",
                "number 128",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        # Multiple values
        (
            "div { margin: 10px 20px; }",
            [
                "selector div",
                "punct {",
                "property margin",
                "punct :",
                "dimension 10px",
                "dimension 20px",
                "punct ;",
                "punct }",
            ],
        ),
        # Font shorthand with slash
        (
            "h1 { font: bold 2em/1.5 Arial; }",
            [
                "selector h1",
                "punct {",
                "property font",
                "punct :",
                "ident bold",
                "dimension 2em",
                "punct /",
                "number 1.5",
                "ident Arial",
                "punct ;",
                "punct }",
            ],
        ),
        # Important
        (
            "div { color: red !important; }",
            [
                "selector div",
                "punct {",
                "property color",
                "punct :",
                "ident red",
                "important !important",
                "punct ;",
                "punct }",
            ],
        ),
        # Comments
        ("/* comment */", ["comment /* comment */"]),
        (
            "div { /* comment */ color: red; }",
            [
                "selector div",
                "punct {",
                "comment /* comment */",
                "property color",
                "punct :",
                "ident red",
                "punct ;",
                "punct }",
            ],
        ),
        # Multiline comments
        ("/*\n * Header\n */", ["comment /*\n * Header\n */"]),
        # At-rules
        (
            "@import url('style.css');",
            ["at-rule @import", "url url('style.css')", "punct ;"],
        ),
        (
            "@media screen { body { color: black; } }",
            [
                "at-rule @media",
                "ident screen",
                "punct {",
                "selector body",
                "punct {",
                "property color",
                "punct :",
                "ident black",
                "punct ;",
                "punct }",
                "punct }",
            ],
        ),
        # Complex selectors
        (
            "div > p + span",
            ["selector div", "punct >", "selector p", "punct +", "selector span"],
        ),
        (
            "div.class#id[type='text']:hover",
            [
                "selector div",
                "class .class",
                "id-selector #id",
                "attribute [type='text']",
                "pseudo :hover",
            ],
        ),
        # Font-face
        (
            "@font-face { font-family: 'MyFont'; src: url('font.woff'); }",
            [
                "at-rule @font-face",
                "punct {",
                "property font-family",
                "punct :",
                "string 'MyFont'",
                "punct ;",
                "property src",
                "punct :",
                "url url('font.woff')",
                "punct ;",
                "punct }",
            ],
        ),
        # Complex function calls
        (
            "div { background: linear-gradient(to right, red, blue); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "function linear-gradient(",
                "ident to",
                "ident right",
                "punct ,",
                "ident red",
                "punct ,",
                "ident blue",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        # URLs with comments (unquoted)
        (
            "div { background: url(/*comment*/image.png); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "url url(/*comment*/image.png)",
                "punct ;",
                "punct }",
            ],
        ),
        # URLs with comments in quotes (literal)
        (
            "div { background: url('/*comment*/image.png'); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "url url('/*comment*/image.png')",
                "punct ;",
                "punct }",
            ],
        ),
        # Empty URL
        (
            "div { background: url(); }",
            [
                "selector div",
                "punct {",
                "property background",
                "punct :",
                "url url()",
                "punct ;",
                "punct }",
            ],
        ),
        # Calc function
        (
            "div { width: calc(100% - 20px); }",
            [
                "selector div",
                "punct {",
                "property width",
                "punct :",
                "function calc(",
                "percentage 100%",
                "ident -",
                "dimension 20px",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
        # Custom properties (CSS variables)
        (
            "div { --main-color: #333; color: var(--main-color); }",
            [
                "selector div",
                "punct {",
                "property --main-color",
                "punct :",
                "hash #333",
                "punct ;",
                "property color",
                "punct :",
                "function var(",
                "ident --main-color",
                "punct )",
                "punct ;",
                "punct }",
            ],
        ),
    ]

    def make_function(input_css, expected_toks):
        def test_func(self):
            lexer = CssLexer()
            result = [
                "%s %s" % (name, tok)
                for name, tok, _ in lexer.lex(input_css)
                if name != "ws"
            ]
            self.assertEqual(result, expected_toks)

        return test_func

    # Generate test methods
    for i, (input_css, expected_toks) in enumerate(LEX_CASES):
        locals()[f"test_case_{i}"] = make_function(input_css, expected_toks)
