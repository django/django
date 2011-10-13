from __future__ import absolute_import

from datetime import date

from django.test import TestCase

from .models import Article


class MethodsTests(TestCase):
    def test_custom_methods(self):
        a = Article.objects.create(
            headline="Area man programs in Python", pub_date=date(2005, 7, 27)
        )
        b = Article.objects.create(
            headline="Beatles reunite", pub_date=date(2005, 7, 27)
        )

        self.assertFalse(a.was_published_today())
        self.assertQuerysetEqual(
            a.articles_from_same_day_1(), [
                "Beatles reunite",
            ],
            lambda a: a.headline,
        )
        self.assertQuerysetEqual(
            a.articles_from_same_day_2(), [
                "Beatles reunite",
            ],
            lambda a: a.headline
        )

        self.assertQuerysetEqual(
            b.articles_from_same_day_1(), [
                "Area man programs in Python",
            ],
            lambda a: a.headline,
        )
        self.assertQuerysetEqual(
            b.articles_from_same_day_2(), [
                "Area man programs in Python",
            ],
            lambda a: a.headline
        )
