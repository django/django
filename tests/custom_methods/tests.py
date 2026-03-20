from datetime import date

from django.test import TestCase

from .models import Article


class MethodsTests(TestCase):
    def test_custom_methods(self):
        a = Article.objects.create(
            headline="Parrot programs in Python", pub_date=date(2005, 7, 27)
        )
        b = Article.objects.create(
            headline="Beatles reunite", pub_date=date(2005, 7, 27)
        )

        self.assertFalse(a.was_published_today())
        self.assertQuerySetEqual(
            a.articles_from_same_day_1(),
            [
                "Beatles reunite",
            ],
            lambda a: a.headline,
        )
        self.assertQuerySetEqual(
            a.articles_from_same_day_2(),
            [
                "Beatles reunite",
            ],
            lambda a: a.headline,
        )

        self.assertQuerySetEqual(
            b.articles_from_same_day_1(),
            [
                "Parrot programs in Python",
            ],
            lambda a: a.headline,
        )
        self.assertQuerySetEqual(
            b.articles_from_same_day_2(),
            [
                "Parrot programs in Python",
            ],
            lambda a: a.headline,
        )

    def test_was_published_today(self):
        a = Article.objects.create(headline="Today's news", pub_date=date.today())
        self.assertTrue(a.was_published_today())

    def test_articles_from_same_day_no_results(self):
        a = Article.objects.create(headline="Lonely article", pub_date=date(2020, 1, 1))
        self.assertQuerySetEqual(a.articles_from_same_day_1(), [])
        self.assertQuerySetEqual(a.articles_from_same_day_2(), [])

    def test_str(self):
        a = Article.objects.create(headline="Test headline", pub_date=date(2023, 6, 15))
        self.assertEqual(str(a), "Test headline")

    def test_articles_from_same_day_different_dates(self):
        a = Article.objects.create(headline="Day 1", pub_date=date(2023, 1, 1))
        Article.objects.create(headline="Day 2", pub_date=date(2023, 1, 2))
        self.assertQuerySetEqual(a.articles_from_same_day_1(), [])
        self.assertQuerySetEqual(a.articles_from_same_day_2(), [])
