from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^xview/$', views.xview),
)
