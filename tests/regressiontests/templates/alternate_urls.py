# coding: utf-8

from __future__ import absolute_import

from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('',
    # View returning a template response
    (r'^template_response_view/$', views.template_response_view),

    # A view that can be hard to find...
    url(r'^snark/', views.snark, name='snark'),
)
