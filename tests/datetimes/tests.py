import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Article, Category, Comment


class DateTimesTests(TestCase):
    def test_related_model_traverse(self):
        a1 = Article.objects.create(
            title="First one",
            publication_date=datetime.datetime(2005, 7, 28, 9, 0, 0),
        )
        a2 = Article.objects.create(
            title="Another one",
            publication_date=datetime.datetime(2010, 7, 28, 10, 0, 0),
        )
        a3 = Article.objects.create(
            title="Third one, in the first day",
            publication_date=datetime.datetime(2005, 7, 28, 17, 0, 0),
        )

        a1.comments.create(
            text="Im the HULK!",
            publication_date=datetime.datetime(2005, 7, 28, 9, 30, 0),
        )
        a1.comments.create(
            text="HULK SMASH!",
            publication_date=datetime.datetime(2005, 7, 29, 1, 30, 0),
        )
        a2.comments.create(
            text="LMAO",
            publication_date=datetime.datetime(2010, 7, 28, 10, 10, 10),
        )
        a3.comments.create(
            text="+1",
            publication_date=datetime.datetime(2005, 8, 29, 10, 10, 10),
        )

        c = Category.objects.create(name="serious-news")
        c.articles.add(a1, a3)

        self.assertSequenceEqual(
            Comment.objects.datetimes("article__publication_date", "year"), [
                datetime.datetime(2005, 1, 1),
                datetime.datetime(2010, 1, 1),
            ],
        )
        self.assertSequenceEqual(
            Comment.objects.datetimes("article__publication_date", "month"), [
                datetime.datetime(2005, 7, 1),
                datetime.datetime(2010, 7, 1),
            ],
        )
        self.assertSequenceEqual(
            Comment.objects.datetimes("article__publication_date", "day"), [
                datetime.datetime(2005, 7, 28),
                datetime.datetime(2010, 7, 28),
            ],
        )
        self.assertSequenceEqual(
            Article.objects.datetimes("comments__publication_date", "day"), [
                datetime.datetime(2005, 7, 28),
                datetime.datetime(2005, 7, 29),
                datetime.datetime(2005, 8, 29),
                datetime.datetime(2010, 7, 28),
            ],
        )
        self.assertQuerysetEqual(
            Article.objects.datetimes("comments__approval_date", "day"), []
        )
        self.assertSequenceEqual(
            Category.objects.datetimes("articles__publication_date", "day"), [
                datetime.datetime(2005, 7, 28),
            ],
        )

    @override_settings(USE_TZ=True)
    def test_21432(self):
        now = timezone.localtime(timezone.now().replace(microsecond=0))
        Article.objects.create(title="First one", publication_date=now)
        qs = Article.objects.datetimes('publication_date', 'second')
        self.assertEqual(qs[0], now)

    def test_datetimes_returns_available_dates_for_given_scope_and_given_field(self):
        publication_dates = [
            datetime.datetime(2005, 7, 28, 12, 15),
            datetime.datetime(2005, 7, 29, 2, 15),
            datetime.datetime(2005, 7, 30, 5, 15),
            datetime.datetime(2005, 7, 31, 19, 15)]
        for i, publication_date in enumerate(publication_dates):
            Article(publication_date=publication_date, title='title #{}'.format(i)).save()

        self.assertQuerysetEqual(
            Article.objects.datetimes('publication_date', 'year'),
            ["datetime.datetime(2005, 1, 1, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('publication_date', 'month'),
            ["datetime.datetime(2005, 7, 1, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('publication_date', 'day'),
            ["datetime.datetime(2005, 7, 28, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 31, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('publication_date', 'day', order='ASC'),
            ["datetime.datetime(2005, 7, 28, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 31, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('publication_date', 'day', order='DESC'),
            ["datetime.datetime(2005, 7, 31, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 28, 0, 0)"])

    def test_datetimes_has_lazy_iterator(self):
        publication_dates = [
            datetime.datetime(2005, 7, 28, 12, 15),
            datetime.datetime(2005, 7, 29, 2, 15),
            datetime.datetime(2005, 7, 30, 5, 15),
            datetime.datetime(2005, 7, 31, 19, 15)]
        for i, publication_date in enumerate(publication_dates):
            Article(publication_date=publication_date, title='title #{}'.format(i)).save()
        # Use iterator() with datetimes() to return a generator that lazily
        # requests each result one at a time, to save memory.
        dates = []
        with self.assertNumQueries(0):
            article_datetimes_iterator = Article.objects.datetimes('publication_date', 'day', order='DESC').iterator()

        with self.assertNumQueries(1):
            for article in article_datetimes_iterator:
                dates.append(article)
        self.assertEqual(dates, [
            datetime.datetime(2005, 7, 31, 0, 0),
            datetime.datetime(2005, 7, 30, 0, 0),
            datetime.datetime(2005, 7, 29, 0, 0),
            datetime.datetime(2005, 7, 28, 0, 0)])

    def test_datetimes_disallows_date_fields(self):
        dt = datetime.datetime(2005, 7, 28, 12, 15)
        Article.objects.create(publication_date=dt, published_on=dt.date(), title="Don't put dates into datetime functions!")
        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'published_on' to DateTimeField"):
            list(Article.objects.datetimes('published_on', 'second'))
