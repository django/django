# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url

from . import views

ns_patterns = [
    # Test urls for testing reverse lookups
    url(r'^$', views.index, name='index'),
    url(r'^client/([0-9,]+)/$', views.client, name='client'),
    url(r'^client/(?P<id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action, name='client_action'),
    url(r'^client/(?P<client_id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action, name='client_action'),
    url(r'^named-client/([0-9]+)/$', views.client2, name="named.client"),
]


urlpatterns = ns_patterns + [
    # Unicode strings are permitted everywhere.
    url(r'^Юникод/(\w+)/$', views.client2, name="метка_оператора"),
    url(r'^Юникод/(?P<tag>\S+)/$', views.client2, name="метка_оператора_2"),

    # Test urls for namespaces and current_app
    url(r'ns1/', include((ns_patterns, 'app'), 'ns1')),
    url(r'ns2/', include((ns_patterns, 'app'))),
]
