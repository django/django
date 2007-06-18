from django.conf.urls.defaults import *
from regressiontests.templates import views

urlpatterns = patterns('',

    # Test urls for testing reverse lookups
    (r'^$', views.index),
    (r'^client/(\d+)/$', views.client),
    (r'^client/(\d+)/(?P<action>[^/]+)/$', views.client_action),
    url(r'^named-client/(\d+)/$', views.client, name="named-client"),
)
