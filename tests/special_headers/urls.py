# coding: utf-8
from __future__ import absolute_import

from django.conf.urls import patterns

from . import views
from .models import Article

urlpatterns = patterns('',
    (r'^special_headers/article/(?P<object_id>\d+)/$', views.xview_xheaders),
    (r'^special_headers/xview/func/$', views.xview_dec(views.xview)),
    (r'^special_headers/xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
