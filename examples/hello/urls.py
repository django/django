from django.conf.urls.defaults import *

urlpatterns = patterns('examples.hello.views',
    (r'^html/$', 'hello_html'),
    (r'^text/$', 'hello_text'),
    (r'^write/$', 'hello_write'),
    (r'^metadata/$', 'metadata'),
    (r'^getdata/$', 'get_data'),
    (r'^postdata/$', 'post_data'),
)
