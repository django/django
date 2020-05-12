"""Tests for jslex."""
# originally from https://bitbucket.org/ned/jslex

from django.test import SimpleTestCase
from django.utils.jslex import JsLexer, prepare_js_for_gettext


class JsTokensTest(SimpleTestCase):
    LEX_CASES = [
        # ids
        ("a ABC $ _ a123", ["id a", "id ABC", "id $", "id _", "id a123"]),
        ("\\u1234 abc\\u0020 \\u0065_\\u0067", ["id \\u1234", "id abc\\u0020", "id \\u0065_\\u0067"]),
        # numbers
        ("123 1.234 0.123e-3 0 1E+40 1e1 .123", [
            "dnum 123", "dnum 1.234", "dnum 0.123e-3", "dnum 0", "dnum 1E+40",
            "dnum 1e1", "dnum .123",
        ]),
        ("0x1 0xabCD 0XABcd", ["hnum 0x1", "hnum 0xabCD", "hnum 0XABcd"]),
        ("010 0377 090", ["onum 010", "onum 0377", "dnum 0", "dnum 90"]),
        ("0xa123ghi", ["hnum 0xa123", "id ghi"]),
        # keywords
        ("function Function FUNCTION", ["keyword function", "id Function", "id FUNCTION"]),
        ("const constructor in inherits", ["keyword const", "id constructor", "keyword in", "id inherits"]),
        ("true true_enough", ["reserved true", "id true_enough"]),
        # strings
        (''' 'hello' "hello" ''', ["string 'hello'", 'string "hello"']),
        (r""" 'don\'t' "don\"t" '"' "'" '\'' "\"" """, [
            r"""string 'don\'t'""", r'''string "don\"t"''', r"""string '"'""",
            r'''string "'"''', r"""string '\''""", r'''string "\""'''
        ]),
        (r'"ƃuıxǝ⅂ ʇdıɹɔsɐʌɐſ\""', [r'string "ƃuıxǝ⅂ ʇdıɹɔsɐʌɐſ\""']),
        # comments
        ("a//b", ["id a", "linecomment //b"]),
        ("/****/a/=2//hello", ["comment /****/", "id a", "punct /=", "dnum 2", "linecomment //hello"]),
        ("/*\n * Header\n */\na=1;", ["comment /*\n * Header\n */", "id a", "punct =", "dnum 1", "punct ;"]),
        # punctuation
        ("a+++b", ["id a", "punct ++", "punct +", "id b"]),
        # regex
        (r"a=/a*/,1", ["id a", "punct =", "regex /a*/", "punct ,", "dnum 1"]),
        (r"a=/a*[^/]+/,1", ["id a", "punct =", "regex /a*[^/]+/", "punct ,", "dnum 1"]),
        (r"a=/a*\[^/,1", ["id a", "punct =", r"regex /a*\[^/", "punct ,", "dnum 1"]),
        (r"a=/\//,1", ["id a", "punct =", r"regex /\//", "punct ,", "dnum 1"]),

        # next two are from https://www-archive.mozilla.org/js/language/js20-2002-04/rationale/syntax.html#regular-expressions  # NOQA
        (
            """for (var x = a in foo && "</x>" || mot ? z:/x:3;x<5;y</g/i) {xyz(x++);}""",
            [
                "keyword for", "punct (", "keyword var", "id x", "punct =",
                "id a", "keyword in", "id foo", "punct &&", 'string "</x>"',
                "punct ||", "id mot", "punct ?", "id z", "punct :",
                "regex /x:3;x<5;y</g", "punct /", "id i", "punct )", "punct {",
                "id xyz", "punct (", "id x", "punct ++", "punct )", "punct ;",
                "punct }"
            ],
        ),
        (
            """for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y</g/i) {xyz(x++);}""",
            [
                "keyword for", "punct (", "keyword var", "id x", "punct =",
                "id a", "keyword in", "id foo", "punct &&", 'string "</x>"',
                "punct ||", "id mot", "punct ?", "id z", "punct /", "id x",
                "punct :", "dnum 3", "punct ;", "id x", "punct <", "dnum 5",
                "punct ;", "id y", "punct <", "regex /g/i", "punct )",
                "punct {", "id xyz", "punct (", "id x", "punct ++", "punct )",
                "punct ;", "punct }",
            ],
        ),

        # Various "illegal" regexes that are valid according to the std.
        (r"""/????/, /++++/, /[----]/ """, ["regex /????/", "punct ,", "regex /++++/", "punct ,", "regex /[----]/"]),

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
            """, # NOQA
            [
                "id rexl", "punct .", "id re", "punct =", "punct {",
                 "id NAME", "punct :", r"""regex /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/""", "punct ,",
                 "id UNQUOTED_LITERAL", "punct :", r"""regex /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
                 "punct ,",
                 "id QUOTED_LITERAL", "punct :", r"""regex /^'(?:[^']|'')*'/""", "punct ,",
                 "id NUMERIC_LITERAL", "punct :", r"""regex /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "punct ,",
                 "id SYMBOL", "punct :", r"""regex /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",  # NOQA
                 "punct }", "punct ;"
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
                "id rexl", "punct .", "id re", "punct =", "punct {",
                "id NAME", "punct :", r"""regex /^(?![0-9])(?:\w)+|^"(?:[^"]|"")+"/""", "punct ,",
                "id UNQUOTED_LITERAL", "punct :", r"""regex /^@(?:(?![0-9])(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
                "punct ,",
                "id QUOTED_LITERAL", "punct :", r"""regex /^'(?:[^']|'')*'/""", "punct ,",
                "id NUMERIC_LITERAL", "punct :", r"""regex /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "punct ,",
                "id SYMBOL", "punct :", r"""regex /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",   # NOQA
                "punct }", "punct ;",
                "id str", "punct =", """string '"'""", "punct ;",
            ],
        ),
        (r""" this._js = "e.str(\"" + this.value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"") + "\")"; """,
         ["keyword this", "punct .", "id _js", "punct =", r'''string "e.str(\""''', "punct +", "keyword this",
          "punct .", "id value", "punct .", "id replace", "punct (", r"regex /\\/g", "punct ,", r'string "\\\\"',
          "punct )",
          "punct .", "id replace", "punct (", r'regex /"/g', "punct ,", r'string "\\\""', "punct )", "punct +",
          r'string "\")"', "punct ;"]),
    ]


def make_function(input, toks):
    def test_func(self):
        lexer = JsLexer()
        result = ["%s %s" % (name, tok) for name, tok in lexer.lex(input) if name != 'ws']
        self.assertEqual(result, toks)
    return test_func


for i, (input, toks) in enumerate(JsTokensTest.LEX_CASES):
    setattr(JsTokensTest, "test_case_%d" % i, make_function(input, toks))


GETTEXT_CASES = (
    (
        r"""
            a = 1; /* /[0-9]+/ */
            b = 0x2a0b / 1; // /[0-9]+/
            c = 3;
        """,
        r"""
            a = 1; /* /[0-9]+/ */
            b = 0x2a0b / 1; // /[0-9]+/
            c = 3;
        """
    ), (
        r"""
            a = 1.234e-5;
            /*
             * /[0-9+/
             */
            b = .0123;
        """,
        r"""
            a = 1.234e-5;
            /*
             * /[0-9+/
             */
            b = .0123;
        """
    ), (
        r"""
            x = y / z;
            alert(gettext("hello"));
            x /= 3;
        """,
        r"""
            x = y / z;
            alert(gettext("hello"));
            x /= 3;
        """
    ), (
        r"""
            s = "Hello \"th/foo/ere\"";
            s = 'He\x23llo \'th/foo/ere\'';
            s = 'slash quote \", just quote "';
        """,
        r"""
            s = "Hello \"th/foo/ere\"";
            s = "He\x23llo \'th/foo/ere\'";
            s = "slash quote \", just quote \"";
        """
    ), (
        r"""
            s = "Line continuation\
            continued /hello/ still the string";/hello/;
        """,
        r"""
            s = "Line continuation\
            continued /hello/ still the string";"REGEX";
        """
    ), (
        r"""
            var regex = /pattern/;
            var regex2 = /matter/gm;
            var regex3 = /[*/]+/gm.foo("hey");
        """,
        r"""
            var regex = "REGEX";
            var regex2 = "REGEX";
            var regex3 = "REGEX".foo("hey");
        """
    ), (
        r"""
            for (var x = a in foo && "</x>" || mot ? z:/x:3;x<5;y</g/i) {xyz(x++);}
            for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y</g/i) {xyz(x++);}
        """,
        r"""
            for (var x = a in foo && "</x>" || mot ? z:"REGEX"/i) {xyz(x++);}
            for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y<"REGEX") {xyz(x++);}
        """
    ), (
        """
            \\u1234xyz = gettext('Hello there');
        """, r"""
            Uu1234xyz = gettext("Hello there");
        """
    )
)


class JsToCForGettextTest(SimpleTestCase):
    pass


def make_function(js, c):
    def test_func(self):
        self.assertEqual(prepare_js_for_gettext(js), c)
    return test_func


for i, pair in enumerate(GETTEXT_CASES):
    setattr(JsToCForGettextTest, "test_case_%d" % i, make_function(*pair))
