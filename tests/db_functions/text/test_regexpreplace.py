import unittest

from django.db import connection
from django.db.models import Value
from django.db.models.functions import Concat, Now, RegexpReplace
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from ..models import Article, Author


class RegexpReplaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="George R. R. Martin")
        cls.author2 = Author.objects.create(name="J. R. R. Tolkien")

    def test_invalid_position(self):
        with self.assertRaisesMessage(ValueError, "'position' must be greater than 0."):
            RegexpReplace("name", Value(r"(R\. ){2}"), Value(""), position=0)

    def test_invalid_occurrencen(self):
        with self.assertRaisesMessage(
            ValueError, "'occurrence' must be greater than or equal to 0."
        ):
            RegexpReplace("name", Value(r"(R\. ){2}"), Value(""), occurrence=-1)

    def test_null(self):
        tests = [("alias", Value(r"(R\. ){2}"), Value(""))]
        if not connection.features.interprets_empty_strings_as_nulls:
            # Oracle returns original string for NULL pattern and treats NULL
            # replacement as empty string returning the string with the pattern
            # removed.
            tests += [
                ("name", None, Value("")),
                ("name", Value(r"(R\. ){2}"), None),
            ]
        expected = "" if connection.features.interprets_empty_strings_as_nulls else None
        for field, pattern, replacement in tests:
            with self.subTest(field=field, pattern=pattern, replacement=replacement):
                expression = RegexpReplace(field, pattern, replacement)
                author = Author.objects.annotate(replaced=expression).get(
                    pk=self.author1.pk
                )
                self.assertEqual(author.replaced, expected)

    def test_simple(self):
        # The default replacement is an empty string.
        expression = RegexpReplace("name", Value(r"(R\. ){2}"))
        queryset = Author.objects.annotate(without_middlename=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George Martin"),
                ("J. R. R. Tolkien", "J. Tolkien"),
            ],
            transform=lambda x: (x.name, x.without_middlename),
            ordered=False,
        )

    def test_case_sensitive(self):
        expression = RegexpReplace("name", Value(r"(r\. ){2}"), Value(""))
        queryset = Author.objects.annotate(same_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George R. R. Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )

    def test_lookahead(self):
        expression = RegexpReplace("name", Value(r"(R\. ){2}(?=Martin)"), Value(""))
        queryset = Author.objects.annotate(altered_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.altered_name),
            ordered=False,
        )

    def test_lookbehind(self):
        expression = RegexpReplace("name", Value(r"(?<=George )(R\. ){2}"), Value(""))
        queryset = Author.objects.annotate(altered_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.altered_name),
            ordered=False,
        )

    def test_substitution(self):
        if connection.vendor == "oracle":
            # Oracle doesn't support non-capturing groups.
            expression = RegexpReplace(
                "name", Value(r"^(.*(R\. ?){2}) (.*)$"), Value(r"\3, \1")
            )
        elif connection.vendor == "mysql" and not connection.mysql_is_mariadb:
            # MySQL uses dollar instead of backslash in replacement.
            expression = RegexpReplace(
                "name", Value(r"^(.*(?:R\. ?){2}) (.*)$"), Value(r"$2, $1")
            )
        else:
            expression = RegexpReplace(
                "name", Value(r"^(.*(?:R\. ?){2}) (.*)$"), Value(r"\2, \1")
            )
        queryset = Author.objects.annotate(flipped_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "Martin, George R. R."),
                ("J. R. R. Tolkien", "Tolkien, J. R. R."),
            ],
            transform=lambda x: (x.name, x.flipped_name),
            ordered=False,
        )

    def test_expression(self):
        expression = RegexpReplace(
            Concat(Value("Author: "), "name"), Value(r".*: "), Value("")
        )
        queryset = Author.objects.annotate(same_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George R. R. Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )

    # TODO: Fix position argument for MariaDB and PostgreSQL < 15?
    def test_position(self):
        expression = RegexpReplace("name", Value(r"R\. "), Value("X. "), position=7)
        queryset = Author.objects.annotate(new_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George X. R. Martin"),
                ("J. R. R. Tolkien", "J. R. X. Tolkien"),
            ],
            transform=lambda x: (x.name, x.new_name),
            ordered=False,
        )

    def test_first_occurrence(self):
        expression = RegexpReplace("name", Value(r"R\. "), Value("X. "))
        queryset = Author.objects.annotate(single_middlename=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George X. R. Martin"),
                ("J. R. R. Tolkien", "J. X. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.single_middlename),
            ordered=False,
        )

    # TODO: Fix occurrence argument for MariaDB and PostgreSQL < 15?
    def test_second_occurrence(self):
        expression = RegexpReplace("name", Value(r"R\. "), Value("X. "), occurrence=2)
        queryset = Author.objects.annotate(new_name=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George R. X. Martin"),
                ("J. R. R. Tolkien", "J. R. X. Tolkien"),
            ],
            transform=lambda x: (x.name, x.new_name),
            ordered=False,
        )

    def test_all_occurrences(self):
        # MariaDB only supports replacing all occurrences.
        expression = RegexpReplace("name", Value(r"R\. "), Value("X. "), occurrence=0)
        queryset = Author.objects.annotate(no_middlename=expression)
        self.assertQuerySetEqual(
            queryset,
            [
                ("George R. R. Martin", "George X. X. Martin"),
                ("J. R. R. Tolkien", "J. X. X. Tolkien"),
            ],
            transform=lambda x: (x.name, x.no_middlename),
            ordered=False,
        )

    def test_update(self):
        Author.objects.update(
            name=RegexpReplace("name", Value(r"(R\. ){2}"), Value(""))
        )
        self.assertQuerySetEqual(
            Author.objects.all(),
            [
                "George Martin",
                "J. Tolkien",
            ],
            transform=lambda x: x.name,
            ordered=False,
        )


class RegexpReplaceFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Article.objects.create(
            title="Chapter One",
            text="First Line.\nSecond Line.\nThird Line.",
            written=Now(),
        )

    def test_dotall_flag(self):
        expression = RegexpReplace(
            "text", Value(r"\.."), Value(", "), occurrence=0, flags=Value("s")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First Line, Second Line, Third Line.")

    def test_multiline_flag(self):
        expression = RegexpReplace(
            "text", Value(r" Line\.$"), Value(""), occurrence=0, flags=Value("m")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First\nSecond\nThird")

    def test_extended_flag(self):
        pattern = Value(
            r"""
            .
            Line
            \.
            """
        )
        expression = RegexpReplace(
            "text", pattern, Value(""), occurrence=0, flags=Value("x")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First\nSecond\nThird")

    def test_extended_flag_with_comments(self):
        pattern = Value(
            r"""
            .     # Match the space character
            Line  # Match the word "Line"
            \.    # Match the period.
            """
        )
        expression = RegexpReplace(
            "text", pattern, Value(""), occurrence=0, flags=Value("x")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "First\nSecond\nThird")

    def test_case_sensitive_flag(self):
        expression = RegexpReplace(
            "title", Value(r"chapter"), Value("Section"), flags=Value("c")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Chapter One")

    def test_case_insensitive_flag(self):
        expression = RegexpReplace(
            "title", Value(r"chapter"), Value("Section"), flags=Value("i")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Section One")

    def test_case_sensitive_flag_preferred(self):
        expression = RegexpReplace(
            "title", Value(r"chapter"), Value("Section"), flags=Value("ic")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Chapter One")

    def test_case_insensitive_flag_preferred(self):
        expression = RegexpReplace(
            "title", Value(r"Chapter"), Value("Section"), flags=Value("ci")
        )
        article = Article.objects.annotate(result=expression).first()
        self.assertEqual(article.result, "Section One")

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL test")
    def test_backend_specific_flags_not_stripped(self):
        # Check that any additional flags passed that Django doesn't handle
        # will still get to the backend.
        expression = RegexpReplace(
            "text", Value(" Line"), Value(""), occurrence=0, flags=Value("w")
        )

        with CaptureQueriesContext(connection) as captured_queries:
            article = Article.objects.annotate(result=expression).first()

        expected = ", 'pw')" if connection.features.is_postgresql_15 else ", 'pwg')"
        self.assertIn(expected, captured_queries[0]["sql"])
        self.assertEqual(article.result, "First.\nSecond.\nThird.")
