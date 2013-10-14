from __future__ import unicode_literals

from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^regular/$', views.regular),
    url(r'^streaming/$', views.streaming),
    url(r'^in_transaction/$', views.in_transaction),
    url(r'^not_in_transaction/$', views.not_in_transaction),
    url(r'^suspicious/$', views.suspicious),
)
