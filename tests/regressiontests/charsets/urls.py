from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    (r'^accept_charset/', views.accept_charset),
    (r'^good_content_type/', views.good_content_type),
    (r'^bad_content_type/', views.bad_content_type),
)
