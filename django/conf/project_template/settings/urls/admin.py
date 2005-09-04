from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^admin/', include('django.conf.urls.admin')),
    (r'^r/', include('django.conf.urls.shortcut')),
)
