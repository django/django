from __future__ import absolute_import

from django.conf.urls import patterns

from . import feeds


urlpatterns = patterns('django.contrib.syndication.views',
    (r'^syndication/complex/(?P<foo>.*)/$', feeds.ComplexFeed()),
    (r'^syndication/rss2/$', feeds.TestRss2Feed()),
    (r'^syndication/rss091/$', feeds.TestRss091Feed()),
    (r'^syndication/atom/$', feeds.TestAtomFeed()),
    (r'^syndication/custom/$', feeds.TestCustomFeed()),
    (r'^syndication/naive-dates/$', feeds.NaiveDatesFeed()),
    (r'^syndication/aware-dates/$', feeds.TZAwareDatesFeed()),
    (r'^syndication/feedurl/$', feeds.TestFeedUrlFeed()),
    (r'^syndication/articles/$', feeds.ArticlesFeed()),
    (r'^syndication/template/$', feeds.TemplateFeed()),
)
