from django.db import connection
from django.db.models import Value
from django.db.models.functions import Concat, Now, RegexpStrIndex
from django.test import TestCase

from ..models import Article, Author


class RegexpStrIndexTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="George R. R. Martin")
        cls.author2 = Author.objects.create(name="J. R. R. Tolkien")

    def test_invalid_position(self):
        with self.assertRaisesMessage(ValueError, "'position' must be greater than 0."):
            RegexpStrIndex("name", Value(r"(R\. ){2}"), position=0)

    def test_invalid_occurrence(self):
        with self.assertRaisesMessage(
            ValueError, "'occurrence' must be greater than 0."
        ):
            RegexpStrIndex("name", Value(r"(R\. ){2}"), occurrence=0)

    def test_invalid_return_option(self):
        with self.assertRaisesMessage(ValueError, "'return_option' must be 0 or 1."):
            RegexpStrIndex("name", Value(r"(R\. ){2}"), return_option=-1)
        with self.assertRaisesMessage(ValueError, "'return_option' must be 0 or 1."):
            RegexpStrIndex("name", Value(r"(R\. ){2}"), return_option=2)

    def test_null(self):
        tests = [("alias", Value(r"(R\. ){2}"))]
        if connection.vendor != "postgresql" or connection.features.is_postgresql_15:
            # PostgreSQL < 15 workaround doesn't handle NULL passed to pattern.
            tests += [("name", None)]
        for field, pattern in tests:
            with self.subTest(field=field, pattern=pattern):
                expression = RegexpStrIndex(field, pattern)
                author = Author.objects.annotate(index=expression).get(
                    pk=self.author1.pk
                )
                self.assertIsNone(author.index)

    def test_simple(self):
        expression = RegexpStrIndex("name", Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 8),
                ("J. R. R. Tolkien", 4),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_case_sensitive(self):
        expression = RegexpStrIndex("name", Value(r"(r\. ){2}"))
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 0),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_lookahead(self):
        expression = RegexpStrIndex("name", Value(r"(R\. ){2}(?=Martin)"))
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 8),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_lookbehind(self):
        expression = RegexpStrIndex("name", Value(r"(?<=George )(R\. ){2}"))
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 8),
                ("J. R. R. Tolkien", 0),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_substitution(self):
        expression = RegexpStrIndex("name", Value(r"(R\. )\1"))
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 8),
                ("J. R. R. Tolkien", 4),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_expression(self):
        expression = RegexpStrIndex(
            Concat(Value("Author: "), "name"), Value(r"(R\. ){2}")
        )
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 16),
                ("J. R. R. Tolkien", 12),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    # TODO: Fix position argument for MariaDB and PostgreSQL < 15?
    def test_position(self):
        expression = RegexpStrIndex("name", Value(r"R\. "), position=7)
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 8),
                ("J. R. R. Tolkien", 7),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    # TODO: Fix occurrence argument for MariaDB and PostgreSQL < 15?
    def test_occurrence(self):
        expression = RegexpStrIndex("name", Value(r"R\. "), occurrence=2)
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 11),
                ("J. R. R. Tolkien", 7),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    # TODO: Fix return_option argument for MariaDB and PostgreSQL < 15?
    def test_return_option(self):
        expression = RegexpStrIndex("name", Value(r"(R\. )+"), return_option=1)
        queryset = Author.objects.annotate(index=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", 14),
                ("J. R. R. Tolkien", 10),
            ],
            transform=lambda x: (x.name, x.index),
            ordered=False,
        )

    def test_update(self):
        Author.objects.update(age=RegexpStrIndex("name", Value(r"(Martin|Tolkien)")))
        self.assertQuerySetEqual(
            Author.objects.all(),
            [
                14,
                10,
            ],
            transform=lambda x: x.age,
            ordered=False,
        )


class RegexpStrIndexFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Article.objects.create(
            title="Chapter One",
            text="First Line.\nSecond Line.\nThird Line.",
            written=Now(),
        )

    def test_dotall_flag(self):
        expression = RegexpStrIndex("text", Value(r"^.*$"), flags=Value("s"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_multiline_flag(self):
        expression = RegexpStrIndex("text", Value(r"^.*\Z"), flags=Value("m"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 26)

    def test_extended_flag(self):
        pattern = Value(
            r"""
            ^[^ ]*
            \ Line\.
            """
        )
        expression = RegexpStrIndex("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_extended_flag_with_comments(self):
        pattern = Value(
            r"""
            ^[^ ]*    # Match word at beginning of line.
            \ Line\.  # Another part of the pattern...
            """
        )
        expression = RegexpStrIndex("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_case_sensitive_flag(self):
        expression = RegexpStrIndex("title", Value(r"chapter"), flags=Value("c"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 0)

    def test_case_insensitive_flag(self):
        expression = RegexpStrIndex("title", Value(r"chapter"), flags=Value("i"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)

    def test_case_sensitive_flag_preferred(self):
        expression = RegexpStrIndex("title", Value(r"chapter"), flags=Value("ic"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 0)

    def test_case_insensitive_flag_preferred(self):
        expression = RegexpStrIndex("title", Value(r"Chapter"), flags=Value("ci"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, 1)
