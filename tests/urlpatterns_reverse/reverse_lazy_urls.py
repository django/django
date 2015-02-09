from django.conf.urls import url

from .views import LazyRedirectView, empty_view, login_required_view

urlpatterns = [
    url(r'^redirected_to/$', empty_view, name='named-lazy-url-redirected-to'),
    url(r'^login/$', empty_view, name='some-login-page'),
    url(r'^login_required_view/$', login_required_view),
    url(r'^redirect/$', LazyRedirectView.as_view()),
]
