from django.conf.urls.defaults import *
from django.contrib.admindocs import views

urlpatterns = patterns('',
    ('^$', views.doc_index),
    ('^bookmarklets/$', views.bookmarklets),
    ('^tags/$', views.template_tag_index),
    ('^filters/$', views.template_filter_index),
    ('^views/$', views.view_index),
    ('^views/(?P<view>[^/]+)/$', views.view_detail),
    ('^models/$', views.model_index),
    ('^models/(?P<app_label>[^\.]+)\.(?P<model_name>[^/]+)/$', views.model_detail),
#    ('^templates/$', views.template_index),
    ('^templates/(?P<template>.*)/$', views.template_detail),
)
