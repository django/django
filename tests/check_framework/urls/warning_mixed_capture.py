from django.urls import re_path

urlpatterns = [
    re_path(r'^(?P<year>\d+)/(\d+)/$', lambda x: x),
]
