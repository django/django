from django.conf.urls.defaults import *

import feeds

feed_dict = {
    'complex': feeds.DeprecatedComplexFeed,
    'rss': feeds.DeprecatedRssFeed,
}

urlpatterns = patterns('django.contrib.syndication.views',
    (r'^complex/(?P<foo>.*)/$', feeds.ComplexFeed()),
    (r'^rss2/$', feeds.TestRss2Feed()),
    (r'^rss091/$', feeds.TestRss091Feed()),
    (r'^atom/$', feeds.TestAtomFeed()),
    (r'^custom/$', feeds.TestCustomFeed()),
    (r'^naive-dates/$', feeds.NaiveDatesFeed()),
    (r'^aware-dates/$', feeds.TZAwareDatesFeed()),
    (r'^feedurl/$', feeds.TestFeedUrlFeed()),
    (r'^articles/$', feeds.ArticlesFeed()),
    (r'^template/$', feeds.TemplateFeed()),

    (r'^depr-feeds/(?P<url>.*)/$', 'feed', {'feed_dict': feed_dict}),
    (r'^depr-feeds-empty/(?P<url>.*)/$', 'feed', {'feed_dict': None}),
)
