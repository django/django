# coding: utf-8
from django.test import TestCase
from datetime import datetime, date
from datetime import timedelta
from regressiontests.views.models import Article, Author, DateArticle

class ObjectDetailTest(TestCase):
    fixtures = ['testdata.json']
    def setUp(self):
        # Correct the date for the current article
        current_article = Article.objects.get(title="Current Article")
        current_article.date_created = datetime.now()
        current_article.save()

    def test_finds_past(self):
        "date_based.object_detail can view a page in the past"
        response = self.client.get('/views/date_based/object_detail/2001/01/01/old_article/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].title, "Old Article")

    def test_object_detail_finds_today(self):
        "date_based.object_detail can view a page from today"
        today_url = datetime.now().strftime('%Y/%m/%d')
        response = self.client.get('/views/date_based/object_detail/%s/current_article/' % today_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].title, "Current Article")

    def test_object_detail_ignores_future(self):
        "date_based.object_detail can view a page from the future, but only if allowed."
        response = self.client.get('/views/date_based/object_detail/3000/01/01/future_article/')
        self.assertEqual(response.status_code, 404)

    def test_object_detail_allowed_future_if_enabled(self):
        "date_based.object_detail can view a page from the future if explicitly allowed."
        response = self.client.get('/views/date_based/object_detail/3000/01/01/future_article/allow_future/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].title, "Future Article")

class MonthArchiveTest(TestCase):
    def test_archive_month_includes_only_month(self):
        "Regression for #3031: Archives around Feburary include only one month"
        author = Author(name="John Smith")
        author.save()

        # 2004 was a leap year, so it should be weird enough to not cheat
        first_second_of_feb = datetime(2004, 2, 1, 0, 0, 1)
        first_second_of_mar = datetime(2004, 3, 1, 0, 0, 1)
        two_seconds = timedelta(0, 2, 0)
        article = Article(title="example", author=author)

        article.date_created = first_second_of_feb
        article.save()
        response = self.client.get('/views/date_based/archive_month/2004/02/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_month'], date(2004, 3, 1))
        self.assertEqual(response.context['previous_month'], date(2004, 1, 1))

        article.date_created = first_second_of_feb-two_seconds
        article.save()
        response = self.client.get('/views/date_based/archive_month/2004/02/')
        self.assertEqual(response.status_code, 404)

        article.date_created = first_second_of_mar-two_seconds
        article.save()
        response = self.client.get('/views/date_based/archive_month/2004/02/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_month'], date(2004, 3, 1))
        self.assertEqual(response.context['previous_month'], date(2004, 1, 1))

        article.date_created = first_second_of_mar
        article.save()
        response = self.client.get('/views/date_based/archive_month/2004/02/')
        self.assertEqual(response.status_code, 404)

        article2 = DateArticle(title="example", author=author)

        article2.date_created = first_second_of_feb.date()
        article2.save()
        response = self.client.get('/views/date_based/datefield/archive_month/2004/02/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_month'], date(2004, 3, 1))
        self.assertEqual(response.context['previous_month'], date(2004, 1, 1))

        article2.date_created = (first_second_of_feb-two_seconds).date()
        article2.save()
        response = self.client.get('/views/date_based/datefield/archive_month/2004/02/')
        self.assertEqual(response.status_code, 404)

        article2.date_created = (first_second_of_mar-two_seconds).date()
        article2.save()
        response = self.client.get('/views/date_based/datefield/archive_month/2004/02/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_month'], date(2004, 3, 1))
        self.assertEqual(response.context['previous_month'], date(2004, 1, 1))

        article2.date_created = first_second_of_mar.date()
        article2.save()
        response = self.client.get('/views/date_based/datefield/archive_month/2004/02/')
        self.assertEqual(response.status_code, 404)

        now = datetime.now()
        prev_month = now.date().replace(day=1)
        if prev_month.month == 1:
            prev_month = prev_month.replace(year=prev_month.year-1, month=12)
        else:
            prev_month = prev_month.replace(month=prev_month.month-1)
        article2.date_created = now
        article2.save()
        response = self.client.get('/views/date_based/datefield/archive_month/%s/' % now.strftime('%Y/%m'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_month'], None)
        self.assertEqual(response.context['previous_month'], prev_month)

class DayArchiveTests(TestCase):

    def test_year_month_day_format(self):
        """
        Make sure day views don't get confused with numeric month formats (#7944)
        """
        author = Author.objects.create(name="John Smith")
        article = Article.objects.create(title="example", author=author, date_created=datetime(2004, 1, 21, 0, 0, 1))
        response = self.client.get('/views/date_based/archive_day/2004/1/21/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0], article)
