from __future__ import absolute_import

import datetime

try:
    import pytz
except ImportError:
    pytz = None

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.unittest import skipIf


from .models import Article, Comment, Category


class DateTimesTests(TestCase):
    def test_related_model_traverse(self):
        a1 = Article.objects.create(
            title="First one",
            pub_date=datetime.datetime(2005, 7, 28, 9, 0, 0),
        )
        a2 = Article.objects.create(
            title="Another one",
            pub_date=datetime.datetime(2010, 7, 28, 10, 0, 0),
        )
        a3 = Article.objects.create(
            title="Third one, in the first day",
            pub_date=datetime.datetime(2005, 7, 28, 17, 0, 0),
        )

        a1.comments.create(
            text="Im the HULK!",
            pub_date=datetime.datetime(2005, 7, 28, 9, 30, 0),
        )
        a1.comments.create(
            text="HULK SMASH!",
            pub_date=datetime.datetime(2005, 7, 29, 1, 30, 0),
        )
        a2.comments.create(
            text="LMAO",
            pub_date=datetime.datetime(2010, 7, 28, 10, 10, 10),
        )
        a3.comments.create(
            text="+1",
            pub_date=datetime.datetime(2005, 8, 29, 10, 10, 10),
        )

        c = Category.objects.create(name="serious-news")
        c.articles.add(a1, a3)

        self.assertQuerysetEqual(
            Comment.objects.datetimes("article__pub_date", "year"), [
                datetime.datetime(2005, 1, 1),
                datetime.datetime(2010, 1, 1),
            ],
            lambda d: d,
        )
        self.assertQuerysetEqual(
            Comment.objects.datetimes("article__pub_date", "month"), [
                datetime.datetime(2005, 7, 1),
                datetime.datetime(2010, 7, 1),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Comment.objects.datetimes("article__pub_date", "day"), [
                datetime.datetime(2005, 7, 28),
                datetime.datetime(2010, 7, 28),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Article.objects.datetimes("comments__pub_date", "day"), [
                datetime.datetime(2005, 7, 28),
                datetime.datetime(2005, 7, 29),
                datetime.datetime(2005, 8, 29),
                datetime.datetime(2010, 7, 28),
            ],
            lambda d: d
        )
        self.assertQuerysetEqual(
            Article.objects.datetimes("comments__approval_date", "day"), []
        )
        self.assertQuerysetEqual(
            Category.objects.datetimes("articles__pub_date", "day"), [
                datetime.datetime(2005, 7, 28),
            ],
            lambda d: d,
        )

    @skipIf(pytz is None, "this test requires pytz")
    @override_settings(USE_TZ=True)
    def test_21432(self):
        now = timezone.localtime(timezone.now().replace(microsecond=0))
        Article.objects.create(title="First one", pub_date=now)
        qs = Article.objects.datetimes('pub_date', 'second')
        self.assertEqual(qs[0], now)
