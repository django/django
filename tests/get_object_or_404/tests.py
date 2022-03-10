from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_list_or_404, get_object_or_404
from django.test import TestCase

from .models import Article, Author


class GetObjectOr404Tests(TestCase):
    def test_get_object_or_404(self):
        a1 = Author.objects.create(name="Brave Sir Robin")
        a2 = Author.objects.create(name="Patsy")

        # No Articles yet, so we should get an Http404 error.
        with self.assertRaises(Http404):
            get_object_or_404(Article, title="Foo")

        article = Article.objects.create(title="Run away!")
        article.authors.set([a1, a2])
        # get_object_or_404 can be passed a Model to query.
        self.assertEqual(get_object_or_404(Article, title__contains="Run"), article)

        # We can also use the Article manager through an Author object.
        self.assertEqual(
            get_object_or_404(a1.article_set, title__contains="Run"), article
        )

        # No articles containing "Camelot". This should raise an Http404 error.
        with self.assertRaises(Http404):
            get_object_or_404(a1.article_set, title__contains="Camelot")

        # Custom managers can be used too.
        self.assertEqual(
            get_object_or_404(Article.by_a_sir, title="Run away!"), article
        )

        # QuerySets can be used too.
        self.assertEqual(
            get_object_or_404(Article.objects.all(), title__contains="Run"), article
        )

        # Just as when using a get() lookup, you will get an error if more than
        # one object is returned.

        with self.assertRaises(Author.MultipleObjectsReturned):
            get_object_or_404(Author.objects.all())

        # Using an empty QuerySet raises an Http404 error.
        with self.assertRaises(Http404):
            get_object_or_404(Article.objects.none(), title__contains="Run")

        # get_list_or_404 can be used to get lists of objects
        self.assertEqual(
            get_list_or_404(a1.article_set, title__icontains="Run"), [article]
        )

        # Http404 is returned if the list is empty.
        with self.assertRaises(Http404):
            get_list_or_404(a1.article_set, title__icontains="Shrubbery")

        # Custom managers can be used too.
        self.assertEqual(
            get_list_or_404(Article.by_a_sir, title__icontains="Run"), [article]
        )

        # QuerySets can be used too.
        self.assertEqual(
            get_list_or_404(Article.objects.all(), title__icontains="Run"), [article]
        )
        # Q objects.
        self.assertEqual(
            get_object_or_404(
                Article,
                Q(title__startswith="Run") | Q(title__startswith="Walk"),
                authors__name__contains="Brave",
            ),
            article,
        )
        self.assertEqual(
            get_list_or_404(
                Article,
                Q(title__startswith="Run") | Q(title__startswith="Walk"),
                authors__name="Patsy",
            ),
            [article],
        )

    def test_bad_class(self):
        # Given an argument klass that is not a Model, Manager, or Queryset
        # raises a helpful ValueError message
        msg = (
            "First argument to get_object_or_404() must be a Model, Manager, or "
            "QuerySet, not 'str'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            get_object_or_404("Article", title__icontains="Run")

        class CustomClass:
            pass

        msg = (
            "First argument to get_object_or_404() must be a Model, Manager, or "
            "QuerySet, not 'CustomClass'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            get_object_or_404(CustomClass, title__icontains="Run")

        # Works for lists too
        msg = (
            "First argument to get_list_or_404() must be a Model, Manager, or "
            "QuerySet, not 'list'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            get_list_or_404([Article], title__icontains="Run")

    def test_get_object_or_404_queryset_attribute_error(self):
        """AttributeError raised by QuerySet.get() isn't hidden."""
        with self.assertRaisesMessage(AttributeError, "AttributeErrorManager"):
            get_object_or_404(Article.attribute_error_objects, id=42)

    def test_get_list_or_404_queryset_attribute_error(self):
        """AttributeError raised by QuerySet.filter() isn't hidden."""
        with self.assertRaisesMessage(AttributeError, "AttributeErrorManager"):
            get_list_or_404(Article.attribute_error_objects, title__icontains="Run")
