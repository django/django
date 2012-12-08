# -*- coding: utf-8 -*-
"""
URL dispatcher config for {{ app_name|title }} Django application.

.. seealso::
    http://docs.djangoproject.com/en/dev/topics/http/urls/
"""
from django.conf.urls import patterns, include, url

from {{ app_name }} import views


# Replace the following example with your URL dispatcher config or remove file.

urlpatterns = patterns('',
    url(r'^$', views.HomeView.as_view(), name='home'),
)

