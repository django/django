from __future__ import absolute_import

import datetime

from django.test import TestCase

from .models import Article, Comment, Category


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
