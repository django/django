# coding: utf-8
from __future__ import absolute_import

from os import path

from django.conf.urls import patterns, url, include
from django.utils._os import upath

from . import views


base_dir = path.dirname(path.abspath(upath(__file__)))
media_dir = path.join(base_dir, 'media')
locale_dir = path.join(base_dir, 'locale')

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('view_tests',),
}

js_info_dict_english_translation = {
    'domain': 'djangojs',
    'packages': ('view_tests.app0',),
}

js_info_dict_multi_packages1 = {
    'domain': 'djangojs',
    'packages': ('view_tests.app1', 'view_tests.app2'),
}

js_info_dict_multi_packages2 = {
    'domain': 'djangojs',
    'packages': ('view_tests.app3', 'view_tests.app4'),
}

js_info_dict_admin = {
    'domain': 'djangojs',
    'packages': ('django.contrib.admin', 'view_tests'),
}

urlpatterns = patterns('',
    (r'^$', views.index_page),

    # Default views
    (r'^non_existing_url/', 'django.views.defaults.page_not_found'),
    (r'^server_error/', 'django.views.defaults.server_error'),

    # a view that raises an exception for the debug view
    (r'raises/$', views.raises),

    (r'raises400/$', views.raises400),
    (r'raises403/$', views.raises403),
    (r'raises404/$', views.raises404),

    # i18n views
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    (r'^jsi18n_english_translation/$', 'django.views.i18n.javascript_catalog', js_info_dict_english_translation),
    (r'^jsi18n_multi_packages1/$', 'django.views.i18n.javascript_catalog', js_info_dict_multi_packages1),
    (r'^jsi18n_multi_packages2/$', 'django.views.i18n.javascript_catalog', js_info_dict_multi_packages2),
    (r'^jsi18n_admin/$', 'django.views.i18n.javascript_catalog', js_info_dict_admin),
    (r'^jsi18n_template/$', views.jsi18n),

    # Static views
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_dir}),
)

urlpatterns += patterns('view_tests.views',
    url(r'view_exception/(?P<n>\d+)/$', 'view_exception', name='view_exception'),
    url(r'template_exception/(?P<n>\d+)/$', 'template_exception', name='template_exception'),
    url(r'^raises_template_does_not_exist/(?P<path>.+)$', 'raises_template_does_not_exist', name='raises_template_does_not_exist'),
    url(r'^render_no_template/$', 'render_no_template', name='render_no_template'),
)
