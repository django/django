# coding: utf-8
from django.conf.urls.defaults import *
from django.views.generic.list_detail import object_detail
from models import Article
import views

urlpatterns = patterns('',
    (r'^special_headers/article/(?P<object_id>\d+)/$', object_detail, {'queryset': Article.objects.all()}),
    (r'^special_headers/xview/func/$', views.xview_dec(views.xview)),
    (r'^special_headers/xview/class/$', views.xview_dec(views.XViewClass.as_view())),
)
