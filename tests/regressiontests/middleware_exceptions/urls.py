# coding: utf-8
from __future__ import absolute_import

from django.conf.urls import patterns

from . import views

urlpatterns = patterns('',
    (r'^middleware_exceptions/view/$', views.normal_view),
    (r'^middleware_exceptions/not_found/$', views.not_found),
    (r'^middleware_exceptions/error/$', views.server_error),
    (r'^middleware_exceptions/null_view/$', views.null_view),
    (r'^middleware_exceptions/permission_denied/$', views.permission_denied),

    (r'^middleware_exceptions/template_response/$', views.template_response),
    (r'^middleware_exceptions/template_response_error/$', views.template_response_error),
)
