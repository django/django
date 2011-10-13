# coding: utf-8
from __future__ import absolute_import

from django.conf.urls import patterns
from django.views.generic.list_detail import object_detail

from . import views
from .models import Article

urlpatterns = patterns('',
    (r'^special_headers/article/(?P<object_id>\d+)/$', object_detail, {'queryset': Article.objects.all()}),
    (r'^special_headers/xview/func/$', views.xview_dec(views.xview)),
    (r'^special_headers/xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
