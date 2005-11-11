from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^(?P<url>.*)$', 'django.contrib.flatpages.views.flatpage'),
)
