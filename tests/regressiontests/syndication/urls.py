import feeds
from django.conf.urls.defaults import patterns

feed_dict = {
    'complex': feeds.ComplexFeed,
    'rss': feeds.TestRssFeed,
    'atom': feeds.TestAtomFeed,
    'custom': feeds.TestCustomFeed,
    'naive-dates': feeds.NaiveDatesFeed,
    'aware-dates': feeds.TZAwareDatesFeed,    
}
urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict})
)
