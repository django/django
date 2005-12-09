from django.core import template_loader
from django.core.exceptions import Http404, ObjectDoesNotExist
from django.core.extensions import DjangoContext as Context
from django.core.xheaders import populate_xheaders
from django.models import get_module
from django.utils.httpwrappers import HttpResponse
import datetime, time

def archive_index(request, app_label, module_name, date_field, num_latest=15,
                  template_name=None, template_loader=template_loader,
                  extra_lookup_kwargs={}, extra_context={}, allow_empty=False):
    """
    Generic top-level archive of date-based objects.

    Templates: ``<app_label>/<module_name>_archive``
    Context:
        date_list
            List of years
        latest
            Latest N (defaults to 15) objects by date
    """
    mod = get_module(app_label, module_name)
    lookup_kwargs = {'%s__lte' % date_field: datetime.datetime.now()}
    lookup_kwargs.update(extra_lookup_kwargs)
    date_list = getattr(mod, "get_%s_list" % date_field)('year', **lookup_kwargs)[::-1]
    if not date_list and not allow_empty:
        raise Http404("No %s.%s available" % (app_label, module_name))

    if date_list and num_latest:
        lookup_kwargs.update({
            'limit': num_latest,
            'order_by': ('-' + date_field,),
        })
        latest = mod.get_list(**lookup_kwargs)
    else:
        latest = None

    if not template_name:
        template_name = "%s/%s_archive" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'date_list' : date_list,
        'latest' : latest,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_year(request, year, app_label, module_name, date_field,
                 template_name=None, template_loader=template_loader,
                 extra_lookup_kwargs={}, extra_context={}):
    """
    Generic yearly archive view.

    Templates: ``<app_label>/<module_name>_archive_year``
    Context:
        date_list
            List of months in this year with objects
        year
            This year
    """
    mod = get_module(app_label, module_name)
    now = datetime.datetime.now()
    lookup_kwargs = {'%s__year' % date_field: year}
    # Only bother to check current date if the year isn't in the past.
    if int(year) >= now.year:
        lookup_kwargs['%s__lte' % date_field] = now
    lookup_kwargs.update(extra_lookup_kwargs)
    date_list = getattr(mod, "get_%s_list" % date_field)('month', **lookup_kwargs)
    if not date_list:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_year" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'date_list': date_list,
        'year': year,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_month(request, year, month, app_label, module_name, date_field,
                  month_format='%b', template_name=None, template_loader=template_loader,
                  extra_lookup_kwargs={}, extra_context={}):
    """
    Generic monthly archive view.

    Templates: ``<app_label>/<module_name>_archive_month``
    Context:
        month:
            this month
        object_list:
            list of objects published in the given month
    """
    try:
        date = datetime.date(*time.strptime(year+month, '%Y'+month_format)[:3])
    except ValueError:
        raise Http404

    mod = get_module(app_label, module_name)
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
    lookup_kwargs.update(extra_lookup_kwargs)
    object_list = mod.get_list(**lookup_kwargs)
    if not object_list:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_month" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'object_list': object_list,
        'month': date,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def archive_day(request, year, month, day, app_label, module_name, date_field,
                month_format='%b', day_format='%d', template_name=None,
                template_loader=template_loader, extra_lookup_kwargs={},
                extra_context={}, allow_empty=False):
    """
    Generic daily archive view.

    Templates: ``<app_label>/<module_name>_archive_day``
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

    mod = get_module(app_label, module_name)
    now = datetime.datetime.now()
    lookup_kwargs = {
        '%s__range' % date_field: (datetime.datetime.combine(date, datetime.time.min), datetime.datetime.combine(date, datetime.time.max)),
    }
    # Only bother to check current date if the date isn't in the past.
    if date >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    lookup_kwargs.update(extra_lookup_kwargs)
    object_list = mod.get_list(**lookup_kwargs)
    if not allow_empty and not object_list:
        raise Http404
    if not template_name:
        template_name = "%s/%s_archive_day" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    c = Context(request, {
        'object_list': object_list,
        'day': date,
        'previous_day': date - datetime.timedelta(days=1),
        'next_day': (date < datetime.date.today()) and (date + datetime.timedelta(days=1)) or None,
    })
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

def object_detail(request, year, month, day, app_label, module_name, date_field,
                  month_format='%b', day_format='%d', object_id=None, slug=None,
                  slug_field=None, template_name=None, template_name_field=None,
                  template_loader=template_loader, extra_lookup_kwargs={},
                  extra_context={}):
    """
    Generic detail view from year/month/day/slug or year/month/day/id structure.

    Templates: ``<app_label>/<module_name>_detail``
    Context:
        object:
            the object to be detailed
    """
    try:
        date = datetime.date(*time.strptime(year+month+day, '%Y'+month_format+day_format)[:3])
    except ValueError:
        raise Http404

    mod = get_module(app_label, module_name)
    now = datetime.datetime.now()
    lookup_kwargs = {
        '%s__range' % date_field: (datetime.datetime.combine(date, datetime.time.min), datetime.datetime.combine(date, datetime.time.max)),
    }
    # Only bother to check current date if the date isn't in the past.
    if date >= now.date():
        lookup_kwargs['%s__lte' % date_field] = now
    if object_id:
        lookup_kwargs['%s__exact' % mod.Klass._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic detail view must be called with either an object_id or a slug/slugfield")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404("%s.%s does not exist for %s" % (app_label, module_name, lookup_kwargs))
    if not template_name:
        template_name = "%s/%s_detail" % (app_label, module_name)
    if template_name_field:
        template_name_list = [getattr(object, template_name_field), template_name]
        t = template_loader.select_template(template_name_list)
    else:
        t = template_loader.get_template(template_name)
    c = Context(request, {
        'object': object,
    })
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, app_label, module_name, getattr(object, object._meta.pk.name))
    return response
