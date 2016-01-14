from django.conf.urls import url

from . import feeds

urlpatterns = [
    url(r'^syndication/rss2/$', feeds.TestRss2Feed()),
    url(r'^syndication/rss2/guid_ispermalink_true/$',
        feeds.TestRss2FeedWithGuidIsPermaLinkTrue()),
    url(r'^syndication/rss2/guid_ispermalink_false/$',
        feeds.TestRss2FeedWithGuidIsPermaLinkFalse()),
    url(r'^syndication/rss091/$', feeds.TestRss091Feed()),
    url(r'^syndication/no_pubdate/$', feeds.TestNoPubdateFeed()),
    url(r'^syndication/atom/$', feeds.TestAtomFeed()),
    url(r'^syndication/latest/$', feeds.TestLatestFeed()),
    url(r'^syndication/custom/$', feeds.TestCustomFeed()),
    url(r'^syndication/naive-dates/$', feeds.NaiveDatesFeed()),
    url(r'^syndication/aware-dates/$', feeds.TZAwareDatesFeed()),
    url(r'^syndication/feedurl/$', feeds.TestFeedUrlFeed()),
    url(r'^syndication/articles/$', feeds.ArticlesFeed()),
    url(r'^syndication/template/$', feeds.TemplateFeed()),
    url(r'^syndication/template_context/$', feeds.TemplateContextFeed()),
    url(r'^syndication/rss2/single-enclosure/$', feeds.TestSingleEnclosureRSSFeed()),
    url(r'^syndication/rss2/multiple-enclosure/$', feeds.TestMultipleEnclosureRSSFeed()),
    url(r'^syndication/atom/single-enclosure/$', feeds.TestSingleEnclosureAtomFeed()),
    url(r'^syndication/atom/multiple-enclosure/$', feeds.TestMultipleEnclosureAtomFeed()),
]
