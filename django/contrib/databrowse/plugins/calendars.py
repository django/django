from django import http
from django.db import models
from django.contrib.databrowse.datastructures import EasyModel
from django.contrib.databrowse.sites import DatabrowsePlugin
from django.shortcuts import render_to_response
from django.utils.text import capfirst
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.views.generic import date_based
from django.utils import datetime_safe

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
        if self.fields.has_key(url_bits[0]):
            return self.calendar_view(request, self.fields[url_bits[0]], *url_bits[1:])

        raise http.Http404('The requested page does not exist.')

    def homepage_view(self, request):
        easy_model = EasyModel(self.site, self.model)
        field_list = self.fields.values()
        field_list.sort(lambda x, y: cmp(x.verbose_name, y.verbose_name))
        return render_to_response('databrowse/calendar_homepage.html', {'root_url': self.site.root_url, 'model': easy_model, 'field_list': field_list})

    def calendar_view(self, request, field, year=None, month=None, day=None):
        easy_model = EasyModel(self.site, self.model)
        queryset = easy_model.get_query_set()
        extra_context = {'root_url': self.site.root_url, 'model': easy_model, 'field': field}
        if day is not None:
            return date_based.archive_day(request, year, month, day, queryset, field.name,
                template_name='databrowse/calendar_day.html', allow_empty=False, allow_future=True,
                extra_context=extra_context)
        elif month is not None:
            return date_based.archive_month(request, year, month, queryset, field.name,
                template_name='databrowse/calendar_month.html', allow_empty=False, allow_future=True,
                extra_context=extra_context)
        elif year is not None:
            return date_based.archive_year(request, year, queryset, field.name,
                template_name='databrowse/calendar_year.html', allow_empty=False, allow_future=True,
                extra_context=extra_context)
        else:
            return date_based.archive_index(request, queryset, field.name,
                template_name='databrowse/calendar_main.html', allow_empty=True, allow_future=True,
                extra_context=extra_context)
        assert False, ('%s, %s, %s, %s' % (field, year, month, day))
