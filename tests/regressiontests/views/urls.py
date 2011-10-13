# coding: utf-8
from __future__ import absolute_import

from os import path

from django.conf.urls import patterns, url, include

from . import views


base_dir = path.dirname(path.abspath(__file__))
media_dir = path.join(base_dir, 'media')
locale_dir = path.join(base_dir, 'locale')

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views',),
}

js_info_dict_english_translation = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views.app0',),
}

js_info_dict_multi_packages1 = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views.app1', 'regressiontests.views.app2'),
}

js_info_dict_multi_packages2 = {
    'domain': 'djangojs',
    'packages': ('regressiontests.views.app3', 'regressiontests.views.app4'),
}

urlpatterns = patterns('',
    (r'^$', views.index_page),

    # Default views
    (r'^shortcut/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    (r'^non_existing_url/', 'django.views.defaults.page_not_found'),
    (r'^server_error/', 'django.views.defaults.server_error'),

    # a view that raises an exception for the debug view
    (r'raises/$', views.raises),
    (r'raises404/$', views.raises404),
    (r'raises403/$', views.raises403),

    # i18n views
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    (r'^jsi18n_english_translation/$', 'django.views.i18n.javascript_catalog', js_info_dict_english_translation),
    (r'^jsi18n_multi_packages1/$', 'django.views.i18n.javascript_catalog', js_info_dict_multi_packages1),
    (r'^jsi18n_multi_packages2/$', 'django.views.i18n.javascript_catalog', js_info_dict_multi_packages2),

    # Static views
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_dir}),
)

urlpatterns += patterns('regressiontests.views.views',
    url(r'view_exception/(?P<n>\d+)/$', 'view_exception', name='view_exception'),
    url(r'template_exception/(?P<n>\d+)/$', 'template_exception', name='template_exception'),
    url(r'^raises_template_does_not_exist/$', 'raises_template_does_not_exist', name='raises_template_does_not_exist'),
)
