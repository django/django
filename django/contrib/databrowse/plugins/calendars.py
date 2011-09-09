from django import http
from django.db import models
from django.contrib.databrowse.datastructures import EasyModel
from django.contrib.databrowse.sites import DatabrowsePlugin
from django.shortcuts import render_to_response
from django.utils.text import capfirst
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.views.generic import dates
from django.utils import datetime_safe


class DateViewMixin(object):
    allow_empty = False
    allow_future = True
    root_url = None
    model = None
    field = None

    def get_context_data(self, **kwargs):
        context = super(DateViewMixin, self).get_context_data(**kwargs)
        context.update({
            'root_url': self.root_url,
            'model': self.model,
            'field': self.field
        })
        return context


class DayView(DateViewMixin, dates.DayArchiveView):
    template_name = 'databrowse/calendar_day.html'


class MonthView(DateViewMixin, dates.MonthArchiveView):
    template_name = 'databrowse/calendar_month.html'


class YearView(DateViewMixin, dates.YearArchiveView):
    template_name = 'databrowse/calendar_year.html'


class IndexView(DateViewMixin, dates.ArchiveIndexView):
    template_name = 'databrowse/calendar_main.html'


class CalendarPlugin(DatabrowsePlugin):
    def __init__(self, field_names=None):
        self.field_names = field_names

    def field_dict(self, model):
        """
        Helper function that returns a dictionary of all DateFields or
        DateTimeFields in the given model. If self.field_names is set, it takes
        take that into account when building the dictionary.
        """
        if self.field_names is None:
            return dict([(f.name, f) for f in model._meta.fields if isinstance(f, models.DateField)])
        else:
            return dict([(f.name, f) for f in model._meta.fields if isinstance(f, models.DateField) and f.name in self.field_names])

    def model_index_html(self, request, model, site):
        fields = self.field_dict(model)
        if not fields:
            return u''
        return mark_safe(u'<p class="filter"><strong>View calendar by:</strong> %s</p>' % \
            u', '.join(['<a href="calendars/%s/">%s</a>' % (f.name, force_unicode(capfirst(f.verbose_name))) for f in fields.values()]))

    def urls(self, plugin_name, easy_instance_field):
        if isinstance(easy_instance_field.field, models.DateField):
            d = easy_instance_field.raw_value
            return [mark_safe(u'%s%s/%s/%s/%s/%s/' % (
                easy_instance_field.model.url(),
                plugin_name, easy_instance_field.field.name,
                str(d.year),
                datetime_safe.new_date(d).strftime('%b').lower(),
                d.day))]

    def model_view(self, request, model_databrowse, url):
        self.model, self.site = model_databrowse.model, model_databrowse.site
        self.fields = self.field_dict(self.model)

        # If the model has no DateFields, there's no point in going further.
        if not self.fields:
            raise http.Http404('The requested model has no calendars.')

        if url is None:
            return self.homepage_view(request)
        url_bits = url.split('/')
        if url_bits[0] in self.fields:
            return self.calendar_view(request, self.fields[url_bits[0]], *url_bits[1:])

        raise http.Http404('The requested page does not exist.')

    def homepage_view(self, request):
        easy_model = EasyModel(self.site, self.model)
        field_list = self.fields.values()
        field_list.sort(key=lambda k:k.verbose_name)
        return render_to_response('databrowse/calendar_homepage.html', {
                'root_url': self.site.root_url,
                'model': easy_model,
                'field_list': field_list
            })

    def calendar_view(self, request, field, year=None, month=None, day=None):
        easy_model = EasyModel(self.site, self.model)
        root_url = self.site.root_url

        if day is not None:
            return DayView.as_view(
                                year=year, month=month, day=day,
                                date_field=field.name,
                                queryset=easy_model.get_query_set(),
                                root_url=root_url,
                                model=easy_model,
                                field=field
                            )(request)
        elif month is not None:
            return MonthView.as_view(
                                year=year, month=month,
                                date_field=field.name,
                                queryset=easy_model.get_query_set(),
                                root_url=root_url,
                                model=easy_model,
                                field=field
                            )(request)
        elif year is not None:
            return YearView.as_view(
                                year=year,
                                date_field=field.name,
                                queryset=easy_model.get_query_set(),
                                root_url=root_url,
                                model=easy_model,
                                field=field
                            )(request)
        else:
            return IndexView.as_view(
                                date_field=field.name,
                                queryset=easy_model.get_query_set(),
                                root_url=root_url,
                                model=easy_model,
                                field=field
                            )(request)

        assert False, ('%s, %s, %s, %s' % (field, year, month, day))
