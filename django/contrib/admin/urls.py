from django.conf import settings
from django.conf.urls.defaults import *

if settings.USE_I18N:
    i18n_view = 'django.views.i18n.javascript_catalog'
else:
    i18n_view = 'django.views.i18n.null_javascript_catalog'

urlpatterns = patterns('',
    ('^$', 'django.contrib.admin.views.main.index'),
    ('^r/(\d+)/(.*)/$', 'django.views.defaults.shortcut'),
    ('^jsi18n/$', i18n_view, {'packages': 'django.conf'}),
    ('^logout/$', 'django.contrib.auth.views.logout'),
    ('^password_change/$', 'django.contrib.auth.views.password_change'),
    ('^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    ('^template_validator/$', 'django.contrib.admin.views.template.template_validator'),

    # Documentation
    ('^doc/$', 'django.contrib.admin.views.doc.doc_index'),
    ('^doc/bookmarklets/$', 'django.contrib.admin.views.doc.bookmarklets'),
    ('^doc/tags/$', 'django.contrib.admin.views.doc.template_tag_index'),
    ('^doc/filters/$', 'django.contrib.admin.views.doc.template_filter_index'),
    ('^doc/views/$', 'django.contrib.admin.views.doc.view_index'),
    ('^doc/views/(?P<view>[^/]+)/$', 'django.contrib.admin.views.doc.view_detail'),
    ('^doc/models/$', 'django.contrib.admin.views.doc.model_index'),
    ('^doc/models/(?P<app_label>[^\.]+)\.(?P<model_name>[^/]+)/$', 'django.contrib.admin.views.doc.model_detail'),
#    ('^doc/templates/$', 'django.views.admin.doc.template_index'),
    ('^doc/templates/(?P<template>.*)/$', 'django.contrib.admin.views.doc.template_detail'),

    # "Add user" -- a special-case view
    ('^auth/user/add/$', 'django.contrib.admin.views.auth.user_add_stage'),
    # "Change user password" -- another special-case view
    ('^auth/user/(\d+)/password/$', 'django.contrib.admin.views.auth.user_change_password'),

    # Add/change/delete/history
    ('^([^/]+)/([^/]+)/$', 'django.contrib.admin.views.main.change_list'),
    ('^([^/]+)/([^/]+)/add/$', 'django.contrib.admin.views.main.add_stage'),
    ('^([^/]+)/([^/]+)/(.+)/history/$', 'django.contrib.admin.views.main.history'),
    ('^([^/]+)/([^/]+)/(.+)/delete/$', 'django.contrib.admin.views.main.delete_stage'),
    ('^([^/]+)/([^/]+)/(.+)/$', 'django.contrib.admin.views.main.change_stage'),
)

del i18n_view
