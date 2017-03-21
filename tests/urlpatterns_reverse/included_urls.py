from django.conf.urls import url

from .views import empty_view

urlpatterns = [
    url(r'^$', empty_view, name="inner-nothing"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="inner-extra"),
    url(r'^(?P<one>[0-9]+)|(?P<two>[0-9]+)/$', empty_view, name="inner-disjunction"),
]
