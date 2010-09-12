from django.core.exceptions import FieldError
from django.test import TestCase

from models import Author, Article


class CustomColumnsTests(TestCase):
    def test_db_column(self):
        a1 = Author.objects.create(first_name="John", last_name="Smith")
        a2 = Author.objects.create(first_name="Peter", last_name="Jones")

        art = Article.objects.create(headline="Django lets you build web apps easily")
        art.authors = [a1, a2]

        # Although the table and column names on Author have been set to custom
        # values, nothing about using the Author model has changed...

        # Query the available authors
        self.assertQuerysetEqual(
            Author.objects.all(), [
                "Peter Jones", "John Smith",
            ],
            unicode
        )
        self.assertQuerysetEqual(
            Author.objects.filter(first_name__exact="John"), [
                "John Smith",
            ],
            unicode
        )
        self.assertEqual(
            Author.objects.get(first_name__exact="John"),
            a1,
        )

        self.assertRaises(FieldError,
            lambda: Author.objects.filter(firstname__exact="John")
        )

        a = Author.objects.get(last_name__exact="Smith")
        a.first_name = "John"
        a.last_name = "Smith"

        self.assertRaises(AttributeError, lambda: a.firstname)
        self.assertRaises(AttributeError, lambda: a.last)

        # Although the Article table uses a custom m2m table,
        # nothing about using the m2m relationship has changed...

        # Get all the authors for an article
        self.assertQuerysetEqual(
            art.authors.all(), [
                "Peter Jones",
                "John Smith",
            ],
            unicode
        )
        # Get the articles for an author
        self.assertQuerysetEqual(
            a.article_set.all(), [
                "Django lets you build web apps easily",
            ],
            lambda a: a.headline
        )
        # Query the authors across the m2m relation
        self.assertQuerysetEqual(
            art.authors.filter(last_name='Jones'), [
                "Peter Jones"
            ],
            unicode
        )
