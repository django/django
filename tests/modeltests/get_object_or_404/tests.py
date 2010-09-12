from django.http import Http404
from django.shortcuts import get_object_or_404, get_list_or_404
from django.test import TestCase

from models import Author, Article


class GetObjectOr404Tests(TestCase):
    def test_get_object_or_404(self):
        a1 = Author.objects.create(name="Brave Sir Robin")
        a2 = Author.objects.create(name="Patsy")

        # No Articles yet, so we should get a Http404 error.
        self.assertRaises(Http404, get_object_or_404, Article, title="Foo")

        article = Article.objects.create(title="Run away!")
        article.authors = [a1, a2]
        # get_object_or_404 can be passed a Model to query.
        self.assertEqual(
            get_object_or_404(Article, title__contains="Run"),
            article
        )

        # We can also use the Article manager through an Author object.
        self.assertEqual(
            get_object_or_404(a1.article_set, title__contains="Run"),
            article
        )

        # No articles containing "Camelot".  This should raise a Http404 error.
        self.assertRaises(Http404,
            get_object_or_404, a1.article_set, title__contains="Camelot"
        )

        # Custom managers can be used too.
        self.assertEqual(
            get_object_or_404(Article.by_a_sir, title="Run away!"),
            article
        )

        # QuerySets can be used too.
        self.assertEqual(
            get_object_or_404(Article.objects.all(), title__contains="Run"),
            article
        )

        # Just as when using a get() lookup, you will get an error if more than
        # one object is returned.

        self.assertRaises(Author.MultipleObjectsReturned,
            get_object_or_404, Author.objects.all()
        )

        # Using an EmptyQuerySet raises a Http404 error.
        self.assertRaises(Http404,
            get_object_or_404, Article.objects.none(), title__contains="Run"
        )

        # get_list_or_404 can be used to get lists of objects
        self.assertEqual(
            get_list_or_404(a1.article_set, title__icontains="Run"),
            [article]
        )

        # Http404 is returned if the list is empty.
        self.assertRaises(Http404,
            get_list_or_404, a1.article_set, title__icontains="Shrubbery"
        )

        # Custom managers can be used too.
        self.assertEqual(
            get_list_or_404(Article.by_a_sir, title__icontains="Run"),
            [article]
        )

        # QuerySets can be used too.
        self.assertEqual(
            get_list_or_404(Article.objects.all(), title__icontains="Run"),
            [article]
        )
