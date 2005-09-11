"""
Syndication feed generation library -- used for generating RSS, etc.

Sample usage:

>>> feed = feedgenerator.Rss201rev2Feed(
...     title=u"Poynter E-Media Tidbits",
...     link=u"http://www.poynter.org/column.asp?id=31",
...     description=u"A group weblog by the sharpest minds in online media/journalism/publishing.",
...     language=u"en",
... )
>>> feed.add_item(title="Hello", link=u"http://www.holovaty.com/test/", description="Testing.")
>>> fp = open('test.rss', 'w')
>>> feed.write(fp, 'utf-8')
>>> fp.close()

For definitions of the different versions of RSS, see:
http://diveintomark.org/archives/2004/02/04/incompatible-rss
"""

from django.utils.xmlutils import SimplerXMLGenerator

class SyndicationFeed:
    "Base class for all syndication feeds. Subclasses should provide write()"
    def __init__(self, title, link, description, language=None):
        self.feed_info = {
            'title': title,
            'link': link,
            'description': description,
            'language': language,
        }
        self.items = []

    def add_item(self, title, link, description, author_email=None,
        author_name=None, pubdate=None, comments=None, unique_id=None,
        enclosure=None):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        self.items.append({
            'title': title,
            'link': link,
            'description': description,
            'author_email': author_email,
            'author_name': author_name,
            'pubdate': pubdate,
            'comments': comments,
            'unique_id': unique_id,
            'enclosure': enclosure,
        })

    def num_items(self):
        return len(self.items)

    def write(self, outfile, encoding):
        """
        Outputs the feed in the given encoding to outfile, which is a file-like
        object. Subclasses should override this.
        """
        raise NotImplementedError

    def writeString(self, encoding):
        """
        Returns the feed in the given encoding as a string.
        """
        from StringIO import StringIO
        s = StringIO()
        self.write(s, encoding)
        return s.getvalue()

class Enclosure:
    "Represents an RSS enclosure"
    def __init__(self, url, length, mime_type):
        "All args are expected to be Python Unicode objects"
        self.url, self.length, self.mime_type = url, length, mime_type

class RssFeed(SyndicationFeed):
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        self.writeRssElement(handler)
        self.writeChannelElement(handler)
        for item in self.items:
            self.writeRssItem(handler, item)
        self.endChannelElement(handler)
        self.endRssElement(handler)

    def writeRssElement(self, handler):
        "Adds the <rss> element to handler, taking care of versioning, etc."
        raise NotImplementedError

    def endRssElement(self, handler):
        "Ends the <rss> element."
        handler.endElement(u"rss")

    def writeChannelElement(self, handler):
        handler.startElement(u"channel", {})
        handler.addQuickElement(u"title", self.feed_info['title'], {})
        handler.addQuickElement(u"link", self.feed_info['link'], {})
        handler.addQuickElement(u"description", self.feed_info['description'], {})
        if self.feed_info['language'] is not None:
            handler.addQuickElement(u"language", self.feed_info['language'], {})

    def endChannelElement(self, handler):
        handler.endElement(u"channel")

class RssUserland091Feed(RssFeed):
    def writeRssElement(self, handler):
        handler.startElement(u"rss", {u"version": u"0.91"})

    def writeRssItem(self, handler, item):
        handler.startElement(u"item", {})
        handler.addQuickElement(u"title", item['title'], {})
        handler.addQuickElement(u"link", item['link'], {})
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'], {})
        handler.endElement(u"item")

class Rss201rev2Feed(RssFeed):
    # Spec: http://blogs.law.harvard.edu/tech/rss
    def writeRssElement(self, handler):
        handler.startElement(u"rss", {u"version": u"2.0"})

    def writeRssItem(self, handler, item):
        handler.startElement(u"item", {})
        handler.addQuickElement(u"title", item['title'], {})
        handler.addQuickElement(u"link", item['link'], {})
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'], {})
        if item['author_email'] is not None and item['author_name'] is not None:
            handler.addQuickElement(u"author", u"%s (%s)" % \
                (item['author_email'], item['author_name']), {})
        if item['pubdate'] is not None:
            handler.addQuickElement(u"pubDate", item['pubdate'].strftime('%a, %d %b %Y %H:%M:%S %Z'), {})
        if item['comments'] is not None:
            handler.addQuickElement(u"comments", item['comments'], {})
        if item['unique_id'] is not None:
            handler.addQuickElement(u"guid", item['unique_id'], {})
        if item['enclosure'] is not None:
            handler.addQuickElement(u"enclosure", '',
                {u"url": item['enclosure'].url, u"length": item['enclosure'].length,
                    u"type": item['enclosure'].mime_type})
        handler.endElement(u"item")

# This isolates the decision of what the system default is, so calling code can
# do "feedgenerator.DefaultRssFeed" instead of "feedgenerator.Rss201rev2Feed".
DefaultRssFeed = Rss201rev2Feed
