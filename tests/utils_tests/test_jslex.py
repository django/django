"""Tests for jslex functionality."""

from django.test import SimpleTestCase
from django.utils.jslex import (
    CssLexer,
    JsLexer,
    extract_css_urls,
    find_import_export_strings,
)


class JsTokensTest(SimpleTestCase):
    """Test the JavaScript lexer functionality."""

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
        # comments
        ("a//b", ["id a", "linecomment //b"]),
        (
            "/****/a/=2//hello",
            ["comment /****/", "id a", "punct /=", "dnum 2", "linecomment //hello"],
        ),
        # punctuation
        ("a+++b", ["id a", "punct ++", "punct +", "id b"]),
        # regex
        (r"a=/a*/,1", ["id a", "punct =", "regex /a*/", "punct ,", "dnum 1"]),
        (r"a=/a*[^/]+/,1", ["id a", "punct =", "regex /a*[^/]+/", "punct ,", "dnum 1"]),
        # Template literals
        ("`hello world`", ["string `hello world`"]),
        ("`hello ${name}!`", ["string `hello ${name}!`"]),
        # Arrow functions
        ("() => x", ["punct (", "punct )", "punct =>", "id x"]),
        ("a => a * 2", ["id a", "punct =>", "id a", "punct *", "dnum 2"]),
        # Let keyword
        ("let x = 5", ["keyword let", "id x", "punct =", "dnum 5"]),
        # Binary literals
        ("0b1010 0B1111 0b0", ["bnum 0b1010", "bnum 0B1111", "bnum 0b0"]),
        # New octal literals
        ("0o755 0O644 0o17", ["onum 0o755", "onum 0O644", "onum 0o17"]),
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
        # Exponentiation operator
        ("2 ** 3", ["dnum 2", "punct **", "dnum 3"]),
        ("x **= 2", ["id x", "punct **=", "dnum 2"]),
        # Nullish coalescing
        ("x ?? y", ["id x", "punct ??", "id y"]),
        ("x ??= y", ["id x", "punct ??=", "id y"]),
        # Optional chaining
        ("obj?.prop", ["id obj", "punct ?.", "id prop"]),
        # Logical assignment
        ("x &&= y", ["id x", "punct &&=", "id y"]),
        ("x ||= y", ["id x", "punct ||=", "id y"]),
        # Numeric separators
        ("1_000_000", ["dnum 1_000_000"]),
        ("3.14_159", ["dnum 3.14_159"]),
        ("0xFF_EC_DE_5E", ["hnum 0xFF_EC_DE_5E"]),
        # BigInt literals
        ("123n", ["dbigint 123n"]),
        ("0xFFn", ["hbigint 0xFFn"]),
        ("0b1010n", ["bbigint 0b1010n"]),
        ("0o755n", ["obigint 0o755n"]),
        # Yield keyword
        ("yield x", ["keyword yield", "id x"]),
        # Static keyword
        (
            "static method() {}",
            ["keyword static", "id method", "punct (", "punct )", "punct {", "punct }"],
        ),
    ]


def make_js_test_function(input, toks, lexer_class):
    def test_func(self):
        lexer = lexer_class()
        result = [
            "%s %s" % (name, tok) for name, tok, _ in lexer.lex(input) if name != "ws"
        ]
        self.assertEqual(result, toks)

    return test_func


for i, (input, toks) in enumerate(JsTokensTest.LEX_CASES):
    setattr(
        JsTokensTest, "test_case_%d" % i, make_js_test_function(input, toks, JsLexer)
    )


class CssTokensTest(SimpleTestCase):
    """Test the CSS lexer functionality."""

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
    ]


for i, (input, toks) in enumerate(CssTokensTest.LEX_CASES):
    setattr(
        CssTokensTest, "test_case_%d" % i, make_js_test_function(input, toks, CssLexer)
    )


class ExtractCssUrlsTest(SimpleTestCase):
    """Test the extract_css_urls function."""

    def test_url_function_quoted(self):
        """Test extraction of quoted URLs from url() functions."""
        css = "body { background: url('image.png'); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")
        self.assertEqual(urls[0][1], 24)

    def test_url_function_double_quoted(self):
        """Test extraction of double-quoted URLs from url() functions."""
        css = 'body { background: url("image.png"); }'
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")

    def test_url_function_unquoted(self):
        """Test extraction of unquoted URLs from url() functions."""
        css = "body { background: url(image.png); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")

    def test_url_function_with_comments_unquoted(self):
        """Test extraction with CSS comments in unquoted URLs."""
        css = "body { background: url(/*comment*/image.png); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")  # Comments should be stripped

    def test_url_function_with_comments_quoted(self):
        """
        Test extraction with CSS comments in quoted URLs.
        """
        css = "body { background: url('/*comment*/image.png'); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(
            urls[0][0], "/*comment*/image.png"
        )  # Comments preserved in quotes

    def test_url_function_in_comment(self):
        """Test extraction with url in CSS comments is skipped."""
        css = "/*body { background: url('image.png'); }*/"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 0)

        css = "body { background: /*url('image.png')*/ blue; }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 0)

    def test_url_function_mixed_case(self):
        """Test extraction with url is not case sensetive."""
        css = "body { background: URL('image.png'); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")

        css = "body { background: Url('image.png'); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")

    def test_import_statements(self):
        """Test extraction of URLs from @import statements."""
        css = "@import 'style.css';"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "style.css")

    def test_import_statements_double_quotes(self):
        """
        Test extraction of URLs from @import statements with double quotes.
        """
        css = '@import "style.css";'
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "style.css")

    def test_import_function_mixed_case(self):
        """
        Test extraction of URLs from @import statements is not case sensetive.
        """
        css = "@IMPORT 'style.css';"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "style.css")

        css = "@Import 'style.css';"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "style.css")

    def test_multiple_urls(self):
        """Test extraction of multiple URLs."""
        css = """
        body { background: url('bg.png'); }
        @import 'main.css';
        .icon { background: url("icon.svg"); }
        """
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 3)
        url_values = [url[0] for url in urls]
        self.assertIn("bg.png", url_values)
        self.assertIn("main.css", url_values)
        self.assertIn("icon.svg", url_values)

    def test_empty_url(self):
        """Test handling of empty URLs."""
        css = "body { background: url(); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "")

    def test_url_with_whitespace(self):
        """Test URLs with whitespace."""
        css = "body { background: url( 'image.png' ); }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][0], "image.png")

    def test_no_urls(self):
        """Test CSS with no URLs."""
        css = "body { color: red; margin: 10px; }"
        urls = extract_css_urls(css)
        self.assertEqual(len(urls), 0)


class FindImportExportStringsTest(SimpleTestCase):
    """Test the find_import_export_strings function."""

    def test_import_statement_simple(self):
        """Test simple import statement."""
        js = 'import "module.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "module.js")

    def test_import_statement_from(self):
        """Test import with from clause."""
        js = 'import { func } from "module.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "module.js")

    def test_import_statement_default(self):
        """Test default import."""
        js = 'import React from "react.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "react.js")

    def test_import_dynamic(self):
        """Test dynamic import."""
        js = 'import("module.js").then(m => m.default);'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "module.js")

    def test_export_from(self):
        """Test export from statement."""
        js = 'export { func } from "module.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "module.js")

    def test_export_star_from(self):
        """Test export * from statement."""
        js = 'export * from "module.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "module.js")

    def test_export_star_as_from(self):
        """Test export * as from statement."""
        js = 'export * as utils from "utils.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "utils.js")

    def test_multiple_imports(self):
        """Test multiple import statements."""
        js = """
        import React from "react.js";
        import { Component } from "component.js";
        import utils from "./utils.js";
        export { helper } from "./helper.js";
        """
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 4)
        import_values = [imp[0] for imp in imports]
        self.assertIn("react.js", import_values)
        self.assertIn("component.js", import_values)
        self.assertIn("./utils.js", import_values)
        self.assertIn("./helper.js", import_values)

    def test_export_without_from(self):
        """Test export without from (should not be captured)."""
        js = "export const value = 42;"
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 0)
        js = 'export const value = 42; export { helper } from "./helper.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        js = 'export { variable }; export { helper } from "./helper.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)
        js = 'export { variable }\n export { helper } from "./helper.js";'
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 1)

    def test_import_with_comments(self):
        """Test import statements with comments."""
        js = """
        // import react.js
        import React from "react.js";
        /* Multi-line comment
           import { Component } from "react.js";
        */
        import { Component } from "react.js";
        import { Component } from /* "oldreact.js" */ "react.js";
        import(/* "oldreact.js" */ "react.js")
        """
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 4)
        import_values = [imp[0] for imp in imports]
        self.assertEqual(import_values.count("react.js"), 4)

    def test_export_with_comments(self):
        """Test export statements with comments."""
        js = """
        // export * from "module.js";
        export * from "module.js";
        /* Multi-line comment
           export * from "module.js";
        */
        import { Component } from /* "oldmodule.js" */ "module.js";
        """
        exports = find_import_export_strings(js)
        self.assertEqual(len(exports), 2)
        export_values = [imp[0] for imp in exports]
        self.assertEqual(export_values.count("module.js"), 2)

    def test_no_imports(self):
        """Test JavaScript with no import/export statements."""
        js = """
        const x = 42;
        function test() {
            return x * 2;
        }
        """
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 0)

    def test_poor_syntax(self):
        """Test that poor syntax is ignored."""
        js = """
        import utils for "./utils.js";
        export *;
        """
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 0)

    def test_template_literal_with_import_like_content(self):
        """Test that template literals containing 'import' don't get parsed."""
        js = """
        const code = `import React from "react";`;
        import utils from "./utils.js";
        """
        imports = find_import_export_strings(js)
        # Should capture the actual import, not the template literal content
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][0], "./utils.js")

    def test_complex_import_patterns(self):
        """Test complex import patterns."""
        js = """
        import defaultExport, { export1, export2 } from "module.js";
        import { export1 as alias1 } from "aliased.js";
        import * as name from "namespace.js";
        import defaultExport, * as name from "mixed.js";
        """
        imports = find_import_export_strings(js)
        self.assertEqual(len(imports), 4)
        import_values = [imp[0] for imp in imports]
        self.assertIn("module.js", import_values)
        self.assertIn("aliased.js", import_values)
        self.assertIn("namespace.js", import_values)
        self.assertIn("mixed.js", import_values)
