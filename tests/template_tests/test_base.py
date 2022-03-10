from django.template import Context, Template, Variable, VariableDoesNotExist
from django.template.base import DebugLexer, Lexer, TokenType
from django.test import SimpleTestCase
from django.utils.translation import gettext_lazy


class LexerTestMixin:
    template_string = (
        "text\n"
        "{% if test %}{{ varvalue }}{% endif %}"
        "{#comment {{not a var}} %{not a block}% #}"
        "end text"
    )
    expected_token_tuples = [
        # (token_type, contents, lineno, position)
        (TokenType.TEXT, "text\n", 1, (0, 5)),
        (TokenType.BLOCK, "if test", 2, (5, 18)),
        (TokenType.VAR, "varvalue", 2, (18, 32)),
        (TokenType.BLOCK, "endif", 2, (32, 43)),
        (TokenType.COMMENT, "comment {{not a var}} %{not a block}%", 2, (43, 85)),
        (TokenType.TEXT, "end text", 2, (85, 93)),
    ]

    def test_tokenize(self):
        tokens = self.lexer_class(self.template_string).tokenize()
        token_tuples = [
            (t.token_type, t.contents, t.lineno, t.position) for t in tokens
        ]
        self.assertEqual(token_tuples, self.make_expected())

    def make_expected(self):
        raise NotImplementedError("This method must be implemented by a subclass.")


class LexerTests(LexerTestMixin, SimpleTestCase):
    lexer_class = Lexer

    def make_expected(self):
        # The non-debug lexer does not record position.
        return [t[:-1] + (None,) for t in self.expected_token_tuples]


class DebugLexerTests(LexerTestMixin, SimpleTestCase):
    lexer_class = DebugLexer

    def make_expected(self):
        return self.expected_token_tuples


class TemplateTests(SimpleTestCase):
    def test_lazy_template_string(self):
        template_string = gettext_lazy("lazy string")
        self.assertEqual(Template(template_string).render(Context()), template_string)

    def test_repr(self):
        template = Template(
            "<html><body>\n"
            "{% if test %}<h1>{{ varvalue }}</h1>{% endif %}"
            "</body></html>"
        )
        self.assertEqual(
            repr(template),
            '<Template template_string="<html><body>{% if t...">',
        )


class VariableDoesNotExistTests(SimpleTestCase):
    def test_str(self):
        exc = VariableDoesNotExist(msg="Failed lookup in %r", params=({"foo": "bar"},))
        self.assertEqual(str(exc), "Failed lookup in {'foo': 'bar'}")


class VariableTests(SimpleTestCase):
    def test_integer_literals(self):
        self.assertEqual(
            Variable("999999999999999999999999999").literal, 999999999999999999999999999
        )

    def test_nonliterals(self):
        """Variable names that aren't resolved as literals."""
        var_names = []
        for var in ("inf", "infinity", "iNFiniTy", "nan"):
            var_names.extend((var, "-" + var, "+" + var))
        for var in var_names:
            with self.subTest(var=var):
                self.assertIsNone(Variable(var).literal)
