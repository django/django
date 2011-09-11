from django.conf.urls import patterns, url
from django.contrib.admindocs import views

urlpatterns = patterns('',
    url('^$',
        views.doc_index,
        name='django-admindocs-docroot'
    ),
    url('^bookmarklets/$',
        views.bookmarklets,
        name='django-admindocs-bookmarklets'
    ),
    url('^tags/$',
        views.template_tag_index,
        name='django-admindocs-tags'
    ),
    url('^filters/$',
        views.template_filter_index,
        name='django-admindocs-filters'
    ),
    url('^views/$',
        views.view_index,
        name='django-admindocs-views-index'
    ),
    url('^views/(?P<view>[^/]+)/$',
        views.view_detail,
        name='django-admindocs-views-detail'
    ),
    url('^models/$',
        views.model_index,
        name='django-admindocs-models-index'
    ),
    url('^models/(?P<app_label>[^\.]+)\.(?P<model_name>[^/]+)/$',
        views.model_detail,
        name='django-admindocs-models-detail'
    ),
    url('^templates/(?P<template>.*)/$',
        views.template_detail,
        name='django-admindocs-templates'
    ),
)
