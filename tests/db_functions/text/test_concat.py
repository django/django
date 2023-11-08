from unittest import skipUnless

from django.core.exceptions import FieldError
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
            title_text=Concat("title", V(" - "), "text"),
        ).get(title="The Title")
        self.assertEqual(article.title + " - " + article.text, article.title_text)
        # Wrap the concat in something else to ensure that text is returned
        # rather than bytes.
        article = Article.objects.annotate(
            title_text=Upper(Concat("title", V(" - "), "text")),
        ).get(title="The Title")
        expected = article.title + " - " + article.text
        self.assertEqual(expected.upper(), article.title_text)

    def test_resolved_output_field(self):
        qs = Article.objects.annotate(
            title_summary=Concat("title", V(" - "), "summary"),
            title_text=Concat("title", V(" - "), "text"),
        )
        title_summary = qs.query.annotations["title_summary"]
        self.assertIsInstance(title_summary.output_field, CharField)
        self.assertEqual(title_summary.output_field.max_length, 253)
        title_text = qs.query.annotations["title_text"]
        self.assertIsInstance(title_text.output_field, TextField)
        with self.assertRaises(FieldError):
            Article.objects.annotate(concat_mixed=Concat("title", "views")).get()

    @skipUnless(connection.vendor == "sqlite", "sqlite specific implementation detail.")
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
