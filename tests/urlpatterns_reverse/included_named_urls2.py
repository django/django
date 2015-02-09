from django.conf.urls import url

from .views import empty_view

urlpatterns = [
    url(r'^$', empty_view, name="named-url5"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url6"),
    url(r'^(?P<one>[0-9]+)|(?P<two>[0-9]+)/$', empty_view),
]
