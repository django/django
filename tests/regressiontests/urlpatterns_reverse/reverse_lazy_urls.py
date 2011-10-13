from __future__ import absolute_import

from django.conf.urls import patterns, url

from .views import empty_view, LazyRedirectView, login_required_view

urlpatterns = patterns('',
    url(r'^redirected_to/$', empty_view, name='named-lazy-url-redirected-to'),
    url(r'^login/$', empty_view, name='some-login-page'),
    url(r'^login_required_view/$', login_required_view),
    url(r'^redirect/$', LazyRedirectView.as_view()),
)
