# These URLs are normally mapped to /admin/urls.py. This URLs file is 
# provided as a convenience to those who want to deploy these URLs elsewhere.
# This file is also used to provide a reliable view deployment for test purposes.

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    ('^logout/$', 'django.contrib.auth.views.logout'),
    ('^password_change/$', 'django.contrib.auth.views.password_change'),
    ('^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    ('^password_reset/$', 'django.contrib.auth.views.password_reset'),
    ('^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    ('^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    ('^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
)

