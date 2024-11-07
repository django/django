from django.db.models import Q
from django.shortcuts import get_object_or_none
from django.test import TestCase

from .models import Article, Author


class GetObjectOrNoneTests(TestCase):
    def test_get_object_or_none(self):
        a1 = Author.objects.create(name="Brave Sir Robin")
        article = Article.objects.create(title="Run away!")
        article.authors.set([a1])

        # Test successful retrieval with different query methods
        self.assertEqual(get_object_or_none(Article, title="Run away!"), article)
        self.assertEqual(
            get_object_or_none(Article, Q(title__startswith="Run")), article
        )
        self.assertEqual(
            get_object_or_none(Article.objects.all(), title="Run away!"), article
        )
        self.assertEqual(
            get_object_or_none(a1.article_set, title="Run away!"), article
        )

        # Test non-existent object returns None
        self.assertIsNone(get_object_or_none(Article, title="Does not exist"))
        self.assertIsNone(get_object_or_none(a1.article_set, title="Missing"))

        # Custom managers can be used too
        self.assertEqual(
            get_object_or_none(Article.by_a_sir, title="Run away!"), article
        )

        # Multiple objects should still raise MultipleObjectsReturned
        Author.objects.create(name="Patsy")
        with self.assertRaises(Author.MultipleObjectsReturned):
            get_object_or_none(Author.objects.all())

        # Using an empty QuerySet returns None
        self.assertIsNone(
            get_object_or_none(Article.objects.none(), title="Run away!")
        )

    def test_get_object_or_none_bad_class(self):
        msg = (
            "First argument to get_object_or_none() must be a Model, Manager, or "
            "QuerySet, not 'str'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            get_object_or_none("Article", title="Run away!")

        class CustomClass:
            pass

        msg = (
            "First argument to get_object_or_none() must be a Model, Manager, or "
            "QuerySet, not 'CustomClass'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            get_object_or_none(CustomClass, title="Run away!")

    def test_get_object_or_none_queryset_attribute_error(self):
        """AttributeError raised by QuerySet.get() isn't hidden."""
        with self.assertRaisesMessage(AttributeError, "AttributeErrorManager"):
            get_object_or_none(Article.attribute_error_objects, id=42)
