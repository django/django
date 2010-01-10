# coding: utf-8
from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^$', views.index),
)
