from django.urls import path, re_path

from .views import empty_view

urlpatterns = [
    path('', empty_view, name="named-url5"),
    re_path(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url6"),
    re_path(r'^(?P<one>[0-9]+)|(?P<two>[0-9]+)/$', empty_view),
]
