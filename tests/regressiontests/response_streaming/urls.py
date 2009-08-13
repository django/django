from django.conf.urls.defaults import patterns

import views

urlpatterns = patterns('',
    (r'^stream_file/$', views.test_streaming),
)
