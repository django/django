from __future__ import absolute_import

from django.conf.urls import patterns, url

from .views import empty_view


urlpatterns = patterns('',
    url(r'^$', empty_view, name="inner-nothing"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="inner-extra"),
    url(r'^(?P<one>\d+)|(?P<two>\d+)/$', empty_view, name="inner-disjunction"),
)
