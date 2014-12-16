# A URLs file that doesn't use the default
# from django.conf.urls import *
# import pattern.
from django.conf.urls import url

from .views import empty_view, bad_view


urlpatterns = [
    url(r'^test_view/$', empty_view, name="test_view"),
    url(r'^bad_view/$', bad_view, name="bad_view"),
]
