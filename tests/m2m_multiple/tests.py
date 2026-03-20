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

    def test_add_remove(self):
        c = Category.objects.create(name="Tech")
        a = Article.objects.create(headline="Tech news", pub_date=datetime(2023, 1, 1))
        a.primary_categories.add(c)
        self.assertIn(c, a.primary_categories.all())
        a.primary_categories.remove(c)
        self.assertNotIn(c, a.primary_categories.all())

    def test_clear(self):
        c1 = Category.objects.create(name="A")
        c2 = Category.objects.create(name="B")
        a = Article.objects.create(headline="Clear test", pub_date=datetime(2023, 2, 1))
        a.primary_categories.add(c1, c2)
        self.assertEqual(a.primary_categories.count(), 2)
        a.primary_categories.clear()
        self.assertEqual(a.primary_categories.count(), 0)

    def test_reverse_query(self):
        c = Category.objects.create(name="Science")
        a1 = Article.objects.create(headline="Physics", pub_date=datetime(2023, 3, 1))
        a2 = Article.objects.create(headline="Chemistry", pub_date=datetime(2023, 3, 2))
        a1.secondary_categories.add(c)
        a2.secondary_categories.add(c)
        self.assertEqual(c.secondary_article_set.count(), 2)

    def test_set(self):
        c1 = Category.objects.create(name="X")
        c2 = Category.objects.create(name="Y")
        c3 = Category.objects.create(name="Z")
        a = Article.objects.create(headline="Set test", pub_date=datetime(2023, 4, 1))
        a.primary_categories.set([c1, c2])
        self.assertEqual(a.primary_categories.count(), 2)
        a.primary_categories.set([c3])
        self.assertEqual(a.primary_categories.count(), 1)
        self.assertIn(c3, a.primary_categories.all())
