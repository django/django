from django.urls import include, path, re_path

from . import views

ns_patterns = [
    # Test urls for testing reverse lookups
    path('', views.index, name='index'),
    re_path(r'^client/([0-9,]+)/$', views.client, name='client'),
    re_path(r'^client/(?P<id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action, name='client_action'),
    re_path(r'^client/(?P<client_id>[0-9]+)/(?P<action>[^/]+)/$', views.client_action, name='client_action'),
    re_path(r'^named-client/([0-9]+)/$', views.client2, name="named.client"),
]


urlpatterns = ns_patterns + [
    # Unicode strings are permitted everywhere.
    re_path(r'^Юникод/(\w+)/$', views.client2, name="метка_оператора"),
    re_path(r'^Юникод/(?P<tag>\S+)/$', views.client2, name="метка_оператора_2"),

    # Test urls for namespaces and current_app
    path('ns1/', include((ns_patterns, 'app'), 'ns1')),
    path('ns2/', include((ns_patterns, 'app'))),
]
