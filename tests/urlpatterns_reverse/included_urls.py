from django.conf.urls import url

from .views import empty_view


urlpatterns = [
    url(r'^$', empty_view, name="inner-nothing"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="inner-extra"),
    url(r'^(?P<one>\d+)|(?P<two>\d+)/$', empty_view, name="inner-disjunction"),
]
