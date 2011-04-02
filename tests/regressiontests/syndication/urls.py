from django.conf.urls.defaults import *

import feeds

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
)
