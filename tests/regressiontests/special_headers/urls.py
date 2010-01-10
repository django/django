# coding: utf-8
from django.conf.urls.defaults import *
from django.views.generic.list_detail import object_detail
from models import Article
import views

urlpatterns = patterns('',
    (r'^article/(?P<object_id>\d+)/$', object_detail, {'queryset': Article.objects.all()}),
    (r'^xview/$', views.xview),
)
