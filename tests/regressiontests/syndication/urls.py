from feeds import TestRssFeed, TestAtomFeed, ComplexFeed
from django.conf.urls.defaults import patterns

feed_dict = {
    'complex': ComplexFeed,
    'rss': TestRssFeed,
    'atom': TestAtomFeed,
    
}
urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict})
)
