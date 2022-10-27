from datetime import datetime

from django.test import TestCase

from .models import Article, Category


class M2MMultipleTests(TestCase):
    def test_multiple(self):
        c1, c2, c3, c4 = [
            Category.objects.create(name=name)
            for name in ["Sports", "News", "Crime", "Life"]
        ]

        a1 = Article.objects.create(
            headline="Parrot steals", pub_date=datetime(2005, 11, 27)
        )
        a1.primary_categories.add(c2, c3)
        a1.secondary_categories.add(c4)

        a2 = Article.objects.create(
            headline="Parrot runs", pub_date=datetime(2005, 11, 28)
        )
        a2.primary_categories.add(c1, c2)
        a2.secondary_categories.add(c4)

        self.assertQuerySetEqual(
            a1.primary_categories.all(),
            [
                "Crime",
                "News",
            ],
            lambda c: c.name,
        )
        self.assertQuerySetEqual(
            a2.primary_categories.all(),
            [
                "News",
                "Sports",
            ],
            lambda c: c.name,
        )
        self.assertQuerySetEqual(
            a1.secondary_categories.all(),
            [
                "Life",
            ],
            lambda c: c.name,
        )
        self.assertQuerySetEqual(
            c1.primary_article_set.all(),
            [
                "Parrot runs",
            ],
            lambda a: a.headline,
        )
        self.assertQuerySetEqual(c1.secondary_article_set.all(), [])
        self.assertQuerySetEqual(
            c2.primary_article_set.all(),
            [
                "Parrot steals",
                "Parrot runs",
            ],
            lambda a: a.headline,
        )
        self.assertQuerySetEqual(c2.secondary_article_set.all(), [])
        self.assertQuerySetEqual(
            c3.primary_article_set.all(),
            [
                "Parrot steals",
            ],
            lambda a: a.headline,
        )
        self.assertQuerySetEqual(c3.secondary_article_set.all(), [])
        self.assertQuerySetEqual(c4.primary_article_set.all(), [])
        self.assertQuerySetEqual(
            c4.secondary_article_set.all(),
            [
                "Parrot steals",
                "Parrot runs",
            ],
            lambda a: a.headline,
        )
