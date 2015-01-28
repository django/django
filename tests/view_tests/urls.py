# -*- coding: utf-8 -*-
from os import path

from django.conf.urls import include, url
from django.utils._os import upath
from django.views import defaults, i18n, static

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

js_info_dict_app5 = {
    'domain': 'djangojs',
    'packages': ('view_tests.app5',),
}

urlpatterns = [
    url(r'^$', views.index_page),

    # Default views
    url(r'^non_existing_url/', defaults.page_not_found),
    url(r'^server_error/', defaults.server_error),

    # a view that raises an exception for the debug view
    url(r'raises/$', views.raises),

    url(r'raises400/$', views.raises400),
    url(r'raises403/$', views.raises403),
    url(r'raises404/$', views.raises404),
    url(r'raises500/$', views.raises500),

    url(r'technical404/$', views.technical404, name="my404"),
    url(r'classbased404/$', views.Http404View.as_view()),

    # i18n views
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', i18n.javascript_catalog, js_info_dict),
    url(r'^jsi18n/app5/$', i18n.javascript_catalog, js_info_dict_app5),
    url(r'^jsi18n_english_translation/$', i18n.javascript_catalog, js_info_dict_english_translation),
    url(r'^jsi18n_multi_packages1/$', i18n.javascript_catalog, js_info_dict_multi_packages1),
    url(r'^jsi18n_multi_packages2/$', i18n.javascript_catalog, js_info_dict_multi_packages2),
    url(r'^jsi18n_admin/$', i18n.javascript_catalog, js_info_dict_admin),
    url(r'^jsi18n_template/$', views.jsi18n),

    # Static views
    url(r'^site_media/(?P<path>.*)$', static.serve, {'document_root': media_dir}),
]

urlpatterns += [
    url(r'view_exception/(?P<n>[0-9]+)/$', views.view_exception, name='view_exception'),
    url(r'template_exception/(?P<n>[0-9]+)/$', views.template_exception, name='template_exception'),
    url(r'^raises_template_does_not_exist/(?P<path>.+)$', views.raises_template_does_not_exist, name='raises_template_does_not_exist'),
    url(r'^render_no_template/$', views.render_no_template, name='render_no_template'),
]
