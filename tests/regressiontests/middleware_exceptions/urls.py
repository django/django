# coding: utf-8
from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^view/$', views.normal_view),
    (r'^not_found/$', views.not_found),
    (r'^error/$', views.server_error),
    (r'^null_view/$', views.null_view),
    (r'^permission_denied/$', views.permission_denied),
)
