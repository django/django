from __future__ import absolute_import

from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('',
    (r'^request_attrs/$', views.request_processor),
)
