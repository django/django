import time
import datetime
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.views.generic.base import View
from django.views.generic.detail import BaseDetailView, SingleObjectTemplateResponseMixin
from django.views.generic.list import MultipleObjectMixin, MultipleObjectTemplateResponseMixin


class YearMixin(object):
    year_format = '%Y'
    year = None

    def get_year_format(self):
        """
        Get a year format string in strptime syntax to be used to parse the
        year from url variables.
        """
        return self.year_format

    def get_year(self):
        "Return the year for which this view should display data"
        year = self.year
        if year is None:
            try:
                year = self.kwargs['year']
            except KeyError:
                try:
                    year = self.request.GET['year']
                except KeyError:
                    raise Http404("No year specified")
        return year


class MonthMixin(object):
    month_format = '%b'
    month = None

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

    def get_month(self):
        "Return the month for which this view should display data"
        month = self.month
        if month is None:
            try:
                month = self.kwargs['month']
            except KeyError:
                try:
                    month = self.request.GET['month']
                except KeyError:
                    raise Http404("No month specified")
        return month

    def get_next_month(self, date):
        """
        Get the next valid month.
        """
        first_day, last_day = _month_bounds(date)
        next = (last_day + datetime.timedelta(days=1)).replace(day=1)
        return _get_next_prev_month(self, next, is_previous=False, use_first_day=True)

    def get_previous_month(self, date):
        """
        Get the previous valid month.
        """
        first_day, last_day = _month_bounds(date)
        prev = (first_day - datetime.timedelta(days=1)).replace(day=1)
        return _get_next_prev_month(self, prev, is_previous=True, use_first_day=True)


class DayMixin(object):
    day_format = '%d'
    day = None

    def get_day_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.day_format

    def get_day(self):
        "Return the day for which this view should display data"
        day = self.day
        if day is None:
            try:
                day = self.kwargs['day']
            except KeyError:
                try:
                    day = self.request.GET['day']
                except KeyError:
                    raise Http404("No day specified")
        return day

    def get_next_day(self, date):
        """
        Get the next valid day.
        """
        next = date + datetime.timedelta(days=1)
        return _get_next_prev_month(self, next, is_previous=False, use_first_day=False)

    def get_previous_day(self, date):
        """
        Get the previous valid day.
        """
        prev = date - datetime.timedelta(days=1)
        return _get_next_prev_month(self, prev, is_previous=True, use_first_day=False)


class WeekMixin(object):
    week_format = '%U'
    week = None

    def get_week_format(self):
        """
        Get a week format string in strptime syntax to be used to parse the
        week from url variables.
        """
        return self.week_format

    def get_week(self):
        "Return the week for which this view should display data"
        week = self.week
        if week is None:
            try:
                week = self.kwargs['week']
            except KeyError:
                try:
                    week = self.request.GET['week']
                except KeyError:
                    raise Http404("No week specified")
        return week


class DateMixin(object):
    """
    Mixin class for views manipulating date-based data.
    """
    date_field = None
    allow_future = False

    def get_date_field(self):
        """
        Get the name of the date field to be used to filter by.
        """
        if self.date_field is None:
            raise ImproperlyConfigured(u"%s.date_field is required." % self.__class__.__name__)
        return self.date_field

    def get_allow_future(self):
        """
        Returns `True` if the view should be allowed to display objects from
        the future.
        """
        return self.allow_future


class BaseDateListView(MultipleObjectMixin, DateMixin, View):
    """
    Abstract base class for date-based views display a list of objects.
    """
    allow_empty = False

    def get(self, request, *args, **kwargs):
        self.date_list, self.object_list, extra_context = self.get_dated_items()
        context = self.get_context_data(object_list=self.object_list,
                                        date_list=self.date_list)
        context.update(extra_context)
        return self.render_to_response(context)

    def get_dated_items(self):
        """
        Obtain the list of dates and itesm
        """
        raise NotImplemented('A DateView must provide an implementaiton of get_dated_items()')

    def get_dated_queryset(self, **lookup):
        """
        Get a queryset properly filtered according to `allow_future` and any
        extra lookup kwargs.
        """
        qs = self.get_queryset().filter(**lookup)
        date_field = self.get_date_field()
        allow_future = self.get_allow_future()
        allow_empty = self.get_allow_empty()

        if not allow_future:
            qs = qs.filter(**{'%s__lte' % date_field: datetime.datetime.now()})

        if not allow_empty and not qs:
            raise Http404(u"No %s available" % unicode(qs.model._meta.verbose_name_plural))

        return qs

    def get_date_list(self, queryset, date_type):
        """
        Get a date list by calling `queryset.dates()`, checking along the way
        for empty lists that aren't allowed.
        """
        date_field = self.get_date_field()
        allow_empty = self.get_allow_empty()

        date_list = queryset.dates(date_field, date_type)[::-1]
        if date_list is not None and not date_list and not allow_empty:
            raise Http404(u"No %s available" % unicode(qs.model._meta.verbose_name_plural))

        return date_list



    def get_context_data(self, **kwargs):
        """
        Get the context. Must return a Context (or subclass) instance.
        """
        items = kwargs.pop('object_list')
        context = super(BaseDateListView, self).get_context_data(object_list=items)
        context.update(kwargs)
        return context


class BaseArchiveIndexView(BaseDateListView):
    """
    Base class for archives of date-based items.

    Requires a response mixin.
    """
    context_object_name = 'latest'

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        qs = self.get_dated_queryset()
        date_list = self.get_date_list(qs, 'year')

        if date_list:
            object_list = qs.order_by('-'+self.get_date_field())
        else:
            object_list = qs.none()

        return (date_list, object_list, {})


class ArchiveIndexView(MultipleObjectTemplateResponseMixin, BaseArchiveIndexView):
    """
    Top-level archive of date-based items.
    """
    template_name_suffix = '_archive'


class BaseYearArchiveView(YearMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    make_object_list = False

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        # Yes, no error checking: the URLpattern ought to validate this; it's
        # an error if it doesn't.
        year = self.get_year()
        date_field = self.get_date_field()
        qs = self.get_dated_queryset(**{date_field+'__year': year})
        date_list = self.get_date_list(qs, 'month')

        if self.get_make_object_list():
            object_list = qs.order_by('-'+date_field)
        else:
            # We need this to be a queryset since parent classes introspect it
            # to find information about the model.
            object_list = qs.none()

        return (date_list, object_list, {'year': year})

    def get_make_object_list(self):
        """
        Return `True` if this view should contain the full list of objects in
        the given year.
        """
        return self.make_object_list


class YearArchiveView(MultipleObjectTemplateResponseMixin, BaseYearArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_year'


class BaseMonthArchiveView(YearMixin, MonthMixin, BaseDateListView):
    """
    List of objects published in a given year.
    """
    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format())

        # Construct a date-range lookup.
        first_day, last_day = _month_bounds(date)
        lookup_kwargs = {
            '%s__gte' % date_field: first_day,
            '%s__lt' % date_field: last_day,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)
        date_list = self.get_date_list(qs, 'day')

        return (date_list, qs, {
            'month': date,
            'next_month': self.get_next_month(date),
            'previous_month': self.get_previous_month(date),
        })



class MonthArchiveView(MultipleObjectTemplateResponseMixin, BaseMonthArchiveView):
    """
    List of objects published in a given year.
    """
    template_name_suffix = '_archive_month'


class BaseWeekArchiveView(YearMixin, WeekMixin, BaseDateListView):
    """
    List of objects published in a given week.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        week = self.get_week()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format(),
                                 '0', '%w',
                                 week, self.get_week_format())

        # Construct a date-range lookup.
        first_day = date
        last_day = date + datetime.timedelta(days=7)
        lookup_kwargs = {
            '%s__gte' % date_field: first_day,
            '%s__lt' % date_field: last_day,
        }

        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {'week': date})


class WeekArchiveView(MultipleObjectTemplateResponseMixin, BaseWeekArchiveView):
    """
    List of objects published in a given week.
    """
    template_name_suffix = '_archive_week'


class BaseDayArchiveView(YearMixin, MonthMixin, DayMixin, BaseDateListView):
    """
    List of objects published on a given day.
    """
    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()

        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        return self._get_dated_items(date)

    def _get_dated_items(self, date):
        """
        Do the actual heavy lifting of getting the dated items; this accepts a
        date object so that TodayArchiveView can be trivial.
        """
        date_field = self.get_date_field()

        field = self.get_queryset().model._meta.get_field(date_field)
        lookup_kwargs = _date_lookup_for_field(field, date)

        qs = self.get_dated_queryset(**lookup_kwargs)

        return (None, qs, {
            'day': date,
            'previous_day': self.get_previous_day(date),
            'next_day': self.get_next_day(date),
            'previous_month': self.get_previous_month(date),
            'next_month': self.get_next_month(date)
        })



class DayArchiveView(MultipleObjectTemplateResponseMixin, BaseDayArchiveView):
    """
    List of objects published on a given day.
    """
    template_name_suffix = "_archive_day"


class BaseTodayArchiveView(BaseDayArchiveView):
    """
    List of objects published today.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        return self._get_dated_items(datetime.date.today())


class TodayArchiveView(MultipleObjectTemplateResponseMixin, BaseTodayArchiveView):
    """
    List of objects published today.
    """
    template_name_suffix = "_archive_day"


class BaseDateDetailView(YearMixin, MonthMixin, DayMixin, DateMixin, BaseDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    def get_object(self, queryset=None, **kwargs):
        """
        Get the object this request displays.
        """
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()
        date = _date_from_string(year, self.get_year_format(),
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        qs = self.get_queryset()

        if not self.get_allow_future() and date > datetime.date.today():
            raise Http404("Future %s not available because %s.allow_future is False." % (
                qs.model._meta.verbose_name_plural, self.__class__.__name__)
            )

        # Filter down a queryset from self.queryset using the date from the
        # URL. This'll get passed as the queryset to DetailView.get_object,
        # which'll handle the 404
        date_field = self.get_date_field()
        field = qs.model._meta.get_field(date_field)
        lookup = _date_lookup_for_field(field, date)
        qs = qs.filter(**lookup)

        return super(BaseDetailView, self).get_object(queryset=qs, **kwargs)



class DateDetailView(SingleObjectTemplateResponseMixin, BaseDateDetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    template_name_suffix = '_detail'


def _date_from_string(year, year_format, month, month_format, day='', day_format='', delim='__'):
    """
    Helper: get a datetime.date object given a format string and a year,
    month, and possibly day; raise a 404 for an invalid date.
    """
    format = delim.join((year_format, month_format, day_format))
    datestr = delim.join((year, month, day))
    try:
        return datetime.date(*time.strptime(datestr, format)[:3])
    except ValueError:
        raise Http404(u"Invalid date string '%s' given format '%s'" % (datestr, format))

def _month_bounds(date):
    """
    Helper: return the first and last days of the month for the given date.
    """
    first_day = date.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1)

    return first_day, last_day

def _get_next_prev_month(generic_view, naive_result, is_previous, use_first_day):
    """
    Helper: Get the next or the previous valid date. The idea is to allow
    links on month/day views to never be 404s by never providing a date
    that'll be invalid for the given view.

    This is a bit complicated since it handles both next and previous months
    and days (for MonthArchiveView and DayArchiveView); hence the coupling to generic_view.

    However in essance the logic comes down to:

        * If allow_empty and allow_future are both true, this is easy: just
          return the naive result (just the next/previous day or month,
          reguardless of object existence.)

        * If allow_empty is true, allow_future is false, and the naive month
          isn't in the future, then return it; otherwise return None.

        * If allow_empty is false and allow_future is true, return the next
          date *that contains a valid object*, even if it's in the future. If
          there are no next objects, return None.

        * If allow_empty is false and allow_future is false, return the next
          date that contains a valid object. If that date is in the future, or
          if there are no next objects, return None.

    """
    date_field = generic_view.get_date_field()
    allow_empty = generic_view.get_allow_empty()
    allow_future = generic_view.get_allow_future()

    # If allow_empty is True the naive value will be valid
    if allow_empty:
        result = naive_result

    # Otherwise, we'll need to go to the database to look for an object
    # whose date_field is at least (greater than/less than) the given
    # naive result
    else:
        # Construct a lookup and an ordering depending on weather we're doing
        # a previous date or a next date lookup.
        if is_previous:
            lookup = {'%s__lte' % date_field: naive_result}
            ordering = '-%s' % date_field
        else:
            lookup = {'%s__gte' % date_field: naive_result}
            ordering = date_field

        qs = generic_view.get_queryset().filter(**lookup).order_by(ordering)

        # Snag the first object from the queryset; if it doesn't exist that
        # means there's no next/previous link available.
        try:
            result = getattr(qs[0], date_field)
        except IndexError:
            result = None

    # Convert datetimes to a dates
    if hasattr(result, 'date'):
        result = result.date()

    # For month views, we always want to have a date that's the first of the
    # month for consistancy's sake.
    if result and use_first_day:
        result = result.replace(day=1)

    # Check against future dates.
    if result and (allow_future or result < datetime.date.today()):
        return result
    else:
        return None

def _date_lookup_for_field(field, date):
    """
    Get the lookup kwargs for looking up a date against a given Field. If the
    date field is a DateTimeField, we can't just do filter(df=date) because
    that doesn't take the time into account. So we need to make a range lookup
    in those cases.
    """
    if isinstance(field, models.DateTimeField):
        date_range = (
            datetime.datetime.combine(date, datetime.time.min),
            datetime.datetime.combine(date, datetime.time.max)
        )
        return {'%s__range' % field.name: date_range}
    else:
        return {field.name: date}

