# This exists for the sake of testing only.  Normally URLs are mapped in
# ../admin/urls.py

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    ('^logout/$', 'django.contrib.auth.views.logout'),
    ('^password_change/$', 'django.contrib.auth.views.password_change'),
    ('^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    ('^password_reset/$', 'django.contrib.auth.views.password_reset')
)

