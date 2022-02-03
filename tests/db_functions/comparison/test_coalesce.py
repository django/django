from django.db.models import Subquery, TextField
from django.db.models.functions import Coalesce, Lower
from django.test import TestCase
from django.utils import timezone

from ..models import Article, Author

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


class CoalesceTests(TestCase):
    def test_basic(self):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda")
        authors = Author.objects.annotate(display_name=Coalesce("alias", "name"))
        self.assertQuerysetEqual(
            authors.order_by("name"), ["smithj", "Rhonda"], lambda a: a.display_name
        )

    def test_gt_two_expressions(self):
        with self.assertRaisesMessage(
            ValueError, "Coalesce must take at least two expressions"
        ):
            Author.objects.annotate(display_name=Coalesce("alias"))

    def test_mixed_values(self):
        a1 = Author.objects.create(name="John Smith", alias="smithj")
        a2 = Author.objects.create(name="Rhonda")
        ar1 = Article.objects.create(
            title="How to Django",
            text=lorem_ipsum,
            written=timezone.now(),
        )
        ar1.authors.add(a1)
        ar1.authors.add(a2)
        # mixed Text and Char
        article = Article.objects.annotate(
            headline=Coalesce("summary", "text", output_field=TextField()),
        )
        self.assertQuerysetEqual(
            article.order_by("title"), [lorem_ipsum], lambda a: a.headline
        )
        # mixed Text and Char wrapped
        article = Article.objects.annotate(
            headline=Coalesce(
                Lower("summary"), Lower("text"), output_field=TextField()
            ),
        )
        self.assertQuerysetEqual(
            article.order_by("title"), [lorem_ipsum.lower()], lambda a: a.headline
        )

    def test_ordering(self):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda")
        authors = Author.objects.order_by(Coalesce("alias", "name"))
        self.assertQuerysetEqual(authors, ["Rhonda", "John Smith"], lambda a: a.name)
        authors = Author.objects.order_by(Coalesce("alias", "name").asc())
        self.assertQuerysetEqual(authors, ["Rhonda", "John Smith"], lambda a: a.name)
        authors = Author.objects.order_by(Coalesce("alias", "name").desc())
        self.assertQuerysetEqual(authors, ["John Smith", "Rhonda"], lambda a: a.name)

    def test_empty_queryset(self):
        Author.objects.create(name="John Smith")
        tests = [
            Author.objects.none(),
            Subquery(Author.objects.none()),
        ]
        for empty_query in tests:
            with self.subTest(empty_query.__class__.__name__):
                qs = Author.objects.annotate(annotation=Coalesce(empty_query, 42))
                self.assertEqual(qs.first().annotation, 42)
