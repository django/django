from django.conf.urls.defaults import *

urlpatterns = patterns('django.contrib.flatpages.views',
    (r'^(?P<url>.*)$', 'flatpage'),
)
