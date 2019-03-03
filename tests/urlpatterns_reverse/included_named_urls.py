from django.urls import include, path, re_path

from .views import empty_view

urlpatterns = [
    path('', empty_view, name="named-url3"),
    re_path(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url4"),
    re_path(r'^(?P<one>[0-9]+)|(?P<two>[0-9]+)/$', empty_view),
    path('included/', include('urlpatterns_reverse.included_named_urls2')),
]
