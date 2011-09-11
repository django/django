from django.conf.urls import patterns, url

import views


urlpatterns = patterns('',
    (r'^request_attrs/$', views.request_processor),
)
