from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^(?P<slug>\w+)/$', 'rss.rss.feed'),
    (r'^(?P<slug>\w+)/(?P<param>[\w/]+)/$', 'rss.rss.feed'),
)
