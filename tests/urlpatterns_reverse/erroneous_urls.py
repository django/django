from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'(regex_error/$', views.empty_view),
]
