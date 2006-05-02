from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'examples.views.index'),
    (r'^hello/', include('examples.hello.urls')),
)
