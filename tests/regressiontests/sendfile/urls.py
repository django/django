from django.conf.urls.defaults import patterns

import views

urlpatterns = patterns('',
    (r'^serve_file/(?P<filename>.*)/$', views.serve_file),
)