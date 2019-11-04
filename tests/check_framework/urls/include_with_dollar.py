from django.urls import include, re_path

urlpatterns = [
    re_path('^include-with-dollar$', include([])),
]
