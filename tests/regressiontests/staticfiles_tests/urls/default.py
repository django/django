from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),
)
