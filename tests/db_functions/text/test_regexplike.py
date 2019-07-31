from django.db.models import Value
from django.db.models.functions import Concat, Now, RegexpLike
from django.test import TestCase

from ..models import Article, Author


class RegexpLikeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="George R. R. Martin")
        cls.author2 = Author.objects.create(name="J. R. R. Tolkien")

    def test_null(self):
        tests = [("alias", Value(r"(R\. ){2}")), ("name", None)]
        for field, pattern in tests:
            with self.subTest(field=field, pattern=pattern):
                expression = RegexpLike(field, pattern)
                author = Author.objects.annotate(matched=expression).get(
                    pk=self.author1.pk
                )
                self.assertIsNone(author.matched)

    def test_simple(self):
        expression = RegexpLike("name", Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", True),
                ("J. R. R. Tolkien", True),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )

    def test_case_sensitive(self):
        expression = RegexpLike("name", Value(r"(r\. ){2}"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", False),
                ("J. R. R. Tolkien", False),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )

    def test_lookahead(self):
        expression = RegexpLike("name", Value(r"(R\. ){2}(?=Martin)"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", True),
                ("J. R. R. Tolkien", False),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )

    def test_lookbehind(self):
        expression = RegexpLike("name", Value(r"(?<=George )(R\. ){2}"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", True),
                ("J. R. R. Tolkien", False),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )

    def test_substitution(self):
        expression = RegexpLike("name", Value(r"(R\. )\1"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", True),
                ("J. R. R. Tolkien", True),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )

    def test_expression(self):
        expression = RegexpLike(Concat(Value("Author: "), "name"), Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(matched=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", True),
                ("J. R. R. Tolkien", True),
            ],
            transform=lambda x: (x.name, x.matched),
            ordered=False,
        )


class RegexpLikeFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Article.objects.create(
            title="Chapter One",
            text="First Line.\nSecond Line.\nThird Line.",
            written=Now(),
        )

    def test_dotall_flag(self):
        expression = RegexpLike("text", Value(r"^.*$"), flags=Value("s"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)

    def test_multiline_flag(self):
        expression = RegexpLike("text", Value(r"^.*\Z"), flags=Value("m"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)

    def test_extended_flag(self):
        pattern = Value(
            r"""
            ^[^ ]*
            \ Line\.
            """
        )
        expression = RegexpLike("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)

    def test_extended_flag_with_comments(self):
        pattern = Value(
            r"""
            ^[^ ]*    # Match word at beginning of line.
            \ Line\.  # Another part of the pattern...
            """
        )
        expression = RegexpLike("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)

    def test_case_sensitive_flag(self):
        expression = RegexpLike("title", Value(r"chapter"), flags=Value("c"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, False)

    def test_case_insensitive_flag(self):
        expression = RegexpLike("title", Value(r"chapter"), flags=Value("i"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)

    def test_case_sensitive_flag_preferred(self):
        expression = RegexpLike("title", Value(r"chapter"), flags=Value("ic"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, False)

    def test_case_insensitive_flag_preferred(self):
        expression = RegexpLike("title", Value(r"Chapter"), flags=Value("ci"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, True)
