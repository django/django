from functools import wraps

from django.contrib.syndication import views
from django.utils import feedgenerator
from django.utils.timezone import get_fixed_timezone

from .models import Article, Entry


def wraps_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        value = f(*args, **kwargs)
        return f"{value} -- decorated by @wraps."

    return wrapper


def common_decorator(f):
    def wrapper(*args, **kwargs):
        value = f(*args, **kwargs)
        return f"{value} -- common decorated."

    return wrapper


class TestRss2Feed(views.Feed):
    title = "My blog"
    description = "A more thorough description of my blog."
    link = "/blog/"
    feed_guid = "/foo/bar/1234"
    author_name = "Sally Smith"
    author_email = "test@example.com"
    author_link = "http://www.example.com/"
    categories = ("python", "django")
    feed_copyright = "Copyright (c) 2007, Sally Smith"
    ttl = 600

    def items(self):
        return Entry.objects.all()

    def item_description(self, item):
        return "Overridden description: %s" % item

    def item_pubdate(self, item):
        return item.published

    def item_updateddate(self, item):
        return item.updated

    def item_comments(self, item):
        return "%scomments" % item.get_absolute_url()

    item_author_name = "Sally Smith"
    item_author_email = "test@example.com"
    item_author_link = "http://www.example.com/"
    item_categories = ("python", "testing")
    item_copyright = "Copyright (c) 2007, Sally Smith"


class TestRss2FeedWithCallableObject(TestRss2Feed):
    class TimeToLive:
        def __call__(self):
            return 700

    ttl = TimeToLive()


class TestRss2FeedWithDecoratedMethod(TestRss2Feed):
    class TimeToLive:
        @wraps_decorator
        def __call__(self):
            return 800

    @staticmethod
    @wraps_decorator
    def feed_copyright():
        return "Copyright (c) 2022, John Doe"

    ttl = TimeToLive()

    @staticmethod
    def categories():
        return ("javascript", "vue")

    @wraps_decorator
    def title(self):
        return "Overridden title"

    @wraps_decorator
    def item_title(self, item):
        return f"Overridden item title: {item.title}"

    @wraps_decorator
    def description(self, obj):
        return "Overridden description"

    @wraps_decorator
    def item_description(self):
        return "Overridden item description"


class TestRss2FeedWithWrongDecoratedMethod(TestRss2Feed):
    @common_decorator
    def item_description(self, item):
        return f"Overridden item description: {item.title}"


class TestRss2FeedWithGuidIsPermaLinkTrue(TestRss2Feed):
    def item_guid_is_permalink(self, item):
        return True


class TestRss2FeedWithGuidIsPermaLinkFalse(TestRss2Feed):
    def item_guid(self, item):
        return str(item.pk)

    def item_guid_is_permalink(self, item):
        return False


class TestRss091Feed(TestRss2Feed):
    feed_type = feedgenerator.RssUserland091Feed


class TestNoPubdateFeed(views.Feed):
    title = "Test feed"
    link = "/feed/"

    def items(self):
        return Entry.objects.all()


class TestAtomFeed(TestRss2Feed):
    feed_type = feedgenerator.Atom1Feed
    subtitle = TestRss2Feed.description


class TestLatestFeed(TestRss2Feed):
    """
    A feed where the latest entry date is an `updated` element.
    """

    feed_type = feedgenerator.Atom1Feed
    subtitle = TestRss2Feed.description

    def items(self):
        return Entry.objects.exclude(title="My last entry")


class ArticlesFeed(TestRss2Feed):
    """
    A feed to test no link being defined. Articles have no get_absolute_url()
    method, and item_link() is not defined.
    """

    def items(self):
        return Article.objects.all()


class TestSingleEnclosureRSSFeed(TestRss2Feed):
    """
    A feed to test that RSS feeds work with a single enclosure.
    """

    def item_enclosure_url(self, item):
        return "http://example.com"

    def item_enclosure_size(self, item):
        return 0

    def item_mime_type(self, item):
        return "image/png"


class TestMultipleEnclosureRSSFeed(TestRss2Feed):
    """
    A feed to test that RSS feeds raise an exception with multiple enclosures.
    """

    def item_enclosures(self, item):
        return [
            feedgenerator.Enclosure("http://example.com/hello.png", 0, "image/png"),
            feedgenerator.Enclosure("http://example.com/goodbye.png", 0, "image/png"),
        ]


class TemplateFeed(TestRss2Feed):
    """
    A feed to test defining item titles and descriptions with templates.
    """

    title_template = "syndication/title.html"
    description_template = "syndication/description.html"

    # Defining a template overrides any item_title definition
    def item_title(self):
        return "Not in a template"


class TemplateContextFeed(TestRss2Feed):
    """
    A feed to test custom context data in templates for title or description.
    """

    title_template = "syndication/title_context.html"
    description_template = "syndication/description_context.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["foo"] = "bar"
        return context


class TestLanguageFeed(TestRss2Feed):
    language = "de"


class TestGetObjectFeed(TestRss2Feed):
    def get_object(self, request, entry_id):
        return Entry.objects.get(pk=entry_id)

    def items(self, obj):
        return Article.objects.filter(entry=obj)

    def item_link(self, item):
        return "%sarticle/%s/" % (item.entry.get_absolute_url(), item.pk)

    def item_comments(self, item):
        return "%scomments" % self.item_link(item)

    def item_description(self, item):
        return "Article description: %s" % item.title

    def item_title(self, item):
        return "Title: %s" % item.title


class TestFeedWithStylesheets(TestRss2Feed):
    stylesheets = [
        "/stylesheet1.xsl",
        feedgenerator.Stylesheet("/stylesheet2.xsl"),
    ]


class NaiveDatesFeed(TestAtomFeed):
    """
    A feed with naive (non-timezone-aware) dates.
    """

    def item_pubdate(self, item):
        return item.published


class TZAwareDatesFeed(TestAtomFeed):
    """
    A feed with timezone-aware dates.
    """

    def item_pubdate(self, item):
        # Provide a weird offset so that the test can know it's getting this
        # specific offset and not accidentally getting on from
        # settings.TIME_ZONE.
        return item.published.replace(tzinfo=get_fixed_timezone(42))


class TestFeedUrlFeed(TestAtomFeed):
    feed_url = "http://example.com/customfeedurl/"


class MyCustomAtom1Feed(feedgenerator.Atom1Feed):
    """
    Test of a custom feed generator class.
    """

    def root_attributes(self):
        attrs = super().root_attributes()
        attrs["django"] = "rocks"
        return attrs

    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        handler.addQuickElement("spam", "eggs")

    def item_attributes(self, item):
        attrs = super().item_attributes(item)
        attrs["bacon"] = "yum"
        return attrs

    def add_item_elements(self, handler, item):
        super().add_item_elements(handler, item)
        handler.addQuickElement("ministry", "silly walks")


class TestCustomFeed(TestAtomFeed):
    feed_type = MyCustomAtom1Feed


class TestSingleEnclosureAtomFeed(TestAtomFeed):
    """
    A feed to test that Atom feeds work with a single enclosure.
    """

    def item_enclosure_url(self, item):
        return "http://example.com"

    def item_enclosure_size(self, item):
        return 0

    def item_mime_type(self, item):
        return "image/png"


class TestMultipleEnclosureAtomFeed(TestAtomFeed):
    """
    A feed to test that Atom feeds work with multiple enclosures.
    """

    def item_enclosures(self, item):
        return [
            feedgenerator.Enclosure("http://example.com/hello.png", "0", "image/png"),
            feedgenerator.Enclosure("http://example.com/goodbye.png", "0", "image/png"),
        ]
