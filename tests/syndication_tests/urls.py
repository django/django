from django.urls import path

from . import feeds

urlpatterns = [
    path("syndication/rss2/", feeds.TestRss2Feed()),
    path("syndication/rss2/with-static-methods/", feeds.TestRss2FeedWithStaticMethod()),
    path("syndication/rss2/articles/<int:entry_id>/", feeds.TestGetObjectFeed()),
    path(
        "syndication/rss2/guid_ispermalink_true/",
        feeds.TestRss2FeedWithGuidIsPermaLinkTrue(),
    ),
    path(
        "syndication/rss2/guid_ispermalink_false/",
        feeds.TestRss2FeedWithGuidIsPermaLinkFalse(),
    ),
    path("syndication/rss091/", feeds.TestRss091Feed()),
    path("syndication/no_pubdate/", feeds.TestNoPubdateFeed()),
    path("syndication/atom/", feeds.TestAtomFeed()),
    path("syndication/latest/", feeds.TestLatestFeed()),
    path("syndication/custom/", feeds.TestCustomFeed()),
    path("syndication/language/", feeds.TestLanguageFeed()),
    path("syndication/naive-dates/", feeds.NaiveDatesFeed()),
    path("syndication/aware-dates/", feeds.TZAwareDatesFeed()),
    path("syndication/feedurl/", feeds.TestFeedUrlFeed()),
    path("syndication/articles/", feeds.ArticlesFeed()),
    path("syndication/template/", feeds.TemplateFeed()),
    path("syndication/template_context/", feeds.TemplateContextFeed()),
    path("syndication/rss2/single-enclosure/", feeds.TestSingleEnclosureRSSFeed()),
    path("syndication/rss2/multiple-enclosure/", feeds.TestMultipleEnclosureRSSFeed()),
    path("syndication/atom/single-enclosure/", feeds.TestSingleEnclosureAtomFeed()),
    path("syndication/atom/multiple-enclosure/", feeds.TestMultipleEnclosureAtomFeed()),
]
