# coding: utf-8
from os import path

from django.conf.urls.defaults import *

from models import *
import views


base_dir = path.dirname(path.abspath(__file__))
media_dir = path.join(base_dir, 'media')
locale_dir = path.join(base_dir, 'locale')

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views',),
}

date_based_info_dict = {
    'queryset': Article.objects.all(),
    'date_field': 'date_created',
    'month_format': '%m',
}
numeric_days_info_dict = dict(date_based_info_dict, day_format='%d')

date_based_datefield_info_dict = dict(date_based_info_dict, queryset=DateArticle.objects.all())

urlpatterns = patterns('',
    (r'^$', views.index_page),

    # Default views
    (r'^shortcut/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    (r'^non_existing_url/', 'django.views.defaults.page_not_found'),
    (r'^server_error/', 'django.views.defaults.server_error'),

    # i18n views
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),

    # Static views
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_dir}),

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
        dict(post_save_redirect='/views/create_update/view/article/%(slug)s/',
             model=Article)),
    (r'^create_update/update/article/(?P<slug>[-\w]+)/$', 'update_object',
        dict(post_save_redirect='/views/create_update/view/article/%(slug)s/',
             slug_field='slug', model=Article)),
    (r'^create_update/create_custom/article/$', views.custom_create),
    (r'^create_update/delete/article/(?P<slug>[-\w]+)/$', 'delete_object',
        dict(post_delete_redirect='/views/create_update/', slug_field='slug',
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

# a view that raises an exception for the debug view
urlpatterns += patterns('',
    (r'^raises/$', views.raises),
    (r'^raises404/$', views.raises404),
)

# rediriects, both temporary and permanent, with non-ASCII targets
urlpatterns += patterns('django.views.generic.simple',
    ('^nonascii_redirect/$', 'redirect_to',
        {'url': u'/views/中文/target/', 'permanent': False}),
    ('^permanent_nonascii_redirect/$', 'redirect_to',
        {'url': u'/views/中文/target/', 'permanent': True}),
)

