from django.template import loader, RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.core.xheaders import populate_xheaders
from django.http import Http404, HttpResponse
import datetime, time

def archive_index(request, queryset, date_field, num_latest=15,
        template_name=None, template_loader=loader,
        extra_context={}, allow_empty=False, context_processors=None):
    """
    Generic top-level archive of date-based objects.

    Templates: ``<app_label>/<model_name>_archive.html``
    Context:
        date_list
            List of years
        latest
            Latest N (defaults to 15) objects by date
    """
    model = queryset.model
    queryset = queryset.filter(**{'%s__lte' % date_field: datetime.datetime.now()})
    date_list = queryset.dates(date_field, 'year')[::-1]
    if not date_list and not allow_empty:
        raise Http404, "No %s available" % model._meta.verbose_name

    if date_list and num_latest:
        latest = queryset.order_by('-'+date_field)[:num_latest]
    else:
        latest = None

    if not template_name:
        template_name = "%s/%s_archive.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'date_list' : date_list,
        'latest' : latest,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_year(request, year, queryset, date_field, template_name=None,
        template_loader=loader, extra_context={}, allow_empty=False,
        context_processors=None):
    """
    Generic yearly archive view.

    Templates: ``<app_label>/<model_name>_archive_year.html``
    Context:
        date_list
            List of months in this year with objects
        year
            This year
    """
    model = queryset.model
    now = datetime.datetime.now()

    lookup_kwargs = {'%s__year' % date_field: year}

    # Only bother to check current date if the year isn't in the past.
    if int(year) >= now.year:
        lookup_kwargs['%s__lte' % date_field] = now
    date_list = queryset.filter(**lookup_kwargs).dates(date_field, 'month')
    if not date_list and not allow_empty:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_year.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'date_list': date_list,
        'year': year,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_month(request, year, month, queryset, date_field,
        month_format='%b', template_name=None, template_loader=loader,
        extra_context={}, allow_empty=False, context_processors=None,
        template_object_name='object'):
    """
    Generic monthly archive view.

    Templates: ``<app_label>/<model_name>_archive_month.html``
    Context:
        month:
            (date) this month
        next_month:
            (date) the first day of the next month, or None if the next month is in the future
        previous_month:
            (date) the first day of the previous month
        object_list:
            list of objects published in the given month
    """
    try:
        date = datetime.date(*time.strptime(year+month, '%Y'+month_format)[:3])
    except ValueError:
        raise Http404

    model = queryset.model
    now = datetime.datetime.now()

    # Calculate first and last day of month, for use in a date-range lookup.
    first_day = date.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1)
    lookup_kwargs = {'%s__range' % date_field: (first_day, last_day)}

    # Only bother to check current date if the month isn't in the past.
    if last_day >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    object_list = queryset.filter(**lookup_kwargs)
    if not object_list and not allow_empty:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_month.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        '%s_list' % template_object_name: object_list,
        'month': date,
        'next_month': (last_day < datetime.date.today()) and (last_day + datetime.timedelta(days=1)) or None,
        'previous_month': first_day - datetime.timedelta(days=1),
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_week(request, year, week, queryset, date_field,
        template_name=None, template_loader=loader,
        extra_context={}, allow_empty=True, context_processors=None,
        template_object_name='object'):
    """
    Generic weekly archive view.

    Templates: ``<app_label>/<model_name>_archive_week.html``
    Context:
        week:
            (date) this week
        object_list:
            list of objects published in the given week
    """
    try:
        date = datetime.date(*time.strptime(year+'-0-'+week, '%Y-%w-%U')[:3])
    except ValueError:
        raise Http404

    model = queryset.model
    now = datetime.datetime.now()

    # Calculate first and last day of week, for use in a date-range lookup.
    first_day = date
    last_day = date + datetime.timedelta(days=7)
    lookup_kwargs = {'%s__range' % date_field: (first_day, last_day)}

    # Only bother to check current date if the week isn't in the past.
    if last_day >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    object_list = queryset.filter(**lookup_kwargs)
    if not object_list and not allow_empty:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_week.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        '%s_list' % template_object_name: object_list,
        'week': date,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_day(request, year, month, day, queryset, date_field,
        month_format='%b', day_format='%d', template_name=None,
        template_loader=loader, extra_context={}, allow_empty=False,
        context_processors=None, template_object_name='object'):
    """
    Generic daily archive view.

    Templates: ``<app_label>/<model_name>_archive_day.html``
    Context:
        object_list:
            list of objects published that day
        day:
            (datetime) the day
        previous_day
            (datetime) the previous day
        next_day
            (datetime) the next day, or None if the current day is today
    """
    try:
        date = datetime.date(*time.strptime(year+month+day, '%Y'+month_format+day_format)[:3])
    except ValueError:
        raise Http404

    model = queryset.model
    now = datetime.datetime.now()

    lookup_kwargs = {
        '%s__range' % date_field: (datetime.datetime.combine(date, datetime.time.min), datetime.datetime.combine(date, datetime.time.max)),
    }

    # Only bother to check current date if the date isn't in the past.
    if date >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    object_list = queryset.filter(**lookup_kwargs)
    if not allow_empty and not object_list:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_day.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        '%s_list' % template_object_name: object_list,
        'day': date,
        'previous_day': date - datetime.timedelta(days=1),
        'next_day': (date < datetime.date.today()) and (date + datetime.timedelta(days=1)) or None,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_today(request, **kwargs):
    """
    Generic daily archive view for today. Same as archive_day view.
    """
    today = datetime.date.today()
    kwargs.update({
        'year': str(today.year),
        'month': today.strftime('%b').lower(),
        'day': str(today.day),
    })
    return archive_day(request, **kwargs)

def object_detail(request, year, month, day, queryset, date_field,
        month_format='%b', day_format='%d', object_id=None, slug=None,
        slug_field=None, template_name=None, template_name_field=None,
        template_loader=loader, extra_context={}, context_processors=None,
        template_object_name='object'):
    """
    Generic detail view from year/month/day/slug or year/month/day/id structure.

    Templates: ``<app_label>/<model_name>_detail.html``
    Context:
        object:
            the object to be detailed
    """
    try:
        date = datetime.date(*time.strptime(year+month+day, '%Y'+month_format+day_format)[:3])
    except ValueError:
        raise Http404

    model = queryset.model
    now = datetime.datetime.now()

    lookup_kwargs = {
        '%s__range' % date_field: (datetime.datetime.combine(date, datetime.time.min), datetime.datetime.combine(date, datetime.time.max)),
    }

    # Only bother to check current date if the date isn't in the past.
    if date >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError, "Generic detail view must be called with either an object_id or a slug/slugfield"
    try:
        obj = queryset.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, "No %s found for" % model._meta.verbose_name
    if not template_name:
        template_name = "%s/%s_detail.html" % (model._meta.app_label, model._meta.object_name.lower())
    if template_name_field:
        template_name_list = [getattr(obj, template_name_field), template_name]
        t = template_loader.select_template(template_name_list)
    else:
        t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        template_object_name: obj,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.name))
    return response
