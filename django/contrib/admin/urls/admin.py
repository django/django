from django.conf.urls.defaults import *

urlpatterns = patterns('',
    ('^$', 'django.contrib.admin.views.main.index'),
    ('^jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': 'django.conf'}),
    ('^logout/$', 'django.views.auth.login.logout'),
    ('^password_change/$', 'django.views.registration.passwords.password_change'),
    ('^password_change/done/$', 'django.views.registration.passwords.password_change_done'),
    ('^template_validator/$', 'django.contrib.admin.views.template.template_validator'),

    # Documentation
    ('^doc/$', 'django.contrib.admin.views.doc.doc_index'),
    ('^doc/bookmarklets/$', 'django.contrib.admin.views.doc.bookmarklets'),
    ('^doc/tags/$', 'django.contrib.admin.views.doc.template_tag_index'),
    ('^doc/filters/$', 'django.contrib.admin.views.doc.template_filter_index'),
    ('^doc/views/$', 'django.contrib.admin.views.doc.view_index'),
    ('^doc/views/jump/$', 'django.contrib.admin.views.doc.jump_to_view'),
    ('^doc/views/(?P<view>[^/]+)/$', 'django.contrib.admin.views.doc.view_detail'),
    ('^doc/models/$', 'django.contrib.admin.views.doc.model_index'),
    ('^doc/models/(?P<model>[^/]+)/$', 'django.contrib.admin.views.doc.model_detail'),
#    ('^doc/templates/$', 'django.views.admin.doc.template_index'),
    ('^doc/templates/(?P<template>.*)/$', 'django.contrib.admin.views.doc.template_detail'),
    ('^((?:[^/]+/)+?)add/$', 'django.contrib.admin.views.stages.add.add_stage'),
    ('^((?:[^/]+/)+?)([^/]+)/history/$', 'django.contrib.admin.views.main.history'),
    ('^((?:[^/]+/)+?)([^/]+)/delete/$', 'django.contrib.admin.views.stages.delete.delete_stage'),
    ('^((?:[^/]+/)+?)([^/]+)/change/$', 'django.contrib.admin.views.stages.change.change_stage'),
    ('^((?:[^/]+/)+?)$', 'django.contrib.admin.views.changelist.change_list' ),
)
