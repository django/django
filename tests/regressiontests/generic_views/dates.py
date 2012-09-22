from __future__ import absolute_import

import time
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.unittest import skipUnless

from .models import Book, BookSigning

TZ_SUPPORT = hasattr(time, 'tzset')

# On OSes that don't provide tzset (Windows), we can't set the timezone
# in which the program runs. As a consequence, we must skip tests that
# don't enforce a specific timezone (with timezone.override or equivalent),
# or attempt to interpret naive datetimes in the default timezone.

requires_tz_support = skipUnless(TZ_SUPPORT,
        "This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.")


def _make_books(n, base_date):
    for i in range(n):
        b = Book.objects.create(
            name='Book %d' % i,
            slug='book-%d' % i,
            pages=100+i,
            pubdate=base_date - datetime.timedelta(days=i))

class ArchiveIndexViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'


    def test_archive_view(self):
        res = self.client.get('/dates/books/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'year', 'DESC')))
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()))
        self.assertTemplateUsed(res, 'generic_views/book_archive.html')

    def test_archive_view_context_object_name(self):
        res = self.client.get('/dates/books/context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'year', 'DESC')))
        self.assertEqual(list(res.context['thingies']), list(Book.objects.all()))
        self.assertFalse('latest' in res.context)
        self.assertTemplateUsed(res, 'generic_views/book_archive.html')

    def test_empty_archive_view(self):
        Book.objects.all().delete()
        res = self.client.get('/dates/books/')
        self.assertEqual(res.status_code, 404)

    def test_allow_empty_archive_view(self):
        Book.objects.all().delete()
        res = self.client.get('/dates/books/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [])
        self.assertTemplateUsed(res, 'generic_views/book_archive.html')

    def test_archive_view_template(self):
        res = self.client.get('/dates/books/template_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'year', 'DESC')))
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()))
        self.assertTemplateUsed(res, 'generic_views/list.html')

    def test_archive_view_template_suffix(self):
        res = self.client.get('/dates/books/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'year', 'DESC')))
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()))
        self.assertTemplateUsed(res, 'generic_views/book_detail.html')

    def test_archive_view_invalid(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/dates/books/invalid/')

    def test_archive_view_by_month(self):
        res = self.client.get('/dates/books/by_month/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'month', 'DESC')))

    def test_paginated_archive_view(self):
        _make_books(20, base_date=datetime.date.today())
        res = self.client.get('/dates/books/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(Book.objects.dates('pubdate', 'year', 'DESC')))
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()[0:10]))
        self.assertTemplateUsed(res, 'generic_views/book_archive.html')

        res = self.client.get('/dates/books/paginated/?page=2')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 2)
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()[10:20]))

    def test_paginated_archive_view_does_not_load_entire_table(self):
        # Regression test for #18087
        _make_books(20, base_date=datetime.date.today())
        # 1 query for years list + 1 query for books
        with self.assertNumQueries(2):
            self.client.get('/dates/books/')
        # same as above + 1 query to test if books exist + 1 query to count them
        with self.assertNumQueries(4):
            self.client.get('/dates/books/paginated/')

    def test_no_duplicate_query(self):
        # Regression test for #18354
        with self.assertNumQueries(2):
            self.client.get('/dates/books/reverse/')

    def test_datetime_archive_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = self.client.get('/dates/booksignings/')
        self.assertEqual(res.status_code, 200)

    @requires_tz_support
    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_archive_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/')
        self.assertEqual(res.status_code, 200)

    def test_date_list_order(self):
        """date_list should be sorted descending in index"""
        _make_books(5, base_date=datetime.date(2011, 12, 25))
        res = self.client.get('/dates/books/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), list(reversed(sorted(res.context['date_list']))))


class YearArchiveViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_year_view(self):
        res = self.client.get('/dates/books/2008/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2008, 10, 1)])
        self.assertEqual(res.context['year'], datetime.date(2008, 1, 1))
        self.assertTemplateUsed(res, 'generic_views/book_archive_year.html')

        # Since allow_empty=False, next/prev years must be valid (#7164)
        self.assertEqual(res.context['next_year'], None)
        self.assertEqual(res.context['previous_year'], datetime.date(2006, 1, 1))

    def test_year_view_make_object_list(self):
        res = self.client.get('/dates/books/2006/make_object_list/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2006, 5, 1)])
        self.assertEqual(list(res.context['book_list']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertTemplateUsed(res, 'generic_views/book_archive_year.html')

    def test_year_view_empty(self):
        res = self.client.get('/dates/books/1999/')
        self.assertEqual(res.status_code, 404)
        res = self.client.get('/dates/books/1999/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [])
        self.assertEqual(list(res.context['book_list']), [])

        # Since allow_empty=True, next/prev are allowed to be empty years (#7164)
        self.assertEqual(res.context['next_year'], datetime.date(2000, 1, 1))
        self.assertEqual(res.context['previous_year'], datetime.date(1998, 1, 1))

    def test_year_view_allow_future(self):
        # Create a new book in the future
        year = datetime.date.today().year + 1
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=datetime.date(year, 1, 1))
        res = self.client.get('/dates/books/%s/' % year)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/allow_empty/' % year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), [])

        res = self.client.get('/dates/books/%s/allow_future/' % year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(year, 1, 1)])

    def test_year_view_paginated(self):
        res = self.client.get('/dates/books/2006/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertTemplateUsed(res, 'generic_views/book_archive_year.html')

    def test_year_view_invalid_pattern(self):
        res = self.client.get('/dates/books/no_year/')
        self.assertEqual(res.status_code, 404)

    def test_no_duplicate_query(self):
        # Regression test for #18354
        with self.assertNumQueries(4):
            self.client.get('/dates/books/2008/reverse/')

    def test_datetime_year_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = self.client.get('/dates/booksignings/2008/')
        self.assertEqual(res.status_code, 200)

    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_year_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/2008/')
        self.assertEqual(res.status_code, 200)

    def test_date_list_order(self):
        """date_list should be sorted ascending in year view"""
        _make_books(10, base_date=datetime.date(2011, 12, 25))
        res = self.client.get('/dates/books/2011/')
        self.assertEqual(list(res.context['date_list']), list(sorted(res.context['date_list'])))


class MonthArchiveViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_month_view(self):
        res = self.client.get('/dates/books/2008/oct/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/book_archive_month.html')
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2008, 10, 1)])
        self.assertEqual(list(res.context['book_list']),
                         list(Book.objects.filter(pubdate=datetime.date(2008, 10, 1))))
        self.assertEqual(res.context['month'], datetime.date(2008, 10, 1))

        # Since allow_empty=False, next/prev months must be valid (#7164)
        self.assertEqual(res.context['next_month'], None)
        self.assertEqual(res.context['previous_month'], datetime.date(2006, 5, 1))

    def test_month_view_allow_empty(self):
        # allow_empty = False, empty month
        res = self.client.get('/dates/books/2000/jan/')
        self.assertEqual(res.status_code, 404)

        # allow_empty = True, empty month
        res = self.client.get('/dates/books/2000/jan/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [])
        self.assertEqual(list(res.context['book_list']), [])
        self.assertEqual(res.context['month'], datetime.date(2000, 1, 1))

        # Since allow_empty=True, next/prev are allowed to be empty months (#7164)
        self.assertEqual(res.context['next_month'], datetime.date(2000, 2, 1))
        self.assertEqual(res.context['previous_month'], datetime.date(1999, 12, 1))

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = datetime.date.today().strftime('/dates/books/%Y/%b/allow_empty/').lower()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_month'], None)

    def test_month_view_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60)).replace(day=1)
        urlbit = future.strftime('%Y/%b').lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = self.client.get('/dates/books/%s/' % urlbit)
        self.assertEqual(res.status_code, 404)

        # allow_future = True, valid future month
        res = self.client.get('/dates/books/%s/allow_future/' % urlbit)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['date_list'][0].date(), b.pubdate)
        self.assertEqual(list(res.context['book_list']), [b])
        self.assertEqual(res.context['month'], future)

        # Since allow_future = True but not allow_empty, next/prev are not
        # allowed to be empty months (#7164)
        self.assertEqual(res.context['next_month'], None)
        self.assertEqual(res.context['previous_month'], datetime.date(2008, 10, 1))

        # allow_future, but not allow_empty, with a current month. So next
        # should be in the future (yup, #7164, again)
        res = self.client.get('/dates/books/2008/oct/allow_future/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_month'], future)
        self.assertEqual(res.context['previous_month'], datetime.date(2006, 5, 1))

    def test_month_view_paginated(self):
        res = self.client.get('/dates/books/2008/oct/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), list(Book.objects.filter(pubdate__year=2008, pubdate__month=10)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__year=2008, pubdate__month=10)))
        self.assertTemplateUsed(res, 'generic_views/book_archive_month.html')

    def test_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/')
        self.assertEqual(res.status_code, 200)

    def test_month_view_invalid_pattern(self):
        res = self.client.get('/dates/books/2007/no_month/')
        self.assertEqual(res.status_code, 404)

    def test_previous_month_without_content(self):
        "Content can exist on any day of the previous month. Refs #14711"
        self.pubdate_list = [
            datetime.date(2010, month, day)
            for month,day in ((9,1), (10,2), (11,3))
        ]
        for pubdate in self.pubdate_list:
            name = str(pubdate)
            Book.objects.create(name=name, slug=name, pages=100, pubdate=pubdate)

        res = self.client.get('/dates/books/2010/nov/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['previous_month'], datetime.date(2010,10,1))
        # The following test demonstrates the bug
        res = self.client.get('/dates/books/2010/nov/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['previous_month'], datetime.date(2010,10,1))
        # The bug does not occur here because a Book with pubdate of Sep 1 exists
        res = self.client.get('/dates/books/2010/oct/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['previous_month'], datetime.date(2010,9,1))

    def test_datetime_month_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 2, 1, 12, 0))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 6, 3, 12, 0))
        res = self.client.get('/dates/booksignings/2008/apr/')
        self.assertEqual(res.status_code, 200)

    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_month_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 2, 1, 12, 0, tzinfo=timezone.utc))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 6, 3, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/2008/apr/')
        self.assertEqual(res.status_code, 200)

    def test_date_list_order(self):
        """date_list should be sorted ascending in month view"""
        _make_books(10, base_date=datetime.date(2011, 12, 25))
        res = self.client.get('/dates/books/2011/dec/')
        self.assertEqual(list(res.context['date_list']), list(sorted(res.context['date_list'])))


class WeekArchiveViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_week_view(self):
        res = self.client.get('/dates/books/2008/week/39/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/book_archive_week.html')
        self.assertEqual(res.context['book_list'][0], Book.objects.get(pubdate=datetime.date(2008, 10, 1)))
        self.assertEqual(res.context['week'], datetime.date(2008, 9, 28))

        # Since allow_empty=False, next/prev weeks must be valid
        self.assertEqual(res.context['next_week'], None)
        self.assertEqual(res.context['previous_week'], datetime.date(2006, 4, 30))

    def test_week_view_allow_empty(self):
        # allow_empty = False, empty week
        res = self.client.get('/dates/books/2008/week/12/')
        self.assertEqual(res.status_code, 404)

        # allow_empty = True, empty month
        res = self.client.get('/dates/books/2008/week/12/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), [])
        self.assertEqual(res.context['week'], datetime.date(2008, 3, 23))

        # Since allow_empty=True, next/prev are allowed to be empty weeks
        self.assertEqual(res.context['next_week'], datetime.date(2008, 3, 30))
        self.assertEqual(res.context['previous_week'], datetime.date(2008, 3, 16))

        # allow_empty but not allow_future: next_week should be empty
        url = datetime.date.today().strftime('/dates/books/%Y/week/%U/allow_empty/').lower()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_week'], None)

    def test_week_view_allow_future(self):
        # January 7th always falls in week 1, given Python's definition of week numbers
        future = datetime.date(datetime.date.today().year + 1, 1, 7)
        future_sunday = future - datetime.timedelta(days=(future.weekday() + 1) % 7)
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        res = self.client.get('/dates/books/%s/week/1/' % future.year)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/week/1/allow_future/' % future.year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), [b])
        self.assertEqual(res.context['week'], future_sunday)

        # Since allow_future = True but not allow_empty, next/prev are not
        # allowed to be empty weeks
        self.assertEqual(res.context['next_week'], None)
        self.assertEqual(res.context['previous_week'], datetime.date(2008, 9, 28))

        # allow_future, but not allow_empty, with a current week. So next
        # should be in the future
        res = self.client.get('/dates/books/2008/week/39/allow_future/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_week'], future_sunday)
        self.assertEqual(res.context['previous_week'], datetime.date(2006, 4, 30))

    def test_week_view_paginated(self):
        week_start = datetime.date(2008, 9, 28)
        week_end = week_start + datetime.timedelta(days=7)
        res = self.client.get('/dates/books/2008/week/39/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), list(Book.objects.filter(pubdate__gte=week_start, pubdate__lt=week_end)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__gte=week_start, pubdate__lt=week_end)))
        self.assertTemplateUsed(res, 'generic_views/book_archive_week.html')

    def test_week_view_invalid_pattern(self):
        res = self.client.get('/dates/books/2007/week/no_week/')
        self.assertEqual(res.status_code, 404)

    def test_week_start_Monday(self):
        # Regression for #14752
        res = self.client.get('/dates/books/2008/week/39/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['week'], datetime.date(2008, 9, 28))

        res = self.client.get('/dates/books/2008/week/39/monday/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['week'], datetime.date(2008, 9, 29))

    def test_datetime_week_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = self.client.get('/dates/booksignings/2008/week/13/')
        self.assertEqual(res.status_code, 200)

    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_week_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/2008/week/13/')
        self.assertEqual(res.status_code, 200)


class DayArchiveViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_day_view(self):
        res = self.client.get('/dates/books/2008/oct/01/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/book_archive_day.html')
        self.assertEqual(list(res.context['book_list']),
                         list(Book.objects.filter(pubdate=datetime.date(2008, 10, 1))))
        self.assertEqual(res.context['day'], datetime.date(2008, 10, 1))

        # Since allow_empty=False, next/prev days must be valid.
        self.assertEqual(res.context['next_day'], None)
        self.assertEqual(res.context['previous_day'], datetime.date(2006, 5, 1))

    def test_day_view_allow_empty(self):
        # allow_empty = False, empty month
        res = self.client.get('/dates/books/2000/jan/1/')
        self.assertEqual(res.status_code, 404)

        # allow_empty = True, empty month
        res = self.client.get('/dates/books/2000/jan/1/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), [])
        self.assertEqual(res.context['day'], datetime.date(2000, 1, 1))

        # Since it's allow empty, next/prev are allowed to be empty months (#7164)
        self.assertEqual(res.context['next_day'], datetime.date(2000, 1, 2))
        self.assertEqual(res.context['previous_day'], datetime.date(1999, 12, 31))

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = datetime.date.today().strftime('/dates/books/%Y/%b/%d/allow_empty/').lower()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_day'], None)

    def test_day_view_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60))
        urlbit = future.strftime('%Y/%b/%d').lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = self.client.get('/dates/books/%s/' % urlbit)
        self.assertEqual(res.status_code, 404)

        # allow_future = True, valid future month
        res = self.client.get('/dates/books/%s/allow_future/' % urlbit)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), [b])
        self.assertEqual(res.context['day'], future)

        # allow_future but not allow_empty, next/prev must be valid
        self.assertEqual(res.context['next_day'], None)
        self.assertEqual(res.context['previous_day'], datetime.date(2008, 10, 1))

        # allow_future, but not allow_empty, with a current month.
        res = self.client.get('/dates/books/2008/oct/01/allow_future/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_day'], future)
        self.assertEqual(res.context['previous_day'], datetime.date(2006, 5, 1))

        # allow_future for yesterday, next_day is today (#17192)
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        res = self.client.get('/dates/books/%s/allow_empty_and_future/'
                              % yesterday.strftime('%Y/%b/%d').lower())
        self.assertEqual(res.context['next_day'], today)

    def test_day_view_paginated(self):
        res = self.client.get('/dates/books/2008/oct/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['book_list']), list(Book.objects.filter(pubdate__year=2008, pubdate__month=10, pubdate__day=1)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__year=2008, pubdate__month=10, pubdate__day=1)))
        self.assertTemplateUsed(res, 'generic_views/book_archive_day.html')

    def test_next_prev_context(self):
        res = self.client.get('/dates/books/2008/oct/01/')
        self.assertEqual(res.content, b"Archive for Oct. 1, 2008. Previous day is May 1, 2006")

    def test_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/01/')
        self.assertEqual(res.status_code, 200)

    def test_day_view_invalid_pattern(self):
        res = self.client.get('/dates/books/2007/oct/no_day/')
        self.assertEqual(res.status_code, 404)

    def test_today_view(self):
        res = self.client.get('/dates/books/today/')
        self.assertEqual(res.status_code, 404)
        res = self.client.get('/dates/books/today/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['day'], datetime.date.today())

    def test_datetime_day_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = self.client.get('/dates/booksignings/2008/apr/2/')
        self.assertEqual(res.status_code, 200)

    @requires_tz_support
    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_day_view(self):
        bs = BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/2008/apr/2/')
        self.assertEqual(res.status_code, 200)
        # 2008-04-02T00:00:00+03:00 (beginning of day) > 2008-04-01T22:00:00+00:00 (book signing event date)
        bs.event_date = datetime.datetime(2008, 4, 1, 22, 0, tzinfo=timezone.utc)
        bs.save()
        res = self.client.get('/dates/booksignings/2008/apr/2/')
        self.assertEqual(res.status_code, 200)
        # 2008-04-03T00:00:00+03:00 (end of day) > 2008-04-02T22:00:00+00:00 (book signing event date)
        bs.event_date = datetime.datetime(2008, 4, 2, 22, 0, tzinfo=timezone.utc)
        bs.save()
        res = self.client.get('/dates/booksignings/2008/apr/2/')
        self.assertEqual(res.status_code, 404)


class DateDetailViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_date_detail_by_pk(self):
        res = self.client.get('/dates/books/2008/oct/01/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Book.objects.get(pk=1))
        self.assertEqual(res.context['book'], Book.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/book_detail.html')

    def test_date_detail_by_slug(self):
        res = self.client.get('/dates/books/2006/may/01/byslug/dreaming-in-code/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], Book.objects.get(slug='dreaming-in-code'))

    def test_date_detail_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/01/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], Book.objects.get(pk=1))

    def test_date_detail_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60))
        urlbit = future.strftime('%Y/%b/%d').lower()
        b = Book.objects.create(name="The New New Testement", slug="new-new", pages=600, pubdate=future)

        res = self.client.get('/dates/books/%s/new-new/' % urlbit)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/%s/allow_future/' % (urlbit, b.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], b)
        self.assertTemplateUsed(res, 'generic_views/book_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, "/dates/books/2008/oct/01/nopk/")

    def test_get_object_custom_queryset(self):
        """
        Ensure that custom querysets are used when provided to
        BaseDateDetailView.get_object()
        Refs #16918.
        """
        res = self.client.get(
            '/dates/books/get_object_custom_queryset/2006/may/01/2/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Book.objects.get(pk=2))
        self.assertEqual(res.context['book'], Book.objects.get(pk=2))
        self.assertTemplateUsed(res, 'generic_views/book_detail.html')

        res = self.client.get(
            '/dates/books/get_object_custom_queryset/2008/oct/01/1/')
        self.assertEqual(res.status_code, 404)

    def test_datetime_date_detail(self):
        bs = BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = self.client.get('/dates/booksignings/2008/apr/2/%d/' % bs.pk)
        self.assertEqual(res.status_code, 200)

    @requires_tz_support
    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Nairobi')
    def test_aware_datetime_date_detail(self):
        bs = BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0, tzinfo=timezone.utc))
        res = self.client.get('/dates/booksignings/2008/apr/2/%d/' % bs.pk)
        self.assertEqual(res.status_code, 200)
        # 2008-04-02T00:00:00+03:00 (beginning of day) > 2008-04-01T22:00:00+00:00 (book signing event date)
        bs.event_date = datetime.datetime(2008, 4, 1, 22, 0, tzinfo=timezone.utc)
        bs.save()
        res = self.client.get('/dates/booksignings/2008/apr/2/%d/' % bs.pk)
        self.assertEqual(res.status_code, 200)
        # 2008-04-03T00:00:00+03:00 (end of day) > 2008-04-02T22:00:00+00:00 (book signing event date)
        bs.event_date = datetime.datetime(2008, 4, 2, 22, 0, tzinfo=timezone.utc)
        bs.save()
        res = self.client.get('/dates/booksignings/2008/apr/2/%d/' % bs.pk)
        self.assertEqual(res.status_code, 404)
