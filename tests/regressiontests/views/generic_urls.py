# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import patterns, url

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

# Date-based generic views.
urlpatterns += patterns('django.views.generic.date_based',
    (r'^date_based/object_detail/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        'object_detail',
        dict(slug_field='slug', **date_based_info_dict)),
    (r'^date_based/object_detail/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/allow_future/$',
        'object_detail',
        dict(allow_future=True, slug_field='slug', **date_based_info_dict)),
    (r'^date_based/archive_day/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        'archive_day',
        numeric_days_info_dict),
    (r'^date_based/archive_month/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        'archive_month',
        date_based_info_dict),
    (r'^date_based/datefield/archive_month/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        'archive_month',
        date_based_datefield_info_dict),
)

# crud generic views.
urlpatterns += patterns('django.views.generic.create_update',
    (r'^create_update/member/create/article/$', 'create_object',
        dict(login_required=True, model=Article)),
    (r'^create_update/create/article/$', 'create_object',
        dict(post_save_redirect='/create_update/view/article/%(slug)s/',
             model=Article)),
    (r'^create_update/update/article/(?P<slug>[-\w]+)/$', 'update_object',
        dict(post_save_redirect='/create_update/view/article/%(slug)s/',
             slug_field='slug', model=Article)),
    (r'^create_update/create_custom/article/$', views.custom_create),
    (r'^create_update/delete/article/(?P<slug>[-\w]+)/$', 'delete_object',
        dict(post_delete_redirect='/create_update/', slug_field='slug',
             model=Article)),

    # No post_save_redirect and no get_absolute_url on model.
    (r'^create_update/no_redirect/create/article/$', 'create_object',
        dict(model=Article)),
    (r'^create_update/no_redirect/update/article/(?P<slug>[-\w]+)/$',
        'update_object', dict(slug_field='slug', model=Article)),

    # get_absolute_url on model, but no passed post_save_redirect.
    (r'^create_update/no_url/create/article/$', 'create_object',
        dict(model=UrlArticle)),
    (r'^create_update/no_url/update/article/(?P<slug>[-\w]+)/$',
        'update_object', dict(slug_field='slug', model=UrlArticle)),
)

urlpatterns += patterns('django.views.generic.list_detail',
    (r'^object_list/page(?P<page>[\w]*)/$', 'object_list', object_list_dict),
    (r'^object_list_no_paginate_by/page(?P<page>[0-9]+)/$', 'object_list',
     object_list_no_paginate_by),
)

# rediriects, both temporary and permanent, with non-ASCII targets
urlpatterns += patterns('django.views.generic.simple',
    ('^nonascii_redirect/$', 'redirect_to',
        {'url': u'/中文/target/', 'permanent': False}),
    ('^permanent_nonascii_redirect/$', 'redirect_to',
        {'url': u'/中文/target/', 'permanent': True}),
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

# simple generic views.
urlpatterns += patterns('django.views.generic.simple',
    (r'^simple/redirect_to/$', 'redirect_to', dict(url='/simple/target/')),
    (r'^simple/redirect_to_temp/$', 'redirect_to', dict(url='/simple/target/', permanent=False)),
    (r'^simple/redirect_to_none/$', 'redirect_to', dict(url=None)),
    (r'^simple/redirect_to_arg/(?P<id>\d+)/$', 'redirect_to', dict(url='/simple/target_arg/%(id)s/')),
    (r'^simple/redirect_to_query/$', 'redirect_to', dict(url='/simple/target/', query_string=True)),
    (r'^simple/redirect_to_arg_and_query/(?P<id>\d+)/$', 'redirect_to', dict(url='/simple/target_arg/%(id)s/', query_string=True)),
)
