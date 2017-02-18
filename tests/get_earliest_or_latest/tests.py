from __future__ import unicode_literals

from datetime import datetime

from django.test import TestCase

from .models import Article, IndexErrorArticle, Person


class EarliestOrLatestTests(TestCase):
    """Tests for the earliest() and latest() objects methods"""

    def tearDown(self):
        """Makes sure Article has a get_latest_by"""
        if not Article._meta.get_latest_by:
            Article._meta.get_latest_by = 'pub_date'

    def test_earliest(self):
        # Because no Articles exist yet, earliest() raises ArticleDoesNotExist.
        self.assertRaises(Article.DoesNotExist, Article.objects.earliest)

        a1 = Article.objects.create(
            headline="Article 1", pub_date=datetime(2005, 7, 26),
            expire_date=datetime(2005, 9, 1)
        )
        a2 = Article.objects.create(
            headline="Article 2", pub_date=datetime(2005, 7, 27),
            expire_date=datetime(2005, 7, 28)
        )
        Article.objects.create(
            headline="Article 3", pub_date=datetime(2005, 7, 28),
            expire_date=datetime(2005, 8, 27)
        )
        Article.objects.create(
            headline="Article 4", pub_date=datetime(2005, 7, 28),
            expire_date=datetime(2005, 7, 30)
        )

        # Get the earliest Article.
        self.assertEqual(Article.objects.earliest(), a1)
        # Get the earliest Article that matches certain filters.
        self.assertEqual(
            Article.objects.filter(pub_date__gt=datetime(2005, 7, 26)).earliest(),
            a2
        )

        # Pass a custom field name to earliest() to change the field that's used
        # to determine the earliest object.
        self.assertEqual(Article.objects.earliest('expire_date'), a2)
        self.assertEqual(Article.objects.filter(
            pub_date__gt=datetime(2005, 7, 26)).earliest('expire_date'), a2)

        # Ensure that earliest() overrides any other ordering specified on the
        # query. Refs #11283.
        self.assertEqual(Article.objects.order_by('id').earliest(), a1)

        # Ensure that error is raised if the user forgot to add a get_latest_by
        # in the Model.Meta
        Article.objects.model._meta.get_latest_by = None
        self.assertRaisesMessage(
            AssertionError,
            "earliest() and latest() require either a field_name parameter or "
            "'get_latest_by' in the model",
            lambda: Article.objects.earliest(),
        )

    def test_latest(self):
        # Because no Articles exist yet, latest() raises ArticleDoesNotExist.
        self.assertRaises(Article.DoesNotExist, Article.objects.latest)

        a1 = Article.objects.create(
            headline="Article 1", pub_date=datetime(2005, 7, 26),
            expire_date=datetime(2005, 9, 1)
        )
        Article.objects.create(
            headline="Article 2", pub_date=datetime(2005, 7, 27),
            expire_date=datetime(2005, 7, 28)
        )
        a3 = Article.objects.create(
            headline="Article 3", pub_date=datetime(2005, 7, 27),
            expire_date=datetime(2005, 8, 27)
        )
        a4 = Article.objects.create(
            headline="Article 4", pub_date=datetime(2005, 7, 28),
            expire_date=datetime(2005, 7, 30)
        )

        # Get the latest Article.
        self.assertEqual(Article.objects.latest(), a4)
        # Get the latest Article that matches certain filters.
        self.assertEqual(
            Article.objects.filter(pub_date__lt=datetime(2005, 7, 27)).latest(),
            a1
        )

        # Pass a custom field name to latest() to change the field that's used
        # to determine the latest object.
        self.assertEqual(Article.objects.latest('expire_date'), a1)
        self.assertEqual(
            Article.objects.filter(pub_date__gt=datetime(2005, 7, 26)).latest('expire_date'),
            a3,
        )

        # Ensure that latest() overrides any other ordering specified on the query. Refs #11283.
        self.assertEqual(Article.objects.order_by('id').latest(), a4)

        # Ensure that error is raised if the user forgot to add a get_latest_by
        # in the Model.Meta
        Article.objects.model._meta.get_latest_by = None
        self.assertRaisesMessage(
            AssertionError,
            "earliest() and latest() require either a field_name parameter or "
            "'get_latest_by' in the model",
            lambda: Article.objects.latest(),
        )

    def test_latest_manual(self):
        # You can still use latest() with a model that doesn't have
        # "get_latest_by" set -- just pass in the field name manually.
        Person.objects.create(name="Ralph", birthday=datetime(1950, 1, 1))
        p2 = Person.objects.create(name="Stephanie", birthday=datetime(1960, 2, 3))
        self.assertRaises(AssertionError, Person.objects.latest)
        self.assertEqual(Person.objects.latest("birthday"), p2)


class TestFirstLast(TestCase):

    def test_first(self):
        p1 = Person.objects.create(name="Bob", birthday=datetime(1950, 1, 1))
        p2 = Person.objects.create(name="Alice", birthday=datetime(1961, 2, 3))
        self.assertEqual(
            Person.objects.first(), p1)
        self.assertEqual(
            Person.objects.order_by('name').first(), p2)
        self.assertEqual(
            Person.objects.filter(birthday__lte=datetime(1955, 1, 1)).first(),
            p1)
        self.assertIs(
            Person.objects.filter(birthday__lte=datetime(1940, 1, 1)).first(),
            None)

    def test_last(self):
        p1 = Person.objects.create(
            name="Alice", birthday=datetime(1950, 1, 1))
        p2 = Person.objects.create(
            name="Bob", birthday=datetime(1960, 2, 3))
        # Note: by default PK ordering.
        self.assertEqual(
            Person.objects.last(), p2)
        self.assertEqual(
            Person.objects.order_by('-name').last(), p1)
        self.assertEqual(
            Person.objects.filter(birthday__lte=datetime(1955, 1, 1)).last(),
            p1)
        self.assertIs(
            Person.objects.filter(birthday__lte=datetime(1940, 1, 1)).last(),
            None)

    def test_index_error_not_suppressed(self):
        """
        #23555 -- Unexpected IndexError exceptions in QuerySet iteration
        shouldn't be suppressed.
        """
        def check():
            # We know that we've broken the __iter__ method, so the queryset
            # should always raise an exception.
            self.assertRaises(IndexError, lambda: IndexErrorArticle.objects.all()[0])
            self.assertRaises(IndexError, IndexErrorArticle.objects.all().first)
            self.assertRaises(IndexError, IndexErrorArticle.objects.all().last)

        check()

        # And it does not matter if there are any records in the DB.
        IndexErrorArticle.objects.create(
            headline="Article 1", pub_date=datetime(2005, 7, 26),
            expire_date=datetime(2005, 9, 1)
        )
        check()
