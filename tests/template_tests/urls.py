# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    # Test urls for testing reverse lookups
    url(r'^$', views.index),
    url(r'^client/([0-9,]+)/$', views.client),
    url(r'^client/(?P<id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action),
    url(r'^client/(?P<client_id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action),
    url(r'^named-client/([0-9]+)/$', views.client2, name="named.client"),

    # Unicode strings are permitted everywhere.
    url(r'^Юникод/(\w+)/$', views.client2, name="метка_оператора"),
    url(r'^Юникод/(?P<tag>\S+)/$', views.client2, name="метка_оператора_2"),
]
