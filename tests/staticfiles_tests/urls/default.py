from django.contrib.staticfiles import views
from django.urls import re_path

urlpatterns = [
    re_path('^static/(?P<path>.*)$', views.serve),
]
