from django.db import connection
from django.db.models import Value
from django.db.models.functions import Concat, Now, RegexpSubstr
from django.test import TestCase

from ..models import Article, Author


class RegexpSubstrTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="George R. R. Martin")
        cls.author2 = Author.objects.create(name="J. R. R. Tolkien")

    @property
    def empty(self):
        mariadb = connection.vendor == "mysql" and connection.mysql_is_mariadb
        return (
            ""
            if mariadb or connection.features.interprets_empty_strings_as_nulls
            else None
        )

    def test_invalid_position(self):
        with self.assertRaisesMessage(ValueError, "'position' must be greater than 0."):
            RegexpSubstr("name", Value(r"(R\. ){2}"), position=0)

    def test_invalid_occurrence(self):
        with self.assertRaisesMessage(
            ValueError, "'occurrence' must be greater than 0."
        ):
            RegexpSubstr("name", Value(r"(R\. ){2}"), occurrence=0)

    def test_null(self):
        tests = [("alias", Value(r"(R\. ){2}")), ("name", None)]
        expected = "" if connection.features.interprets_empty_strings_as_nulls else None
        for field, pattern in tests:
            with self.subTest(field=field, pattern=pattern):
                expression = RegexpSubstr(field, pattern)
                author = Author.objects.annotate(substr=expression).get(
                    pk=self.author1.pk
                )
                self.assertEqual(author.substr, expected)

    def test_simple(self):
        expression = RegexpSubstr("name", Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(only_middlename=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", "R. R. "),
            ],
            transform=lambda x: (x.name, x.only_middlename),
            ordered=False,
        )

    def test_case_sensitive(self):
        expression = RegexpSubstr("name", Value(r"(r\. ){2}"))
        queryset = Author.objects.annotate(same_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", self.empty),
                ("J. R. R. Tolkien", self.empty),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )

    def test_lookahead(self):
        expression = RegexpSubstr("name", Value(r"(R\. ){2}(?=Martin)"))
        queryset = Author.objects.annotate(altered_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", self.empty),
            ],
            transform=lambda x: (x.name, x.altered_name),
            ordered=False,
        )

    def test_lookbehind(self):
        expression = RegexpSubstr("name", Value(r"(?<=George )(R\. ){2}"))
        queryset = Author.objects.annotate(altered_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", self.empty),
            ],
            transform=lambda x: (x.name, x.altered_name),
            ordered=False,
        )

    def test_substitution(self):
        expression = RegexpSubstr("name", Value(r"(R\. )\1"))
        queryset = Author.objects.annotate(flipped_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", "R. R. "),
            ],
            transform=lambda x: (x.name, x.flipped_name),
            ordered=False,
        )

    def test_expression(self):
        expression = RegexpSubstr(
            Concat(Value("Author: "), "name"), Value(r"(R\. ){2}")
        )
        queryset = Author.objects.annotate(substr=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", "R. R. "),
            ],
            transform=lambda x: (x.name, x.substr),
            ordered=False,
        )

    # TODO: Fix position argument for MariaDB and PostgreSQL < 15?
    def test_position(self):
        expression = RegexpSubstr("name", Value(r"(R\. )+"), position=7)
        queryset = Author.objects.annotate(substr=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "R. R. "),
                ("J. R. R. Tolkien", "R. "),
            ],
            transform=lambda x: (x.name, x.substr),
            ordered=False,
        )

    # TODO: Fix occurrence argument for MariaDB and PostgreSQL < 15?
    def test_occurrence(self):
        expression = RegexpSubstr("name", Value(r"[A-Z]"), occurrence=4)
        queryset = Author.objects.annotate(substr=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "M"),
                ("J. R. R. Tolkien", "T"),
            ],
            transform=lambda x: (x.name, x.substr),
            ordered=False,
        )

    def test_update(self):
        Author.objects.update(name=RegexpSubstr("name", Value(r"(Martin|Tolkien)")))
        self.assertQuerySetEqual(
            Author.objects.all(),
            [
                "Martin",
                "Tolkien",
            ],
            transform=lambda x: x.name,
            ordered=False,
        )


class RegexpSubstrFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Article.objects.create(
            title="Chapter One",
            text="First Line.\nSecond Line.\nThird Line.",
            written=Now(),
        )

    @property
    def empty(self):
        mariadb = connection.vendor == "mysql" and connection.mysql_is_mariadb
        return (
            ""
            if mariadb or connection.features.interprets_empty_strings_as_nulls
            else None
        )

    def test_dotall_flag(self):
        expression = RegexpSubstr("text", Value(r"^.*$"), flags=Value("s"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First Line.\nSecond Line.\nThird Line.")

    def test_multiline_flag(self):
        expression = RegexpSubstr("text", Value(r"^.*\Z"), flags=Value("m"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Third Line.")

    def test_extended_flag(self):
        pattern = Value(
            r"""
            ^[^ ]*
            \ Line\.
            """
        )
        expression = RegexpSubstr("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First Line.")

    def test_extended_flag_with_comments(self):
        pattern = Value(
            r"""
            ^[^ ]*    # Match word at beginning of line.
            \ Line\.  # Another part of the pattern...
            """
        )
        expression = RegexpSubstr("text", pattern, flags=Value("x"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First Line.")

    def test_case_sensitive_flag(self):
        expression = RegexpSubstr("title", Value(r"chapter"), flags=Value("c"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, self.empty)

    def test_case_insensitive_flag(self):
        expression = RegexpSubstr("title", Value(r"chapter"), flags=Value("i"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Chapter")

    def test_case_sensitive_flag_preferred(self):
        expression = RegexpSubstr("title", Value(r"chapter"), flags=Value("ic"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, self.empty)

    def test_case_insensitive_flag_preferred(self):
        expression = RegexpSubstr("title", Value(r"Chapter"), flags=Value("ci"))
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Chapter")
