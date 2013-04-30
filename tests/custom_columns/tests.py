from __future__ import absolute_import

from django.core.exceptions import FieldError
from django.test import TestCase
from django.utils import six

from .models import Author, Article


class CustomColumnsTests(TestCase):
    def setUp(self):
        a1 = Author.objects.create(first_name="John", last_name="Smith")
        a2 = Author.objects.create(first_name="Peter", last_name="Jones")

        art = Article.objects.create(headline="Django lets you build Web apps easily")
        art.authors = [a1, a2]

        self.a1 = a1
        self.art = art

    def test_query_all_available_authors(self):
        self.assertQuerysetEqual(
            Author.objects.all(), [
                "Peter Jones", "John Smith",
            ],
            six.text_type
        )

    def test_get_first_name(self):
        self.assertEqual(
            Author.objects.get(first_name__exact="John"),
            self.a1,
        )

    def test_filter_first_name(self):
        self.assertQuerysetEqual(
            Author.objects.filter(first_name__exact="John"), [
                "John Smith",
            ],
            six.text_type

        )

    def test_field_error(self):
        self.assertRaises(FieldError,
            lambda: Author.objects.filter(firstname__exact="John")
        )

    def test_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.a1.firstname

        with self.assertRaises(AttributeError):
            self.a1.last

    def test_get_all_authors_for_an_article(self):
        self.assertQuerysetEqual(
            self.art.authors.all(), [
                "Peter Jones",
                "John Smith",
            ],
            six.text_type
        )

    def test_get_all_articles_for_an_author(self):
        self.assertQuerysetEqual(
            self.a1.article_set.all(), [
                "Django lets you build Web apps easily",
            ],
            lambda a: a.headline
        )

    def test_get_author_m2m_relation(self):
        self.assertQuerysetEqual(
            self.art.authors.filter(last_name='Jones'), [
                "Peter Jones"
            ],
            six.text_type
        )
