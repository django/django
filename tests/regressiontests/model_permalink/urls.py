from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^guitarists/(\w{1,50})/$', 'unimplemented_view_placeholder', name='guitarist_detail'),
)
