from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib.contenttypes import views

urlpatterns = [
    url(r'^shortcut/(\d+)/(.*)/$', views.shortcut),
]
