from __future__ import absolute_import

from django.conf.urls import patterns

from . import views


urlpatterns = patterns('',
    (r'^test_utils/get_person/(\d+)/$', views.get_person),
)
