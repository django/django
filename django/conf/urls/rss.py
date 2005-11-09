from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^(?P<slug>[^/]+)/$', 'rss.rss.feed'),
    (r'^(?P<slug>[^/]+)/(?P<param>.+)/$', 'rss.rss.feed'),
)
