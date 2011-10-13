# coding: utf-8
from __future__ import absolute_import

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
    url(ur'^Юникод/(\w+)/$', views.client2, name=u"метка_оператора"),
    url(ur'^Юникод/(?P<tag>\S+)/$', 'regressiontests.templates.views.client2', name=u"метка_оператора_2"),
)
