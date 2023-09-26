from django.db.models import Value
from django.db.models.functions import Concat, Now, RegexpCount
from django.test import TestCase

from ..models import Article, Author


class RegexpCountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="George R. R. Martin")
        cls.author2 = Author.objects.create(name="J. R. R. Tolkien")

    def test_invalid_position(self):
        with self.assertRaisesMessage(ValueError, "'position' must be greater than 0."):
            RegexpCount("name", Value(r"(R\. ){2}"), position=0)

    def test_null(self):
        tests = [("alias", Value(r"(R\. ){2}")), ("name", None)]
        for field, pattern in tests:
            with self.subTest(field=field, pattern=pattern):
                expression = RegexpCount(field, pattern)
                author = Author.objects.annotate(count=expression).get(
                    pk=self.author1.pk
                )
                self.assertIsNone(author.count)

    def test_simple(self):
        expression = RegexpCount("name", Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 1),
                ("J. R. R. Tolkien", 1),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_case_sensitive(self):
        expression = RegexpCount("name", Value(r"(r\. ){2}"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 0),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_lookahead(self):
        expression = RegexpCount("name", Value(r"(R\. ){2}(?=Martin)"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 1),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_lookbehind(self):
        expression = RegexpCount("name", Value(r"(?<=George )(R\. ){2}"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 1),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_substitution(self):
        expression = RegexpCount("name", Value(r"(R\. )\1"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 1),
                ("J. R. R. Tolkien", 1),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_expression(self):
        expression = RegexpCount(Concat(Value("Author: "), "name"), Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 1),
                ("J. R. R. Tolkien", 1),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_position(self):
        expression = RegexpCount("name", Value(r"R\. "), position=7)
        queryset = Author.objects.annotate(count=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 2),
                ("J. R. R. Tolkien", 1),
            ],
            transform=lambda x: (x.name, x.count),
            ordered=False,
        )

    def test_update(self):
        Author.objects.update(age=RegexpCount("name", Value(r"R\.")))
        self.assertQuerySetEqual(
            Author.objects.all(),
            [
                2,
                2,
            ],
            transform=lambda x: x.age,
            ordered=False,
        )


class RegexpCountFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Article.objects.create(
            title="Chapter One",
            text="First Line.\nSecond Line.\nThird Line.",
            written=Now(),
        )

    def test_dotall_flag(self):
        expression = RegexpCount("text", Value(r"^.*$"), flags=Value("s"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_multiline_flag(self):
        expression = RegexpCount("text", Value(r"^.*\Z"), flags=Value("m"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_extended_flag(self):
        pattern = Value(
            r"""
            ^[^ ]*
            \ Line\.
            """
        )
        expression = RegexpCount("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_extended_flag_with_comments(self):
        pattern = Value(
            r"""
            ^[^ ]*    # Match word at beginning of line.
            \ Line\.  # Another part of the pattern...
            """
        )
        expression = RegexpCount("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_case_sensitive_flag(self):
        expression = RegexpCount("title", Value(r"chapter"), flags=Value("c"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 0)

    def test_case_insensitive_flag(self):
        expression = RegexpCount("title", Value(r"chapter"), flags=Value("i"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_case_sensitive_flag_preferred(self):
        expression = RegexpCount("title", Value(r"chapter"), flags=Value("ic"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 0)

    def test_case_insensitive_flag_preferred(self):
        expression = RegexpCount("title", Value(r"Chapter"), flags=Value("ci"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)
