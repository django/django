from __future__ import absolute_import

from django.conf.urls import patterns, url

from .views import empty_view


urlpatterns = patterns('',
    url(r'^$', empty_view, name="named-url5"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url6"),
    url(r'^(?P<one>\d+)|(?P<two>\d+)/$', empty_view),
)

