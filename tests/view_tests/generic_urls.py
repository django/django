# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from . import views
from .models import Article, DateArticle

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

urlpatterns = [
    url(r'^accounts/login/$', auth_views.login, {'template_name': 'login.html'}),
    url(r'^accounts/logout/$', auth_views.logout),

    # Special URLs for particular regression cases.
    url('^中文/$', views.redirect),
    url('^中文/target/$', views.index_page),
]

# redirects, both temporary and permanent, with non-ASCII targets
urlpatterns += [
    url('^nonascii_redirect/$', RedirectView.as_view(
        url='/中文/target/', permanent=False)),
    url('^permanent_nonascii_redirect/$', RedirectView.as_view(
        url='/中文/target/', permanent=True)),
]

# json response
urlpatterns += [
    url(r'^json/response/$', views.json_response_view),
]
