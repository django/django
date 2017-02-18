from __future__ import unicode_literals

import datetime

from django.core.exceptions import FieldError
from django.test import TestCase
from django.utils import six

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

        self.assertQuerysetEqual(
            Comment.objects.dates("article__pub_date", "year"), [
                datetime.date(2005, 1, 1),
                datetime.date(2010, 1, 1),
            ],
            lambda d: d,
        )
        self.assertQuerysetEqual(
            Comment.objects.dates("article__pub_date", "month"), [
                datetime.date(2005, 7, 1),
                datetime.date(2010, 7, 1),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Comment.objects.dates("article__pub_date", "day"), [
                datetime.date(2005, 7, 28),
                datetime.date(2010, 7, 28),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Article.objects.dates("comments__pub_date", "day"), [
                datetime.date(2005, 7, 28),
                datetime.date(2005, 7, 29),
                datetime.date(2005, 8, 29),
                datetime.date(2010, 7, 28),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Article.objects.dates("comments__approval_date", "day"), []
        )
        self.assertQuerysetEqual(
            Category.objects.dates("articles__pub_date", "day"), [
                datetime.date(2005, 7, 28),
            ],
            lambda d: d,
        )

    def test_dates_fails_when_no_arguments_are_provided(self):
        self.assertRaises(
            TypeError,
            Article.objects.dates,
        )

    def test_dates_fails_when_given_invalid_field_argument(self):
        six.assertRaisesRegex(
            self,
            FieldError,
            "Cannot resolve keyword u?'invalid_field' into field. Choices are: "
            "categories, comments, id, pub_date, title",
            Article.objects.dates,
            "invalid_field",
            "year",
        )

    def test_dates_fails_when_given_invalid_kind_argument(self):
        six.assertRaisesRegex(
            self,
            AssertionError,
            "'kind' must be one of 'year', 'month' or 'day'.",
            Article.objects.dates,
            "pub_date",
            "bad_kind",
        )

    def test_dates_fails_when_given_invalid_order_argument(self):
        six.assertRaisesRegex(
            self,
            AssertionError,
            "'order' must be either 'ASC' or 'DESC'.",
            Article.objects.dates,
            "pub_date",
            "year",
            order="bad order",
        )
