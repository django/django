from __future__ import absolute_import

from datetime import datetime
from operator import attrgetter

from django.test import TestCase

from .models import Article, ArticlePKOrdering


class OrderingTests(TestCase):
    def test_basic(self):
        a1 = Article.objects.create(
            headline="Article 1", pub_date=datetime(2005, 7, 26)
        )
        a2 = Article.objects.create(
            headline="Article 2", pub_date=datetime(2005, 7, 27)
        )
        a3 = Article.objects.create(
            headline="Article 3", pub_date=datetime(2005, 7, 27)
        )
        a4 = Article.objects.create(
            headline="Article 4", pub_date=datetime(2005, 7, 28)
        )

        # By default, Article.objects.all() orders by pub_date descending, then
        # headline ascending.
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Article 4",
                "Article 2",
                "Article 3",
                "Article 1",
            ],
            attrgetter("headline")
        )

        # Override ordering with order_by, which is in the same format as the
        # ordering attribute in models.
        self.assertQuerysetEqual(
            Article.objects.order_by("headline"), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by("pub_date", "-headline"), [
                "Article 1",
                "Article 3",
                "Article 2",
                "Article 4",
            ],
            attrgetter("headline")
        )

        # Only the last order_by has any effect (since they each override any
        # previous ordering).
        self.assertQuerysetEqual(
            Article.objects.order_by("id"), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )
        self.assertQuerysetEqual(
            Article.objects.order_by("id").order_by("-headline"), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )

        # Use the 'stop' part of slicing notation to limit the results.
        self.assertQuerysetEqual(
            Article.objects.order_by("headline")[:2], [
                "Article 1",
                "Article 2",
            ],
            attrgetter("headline")
        )

        # Use the 'stop' and 'start' parts of slicing notation to offset the
        # result list.
        self.assertQuerysetEqual(
            Article.objects.order_by("headline")[1:3], [
                "Article 2",
                "Article 3",
            ],
            attrgetter("headline")
        )

        # Getting a single item should work too:
        self.assertEqual(Article.objects.all()[0], a4)

        # Use '?' to order randomly.
        self.assertEqual(
            len(list(Article.objects.order_by("?"))), 4
        )

        # Ordering can be reversed using the reverse() method on a queryset.
        # This allows you to extract things like "the last two items" (reverse
        # and then take the first two).
        self.assertQuerysetEqual(
            Article.objects.all().reverse()[:2], [
                "Article 1",
                "Article 3",
            ],
            attrgetter("headline")
        )

        # Ordering can be based on fields included from an 'extra' clause
        self.assertQuerysetEqual(
            Article.objects.extra(select={"foo": "pub_date"}, order_by=["foo", "headline"]), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )

        # If the extra clause uses an SQL keyword for a name, it will be
        # protected by quoting.
        self.assertQuerysetEqual(
            Article.objects.extra(select={"order": "pub_date"}, order_by=["order", "headline"]), [
                "Article 1",
                "Article 2",
                "Article 3",
                "Article 4",
            ],
            attrgetter("headline")
        )

    def test_order_by_pk(self):
        """
        Ensure that 'pk' works as an ordering option in Meta.
        Refs #8291.
        """
        a1 = ArticlePKOrdering.objects.create(
            pk=1, headline="Article 1", pub_date=datetime(2005, 7, 26)
        )
        a2 = ArticlePKOrdering.objects.create(
            pk=2, headline="Article 2", pub_date=datetime(2005, 7, 27)
        )
        a3 = ArticlePKOrdering.objects.create(
            pk=3, headline="Article 3", pub_date=datetime(2005, 7, 27)
        )
        a4 = ArticlePKOrdering.objects.create(
            pk=4, headline="Article 4", pub_date=datetime(2005, 7, 28)
        )

        self.assertQuerysetEqual(
            ArticlePKOrdering.objects.all(), [
                "Article 4",
                "Article 3",
                "Article 2",
                "Article 1",
            ],
            attrgetter("headline")
        )
