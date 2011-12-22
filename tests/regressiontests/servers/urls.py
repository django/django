from __future__ import absolute_import

from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^example_view/$', views.example_view),
    url(r'^model_view/$', views.model_view),
    url(r'^create_model_instance/$', views.create_model_instance),
)