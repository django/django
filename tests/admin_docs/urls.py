# coding: utf-8
from __future__ import absolute_import

from django.conf.urls import patterns

from . import views

urlpatterns = patterns('',
    (r'^xview/func/$', views.xview_dec(views.xview)),
    (r'^xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
