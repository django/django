from django.conf.urls.defaults import *

import views


urlpatterns = patterns('',
    (r'^request_attrs/$', views.request_processor),
)
