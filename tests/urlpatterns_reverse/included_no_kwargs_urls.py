from django.urls import re_path

from .views import empty_view

urlpatterns = [
    re_path('^inner-no-kwargs/([0-9]+)/$', empty_view, name="inner-no-kwargs")
]
