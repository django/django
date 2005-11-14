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
import datetime, re, time
import email.Utils
from xml.dom import minidom
from xml.parsers.expat import ExpatError

def rfc2822_date(date):
    return email.Utils.formatdate(time.mktime(date.timetuple()))

def rfc3339_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_tag_uri(url, date):
    "Creates a TagURI. See http://diveintomark.org/archives/2004/05/28/howto-atom-id"
    tag = re.sub('^http://', '', url)
    if date is not None:
        tag = re.sub('/', ',%s:/' % date.strftime('%Y-%m-%d'), tag, 1)
    tag = re.sub('#', '/', tag)
    return 'tag:' + tag

class SyndicationFeed:
    "Base class for all syndication feeds. Subclasses should provide write()"
    def __init__(self, title, link, description, language=None, author_email=None,
            author_name=None, author_link=None, subtitle=None, categories=None):
        self.feed = {
            'title': title,
            'link': link,
            'description': description,
            'language': language,
            'author_email': author_email,
            'author_name': author_name,
            'author_link': author_link,
            'subtitle': subtitle,
            'categories': categories or (),
        }
        self.items = []

    def add_item(self, title, link, description, author_email=None,
        author_name=None, pubdate=None, comments=None,
        unique_id=None, enclosure=None, categories=()):
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
            'categories': categories or (),
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

    def latest_post_date(self):
        """
        Returns the latest item's pubdate. If none of them have a pubdate,
        this returns the current date/time.
        """
        updates = [i['pubdate'] for i in self.items if i['pubdate'] is not None]
        if len(updates) > 0:
            updates.sort()
            return updates[-1]
        else:
            return datetime.datetime.now()

class Enclosure:
    "Represents an RSS enclosure"
    def __init__(self, url, length, mime_type):
        "All args are expected to be Python Unicode objects"
        self.url, self.length, self.mime_type = url, length, mime_type

class RssFeed(SyndicationFeed):
    mime_type = 'application/rss+xml'
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        handler.startElement(u"rss", {u"version": self._version})
        handler.startElement(u"channel", {})
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", self.feed['link'])
        handler.addQuickElement(u"description", self.feed['description'])
        if self.feed['language'] is not None:
            handler.addQuickElement(u"language", self.feed['language'])
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement(u"rss")

    def endChannelElement(self, handler):
        handler.endElement(u"channel")

class RssUserland091Feed(RssFeed):
    _version = u"0.91"
    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"item", {})
            handler.addQuickElement(u"title", item['title'])
            handler.addQuickElement(u"link", item['link'])
            if item['description'] is not None:
                handler.addQuickElement(u"description", item['description'])
            handler.endElement(u"item")

class Rss201rev2Feed(RssFeed):
    # Spec: http://blogs.law.harvard.edu/tech/rss
    _version = u"2.0"
    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"item", {})
            handler.addQuickElement(u"title", item['title'])
            handler.addQuickElement(u"link", item['link'])
            if item['description'] is not None:
                handler.addQuickElement(u"description", item['description'])

            # Author information.
            if item['author_email'] is not None and item['author_name'] is not None:
                handler.addQuickElement(u"author", u"%s (%s)" % \
                    (item['author_email'], item['author_name']))

            if item['pubdate'] is not None:
                handler.addQuickElement(u"pubDate", rfc2822_date(item['pubdate']).decode('ascii'))
            if item['comments'] is not None:
                handler.addQuickElement(u"comments", item['comments'])
            if item['unique_id'] is not None:
                handler.addQuickElement(u"guid", item['unique_id'])

            # Enclosure.
            if item['enclosure'] is not None:
                handler.addQuickElement(u"enclosure", '',
                    {u"url": item['enclosure'].url, u"length": item['enclosure'].length,
                        u"type": item['enclosure'].mime_type})

            # Categories.
            for cat in item['categories']:
                handler.addQuickElement(u"category", cat)

            handler.endElement(u"item")

class Atom1Feed(SyndicationFeed):
    # Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    mime_type = 'application/atom+xml'
    ns = u"http://www.w3.org/2005/Atom"
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        if self.feed['language'] is not None:
            handler.startElement(u"feed", {u"xmlns": self.ns, u"xml:lang": self.feed['language']})
        else:
            handler.startElement(u"feed", {u"xmlns": self.ns})
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", "", {u"href": self.feed['link']})
        handler.addQuickElement(u"id", self.feed['link'])
        handler.addQuickElement(u"updated", rfc3339_date(self.latest_post_date()).decode('ascii'))
        if self.feed['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", self.feed['author_name'])
            if self.feed['author_email'] is not None:
                handler.addQuickElement(u"email", self.feed['author_email'])
            if self.feed['author_link'] is not None:
                handler.addQuickElement(u"uri", self.feed['author_link'])
            handler.endElement(u"author")
        if self.feed['subtitle'] is not None:
            handler.addQuickElement(u"subtitle", self.feed['subtitle'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", "", {u"term": cat})
        self.write_items(handler)
        handler.endElement(u"feed")

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"entry", {})
            handler.addQuickElement(u"title", item['title'])
            handler.addQuickElement(u"link", u"", {u"href": item['link']})
            if item['pubdate'] is not None:
                handler.addQuickElement(u"updated", rfc3339_date(item['pubdate']).decode('ascii'))

            # Author information.
            if item['author_name'] is not None:
                handler.startElement(u"author", {})
                handler.addQuickElement(u"name", item['author_name'])
                if item['author_email'] is not None:
                    handler.addQuickElement(u"email", item['author_email'])
                handler.endElement(u"author")

            # Unique ID.
            if item['unique_id'] is not None:
                unique_id = item['unique_id']
            else:
                unique_id = get_tag_uri(item['link'], item['pubdate'])
            handler.addQuickElement(u"id", unique_id)

            # Summary.
            if item['description'] is not None:
                handler.addQuickElement(u"summary", item['description'], {u"type": u"html"})

            # Enclosure.
            if item['enclosure'] is not None:
                handler.addQuickElement(u"link", '',
                    {u"rel": u"enclosure",
                     u"href": item['enclosure'].url,
                     u"length": item['enclosure'].length,
                     u"type": item['enclosure'].mime_type})

            # Categories:
            for cat in item['categories']:
                handler.addQuickElement(u"category", u"", {u"term": cat})

            handler.endElement(u"entry")

# This isolates the decision of what the system default is, so calling code can
# do "feedgenerator.DefaultFeed" instead of "feedgenerator.Rss201rev2Feed".
DefaultFeed = Rss201rev2Feed
