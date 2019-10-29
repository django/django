from django.urls import path, re_path

urlpatterns = [
    path('/path-starting-with-slash/', lambda x: x),
    re_path(r'/url-starting-with-slash/$', lambda x: x),
]
