# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from . import views
from .models import Article, DateArticle, UrlArticle


date_based_info_dict = {
    'queryset': Article.objects.all(),
    'date_field': 'date_created',
    'month_format': '%m',
}

object_list_dict = {
    'queryset': Article.objects.all(),
    'paginate_by': 2,
}

object_list_no_paginate_by = {
    'queryset': Article.objects.all(),
}

numeric_days_info_dict = dict(date_based_info_dict, day_format='%d')

date_based_datefield_info_dict = dict(date_based_info_dict, queryset=DateArticle.objects.all())

urlpatterns = patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),

    # Special URLs for particular regression cases.
    url(u'^中文/$', 'regressiontests.views.views.redirect'),
    url(u'^中文/target/$', 'regressiontests.views.views.index_page'),
)

# rediriects, both temporary and permanent, with non-ASCII targets
urlpatterns += patterns('',
    ('^nonascii_redirect/$', RedirectView.as_view(
        url=u'/中文/target/', permanent=False)),
    ('^permanent_nonascii_redirect/$', RedirectView.as_view(
        url=u'/中文/target/', permanent=True)),
)

urlpatterns += patterns('regressiontests.views.views',
    (r'^shortcuts/render_to_response/$', 'render_to_response_view'),
    (r'^shortcuts/render_to_response/request_context/$', 'render_to_response_view_with_request_context'),
    (r'^shortcuts/render_to_response/mimetype/$', 'render_to_response_view_with_mimetype'),
    (r'^shortcuts/render/$', 'render_view'),
    (r'^shortcuts/render/base_context/$', 'render_view_with_base_context'),
    (r'^shortcuts/render/content_type/$', 'render_view_with_content_type'),
    (r'^shortcuts/render/status/$', 'render_view_with_status'),
    (r'^shortcuts/render/current_app/$', 'render_view_with_current_app'),
    (r'^shortcuts/render/current_app_conflict/$', 'render_view_with_current_app_conflict'),
)
