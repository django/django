import datetime
from unittest import skipUnless

from django.core.exceptions import FieldError
from django.db import connection
from django.test import TestCase, override_settings

from .models import Article, Category, Comment


class DatesTests(TestCase):
    def test_related_model_traverse(self):
        a1 = Article.objects.create(
            title="First one",
            pub_date=datetime.date(2005, 7, 28),
        )
        a2 = Article.objects.create(
            title="Another one",
            pub_date=datetime.date(2010, 7, 28),
        )
        a3 = Article.objects.create(
            title="Third one, in the first day",
            pub_date=datetime.date(2005, 7, 28),
        )

        a1.comments.create(
            text="Im the HULK!",
            pub_date=datetime.date(2005, 7, 28),
        )
        a1.comments.create(
            text="HULK SMASH!",
            pub_date=datetime.date(2005, 7, 29),
        )
        a2.comments.create(
            text="LMAO",
            pub_date=datetime.date(2010, 7, 28),
        )
        a3.comments.create(
            text="+1",
            pub_date=datetime.date(2005, 8, 29),
        )

        c = Category.objects.create(name="serious-news")
        c.articles.add(a1, a3)

        self.assertSequenceEqual(
            Comment.objects.dates("article__pub_date", "year"), [
                datetime.date(2005, 1, 1),
                datetime.date(2010, 1, 1),
            ],
        )
        self.assertSequenceEqual(
            Comment.objects.dates("article__pub_date", "month"), [
                datetime.date(2005, 7, 1),
                datetime.date(2010, 7, 1),
            ],
        )
        self.assertSequenceEqual(
            Comment.objects.dates("article__pub_date", "day"), [
                datetime.date(2005, 7, 28),
                datetime.date(2010, 7, 28),
            ],
        )
        self.assertSequenceEqual(
            Article.objects.dates("comments__pub_date", "day"), [
                datetime.date(2005, 7, 28),
                datetime.date(2005, 7, 29),
                datetime.date(2005, 8, 29),
                datetime.date(2010, 7, 28),
            ],
        )
        self.assertQuerysetEqual(
            Article.objects.dates("comments__approval_date", "day"), []
        )
        self.assertSequenceEqual(
            Category.objects.dates("articles__pub_date", "day"), [
                datetime.date(2005, 7, 28),
            ],
        )

    def test_dates_fails_when_no_arguments_are_provided(self):
        with self.assertRaises(TypeError):
            Article.objects.dates()

    def test_dates_fails_when_given_invalid_field_argument(self):
        self.assertRaisesMessage(
            FieldError,
            "Cannot resolve keyword 'invalid_field' into field. Choices are: "
            "categories, comments, id, pub_date, pub_datetime, title",
            Article.objects.dates,
            "invalid_field",
            "year",
        )

    def test_dates_fails_when_given_invalid_kind_argument(self):
        with self.assertRaisesMessage(AssertionError, "'kind' must be one of 'year', 'month' or 'day'."):
            Article.objects.dates("pub_date", "bad_kind")

    def test_dates_fails_when_given_invalid_order_argument(self):
        with self.assertRaisesMessage(AssertionError, "'order' must be either 'ASC' or 'DESC'."):
            Article.objects.dates("pub_date", "year", order="bad order")

    @override_settings(USE_TZ=False)
    def test_dates_trunc_datetime_fields(self):
        Article.objects.bulk_create(
            Article(pub_date=pub_datetime.date(), pub_datetime=pub_datetime)
            for pub_datetime in [
                datetime.datetime(2015, 10, 21, 18, 1),
                datetime.datetime(2015, 10, 21, 18, 2),
                datetime.datetime(2015, 10, 22, 18, 1),
                datetime.datetime(2015, 10, 22, 18, 2),
            ]
        )
        self.assertSequenceEqual(
            Article.objects.dates('pub_datetime', 'day', order='ASC'), [
                datetime.date(2015, 10, 21),
                datetime.date(2015, 10, 22),
            ]
        )

    @skipUnless(connection.vendor == 'mysql', "Test checks MySQL query syntax")
    def test_dates_avoid_datetime_cast(self):
        Article.objects.create(pub_date=datetime.date(2015, 10, 21))
        for kind in ['day', 'month', 'year']:
            qs = Article.objects.dates('pub_date', kind)
            if kind == 'day':
                self.assertIn('DATE(', str(qs.query))
            else:
                self.assertIn(' AS DATE)', str(qs.query))
