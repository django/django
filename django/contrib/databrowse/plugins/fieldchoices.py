from __future__ import unicode_literals

from django import http
from django.db import models
from django.contrib.databrowse.datastructures import EasyModel
from django.contrib.databrowse.sites import DatabrowsePlugin
from django.shortcuts import render_to_response
from django.utils.html import format_html, format_html_join
from django.utils.http import urlquote
from django.utils.text import capfirst
from django.utils.encoding import force_text


class FieldChoicePlugin(DatabrowsePlugin):
    def __init__(self, field_filter=None):
        # If field_filter is given, it should be a callable that takes a
        # Django database Field instance and returns True if that field should
        # be included. If field_filter is None, that all fields will be used.
        self.field_filter = field_filter

    def field_dict(self, model):
        """
        Helper function that returns a dictionary of all fields in the given
        model. If self.field_filter is set, it only includes the fields that
        match the filter.
        """
        if self.field_filter:
            return dict([(f.name, f) for f in model._meta.fields if self.field_filter(f)])
        else:
            return dict([(f.name, f) for f in model._meta.fields if not f.rel and not f.primary_key and not f.unique and not isinstance(f, (models.AutoField, models.TextField))])

    def model_index_html(self, request, model, site):
        fields = self.field_dict(model)
        if not fields:
            return ''
        return format_html('<p class="filter"><strong>View by:</strong> {0}</p>',
                           format_html_join(', ', '<a href="fields/{0}/">{1}</a>',
                                            ((f.name, force_text(capfirst(f.verbose_name))) for f in fields.values())))

    def urls(self, plugin_name, easy_instance_field):
        if easy_instance_field.field in self.field_dict(easy_instance_field.model.model).values():
            return ['%s%s/%s/%s/' % (
                easy_instance_field.model.url(),
                plugin_name, easy_instance_field.field.name,
                urlquote(easy_instance_field.raw_value, safe=''))]

    def model_view(self, request, model_databrowse, url):
        self.model, self.site = model_databrowse.model, model_databrowse.site
        self.fields = self.field_dict(self.model)

        # If the model has no fields with choices, there's no point in going
        # further.
        if not self.fields:
            raise http.Http404('The requested model has no fields.')

        if url is None:
            return self.homepage_view(request)
        url_bits = url.split('/', 1)
        if url_bits[0] in self.fields:
            return self.field_view(request, self.fields[url_bits[0]], *url_bits[1:])

        raise http.Http404('The requested page does not exist.')

    def homepage_view(self, request):
        easy_model = EasyModel(self.site, self.model)
        field_list = list(self.fields.values())
        field_list.sort(key=lambda k: k.verbose_name)
        return render_to_response('databrowse/fieldchoice_homepage.html', {'root_url': self.site.root_url, 'model': easy_model, 'field_list': field_list})

    def field_view(self, request, field, value=None):
        easy_model = EasyModel(self.site, self.model)
        easy_field = easy_model.field(field.name)
        if value is not None:
            obj_list = easy_model.objects(**{field.name: value})
            return render_to_response('databrowse/fieldchoice_detail.html', {'root_url': self.site.root_url, 'model': easy_model, 'field': easy_field, 'value': value, 'object_list': obj_list})
        obj_list = [v[field.name] for v in self.model._default_manager.distinct().order_by(field.name).values(field.name)]
        return render_to_response('databrowse/fieldchoice_list.html', {'root_url': self.site.root_url, 'model': easy_model, 'field': easy_field, 'object_list': obj_list})
