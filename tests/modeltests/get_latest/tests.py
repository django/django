from __future__ import absolute_import

from datetime import datetime

from django.test import TestCase

from .models import Article, Person


class LatestTests(TestCase):
    def test_latest(self):
        # Because no Articles exist yet, latest() raises ArticleDoesNotExist.
        self.assertRaises(Article.DoesNotExist, Article.objects.latest)

        a1 = Article.objects.create(
            headline="Article 1", pub_date=datetime(2005, 7, 26),
            expire_date=datetime(2005, 9, 1)
        )
        a2 = Article.objects.create(
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

    def test_latest_manual(self):
        # You can still use latest() with a model that doesn't have
        # "get_latest_by" set -- just pass in the field name manually.
        p1 = Person.objects.create(name="Ralph", birthday=datetime(1950, 1, 1))
        p2 = Person.objects.create(name="Stephanie", birthday=datetime(1960, 2, 3))
        self.assertRaises(AssertionError, Person.objects.latest)

        self.assertEqual(Person.objects.latest("birthday"), p2)
