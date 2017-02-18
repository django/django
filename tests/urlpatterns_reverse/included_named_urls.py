from django.conf.urls import include, url

from .views import empty_view

urlpatterns = [
    url(r'^$', empty_view, name="named-url3"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url4"),
    url(r'^(?P<one>[0-9]+)|(?P<two>[0-9]+)/$', empty_view),
    url(r'^included/', include('urlpatterns_reverse.included_named_urls2')),
]
