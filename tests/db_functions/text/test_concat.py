from unittest import skipUnless

from django.db import connection
from django.db.models import CharField, TextField
from django.db.models import Value as V
from django.db.models.functions import Concat, ConcatPair, Upper
from django.test import TestCase
from django.utils import timezone

from ..models import Article, Author

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


class ConcatTests(TestCase):
    def test_basic(self):
        Author.objects.create(name="Jayden")
        Author.objects.create(name="John Smith", alias="smithj", goes_by="John")
        Author.objects.create(name="Margaret", goes_by="Maggie")
        Author.objects.create(name="Rhonda", alias="adnohR")
        authors = Author.objects.annotate(joined=Concat("alias", "goes_by"))
        self.assertQuerySetEqual(
            authors.order_by("name"),
            [
                "",
                "smithjJohn",
                "Maggie",
                "adnohR",
            ],
            lambda a: a.joined,
        )

    def test_gt_two_expressions(self):
        with self.assertRaisesMessage(
            ValueError, "Concat must take at least two expressions"
        ):
            Author.objects.annotate(joined=Concat("alias"))

    def test_many(self):
        Author.objects.create(name="Jayden")
        Author.objects.create(name="John Smith", alias="smithj", goes_by="John")
        Author.objects.create(name="Margaret", goes_by="Maggie")
        Author.objects.create(name="Rhonda", alias="adnohR")
        authors = Author.objects.annotate(
            joined=Concat("name", V(" ("), "goes_by", V(")"), output_field=CharField()),
        )
        self.assertQuerySetEqual(
            authors.order_by("name"),
            [
                "Jayden ()",
                "John Smith (John)",
                "Margaret (Maggie)",
                "Rhonda ()",
            ],
            lambda a: a.joined,
        )

    def test_mixed_char_text(self):
        Article.objects.create(
            title="The Title", text=lorem_ipsum, written=timezone.now()
        )
        article = Article.objects.annotate(
            title_text=Concat("title", V(" - "), "text", output_field=TextField()),
        ).get(title="The Title")
        self.assertEqual(article.title + " - " + article.text, article.title_text)
        # Wrap the concat in something else to ensure that text is returned
        # rather than bytes.
        article = Article.objects.annotate(
            title_text=Upper(
                Concat("title", V(" - "), "text", output_field=TextField())
            ),
        ).get(title="The Title")
        expected = article.title + " - " + article.text
        self.assertEqual(expected.upper(), article.title_text)

    @skipUnless(
        connection.vendor in ("sqlite", "postgresql"),
        "SQLite and PostgreSQL specific implementation detail.",
    )
    def test_coalesce_idempotent(self):
        pair = ConcatPair(V("a"), V("b"))
        # Check nodes counts
        self.assertEqual(len(list(pair.flatten())), 3)
        self.assertEqual(
            len(list(pair.coalesce().flatten())), 7
        )  # + 2 Coalesce + 2 Value()
        self.assertEqual(len(list(pair.flatten())), 3)

    def test_sql_generation_idempotency(self):
        qs = Article.objects.annotate(description=Concat("title", V(": "), "summary"))
        # Multiple compilations should not alter the generated query.
        self.assertEqual(str(qs.query), str(qs.all().query))

    def test_concat_non_str(self):
        Author.objects.create(name="The Name", age=42)
        with self.assertNumQueries(1) as ctx:
            author = Author.objects.annotate(
                name_text=Concat(
                    "name", V(":"), "alias", V(":"), "age", output_field=TextField()
                ),
            ).get()
        self.assertEqual(author.name_text, "The Name::42")
        # Only non-string columns are casted on PostgreSQL.
        self.assertEqual(
            ctx.captured_queries[0]["sql"].count("::text"),
            1 if connection.vendor == "postgresql" else 0,
        )

    def test_equal(self):
        self.assertEqual(
            Concat("foo", "bar", output_field=TextField()),
            Concat("foo", "bar", output_field=TextField()),
        )
        self.assertNotEqual(
            Concat("foo", "bar", output_field=TextField()),
            Concat("foo", "bar", output_field=CharField()),
        )
        self.assertNotEqual(
            Concat("foo", "bar", output_field=TextField()),
            Concat("bar", "foo", output_field=TextField()),
        )
