# coding: utf-8
from __future__ import absolute_import, unicode_literals

from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns('',

    # Test urls for testing reverse lookups
    (r'^$', views.index),
    (r'^client/([\d,]+)/$', views.client),
    (r'^client/(?P<id>\d+)/(?P<action>[^/]+)/$', views.client_action),
    (r'^client/(?P<client_id>\d+)/(?P<action>[^/]+)/$', views.client_action),
    url(r'^named-client/(\d+)/$', views.client2, name="named.client"),

    # Unicode strings are permitted everywhere.
    url(r'^Юникод/(\w+)/$', views.client2, name="метка_оператора"),
    url(r'^Юникод/(?P<tag>\S+)/$', 'template_tests.views.client2', name="метка_оператора_2"),
)
