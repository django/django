from django.contrib.syndication import feeds, views
from django.core.exceptions import ObjectDoesNotExist
from django.utils import feedgenerator, tzinfo
from models import Article, Entry


class ComplexFeed(views.Feed):
    def get_object(self, request, foo=None):
        if foo is not None:
            raise ObjectDoesNotExist
        return None


class TestRss2Feed(views.Feed):
    title = 'My blog'
    description = 'A more thorough description of my blog.'
    link = '/blog/'
    feed_guid = '/foo/bar/1234'
    author_name = 'Sally Smith'
    author_email = 'test@example.com'
    author_link = 'http://www.example.com/'
    categories = ('python', 'django')
    feed_copyright = 'Copyright (c) 2007, Sally Smith'
    ttl = 600

    def items(self):
        return Entry.objects.all()

    def item_description(self, item):
        return "Overridden description: %s" % item

    def item_pubdate(self, item):
        return item.date

    item_author_name = 'Sally Smith'
    item_author_email = 'test@example.com'
    item_author_link = 'http://www.example.com/'
    item_categories = ('python', 'testing')
    item_copyright = 'Copyright (c) 2007, Sally Smith'


class TestRss091Feed(TestRss2Feed):
    feed_type = feedgenerator.RssUserland091Feed


class TestAtomFeed(TestRss2Feed):
    feed_type = feedgenerator.Atom1Feed
    subtitle = TestRss2Feed.description


class ArticlesFeed(TestRss2Feed):
    """
    A feed to test no link being defined. Articles have no get_absolute_url()
    method, and item_link() is not defined.
    """
    def items(self):
        return Article.objects.all()


class TestEnclosureFeed(TestRss2Feed):
    pass


class TemplateFeed(TestRss2Feed):
    """
    A feed to test defining item titles and descriptions with templates.
    """
    title_template = 'syndication/title.html'
    description_template = 'syndication/description.html'

    # Defining a template overrides any item_title definition
    def item_title(self):
        return "Not in a template"


class NaiveDatesFeed(TestAtomFeed):
    """
    A feed with naive (non-timezone-aware) dates.
    """
    def item_pubdate(self, item):
        return item.date


class TZAwareDatesFeed(TestAtomFeed):
    """
    A feed with timezone-aware dates.
    """
    def item_pubdate(self, item):
        # Provide a weird offset so that the test can know it's getting this
        # specific offset and not accidentally getting on from
        # settings.TIME_ZONE.
        return item.date.replace(tzinfo=tzinfo.FixedOffset(42))


class TestFeedUrlFeed(TestAtomFeed):
    feed_url = 'http://example.com/customfeedurl/'


class MyCustomAtom1Feed(feedgenerator.Atom1Feed):
    """
    Test of a custom feed generator class.
    """
    def root_attributes(self):
        attrs = super(MyCustomAtom1Feed, self).root_attributes()
        attrs[u'django'] = u'rocks'
        return attrs

    def add_root_elements(self, handler):
        super(MyCustomAtom1Feed, self).add_root_elements(handler)
        handler.addQuickElement(u'spam', u'eggs')

    def item_attributes(self, item):
        attrs = super(MyCustomAtom1Feed, self).item_attributes(item)
        attrs[u'bacon'] = u'yum'
        return attrs

    def add_item_elements(self, handler, item):
        super(MyCustomAtom1Feed, self).add_item_elements(handler, item)
        handler.addQuickElement(u'ministry', u'silly walks')


class TestCustomFeed(TestAtomFeed):
    feed_type = MyCustomAtom1Feed


class DeprecatedComplexFeed(feeds.Feed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return None


class DeprecatedRssFeed(feeds.Feed):
    link = "/blog/"
    title = 'My blog'

    def items(self):
        return Entry.objects.all()

    def item_link(self, item):
        return "/blog/%s/" % item.pk

