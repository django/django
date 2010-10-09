"""
Syndication feed generation library -- used for generating RSS, etc.

Sample usage:

>>> from django.utils import feedgenerator
>>> feed = feedgenerator.Rss201rev2Feed(
...     title=u"Poynter E-Media Tidbits",
...     link=u"http://www.poynter.org/column.asp?id=31",
...     description=u"A group Weblog by the sharpest minds in online media/journalism/publishing.",
...     language=u"en",
... )
>>> feed.add_item(
...     title="Hello",
...     link=u"http://www.holovaty.com/test/",
...     description="Testing."
... )
>>> fp = open('test.rss', 'w')
>>> feed.write(fp, 'utf-8')
>>> fp.close()

For definitions of the different versions of RSS, see:
http://diveintomark.org/archives/2004/02/04/incompatible-rss
"""

import datetime
import urlparse
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.encoding import force_unicode, iri_to_uri

def rfc2822_date(date):
    # We do this ourselves to be timezone aware, email.Utils is not tz aware.
    if date.tzinfo:
        time_str = date.strftime('%a, %d %b %Y %H:%M:%S ')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d%02d" % (hour, minute)
    else:
        return date.strftime('%a, %d %b %Y %H:%M:%S -0000')

def rfc3339_date(date):
    if date.tzinfo:
        time_str = date.strftime('%Y-%m-%dT%H:%M:%S')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d:%02d" % (hour, minute)
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_tag_uri(url, date):
    """
    Creates a TagURI.

    See http://diveintomark.org/archives/2004/05/28/howto-atom-id
    """
    url_split = urlparse.urlparse(url)

    # Python 2.4 didn't have named attributes on split results or the hostname.
    hostname = getattr(url_split, 'hostname', url_split[1].split(':')[0])
    path = url_split[2]
    fragment = url_split[5]

    d = ''
    if date is not None:
        d = ',%s' % date.strftime('%Y-%m-%d')
    return u'tag:%s%s:%s/%s' % (hostname, d, path, fragment)

class SyndicationFeed(object):
    "Base class for all syndication feeds. Subclasses should provide write()"
    def __init__(self, title, link, description, language=None, author_email=None,
            author_name=None, author_link=None, subtitle=None, categories=None,
            feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs):
        to_unicode = lambda s: force_unicode(s, strings_only=True)
        if categories:
            categories = [force_unicode(c) for c in categories]
        if ttl is not None:
            # Force ints to unicode
            ttl = force_unicode(ttl)
        self.feed = {
            'title': to_unicode(title),
            'link': iri_to_uri(link),
            'description': to_unicode(description),
            'language': to_unicode(language),
            'author_email': to_unicode(author_email),
            'author_name': to_unicode(author_name),
            'author_link': iri_to_uri(author_link),
            'subtitle': to_unicode(subtitle),
            'categories': categories or (),
            'feed_url': iri_to_uri(feed_url),
            'feed_copyright': to_unicode(feed_copyright),
            'id': feed_guid or link,
            'ttl': ttl,
        }
        self.feed.update(kwargs)
        self.items = []

    def add_item(self, title, link, description, author_email=None,
        author_name=None, author_link=None, pubdate=None, comments=None,
        unique_id=None, enclosure=None, categories=(), item_copyright=None,
        ttl=None, **kwargs):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        to_unicode = lambda s: force_unicode(s, strings_only=True)
        if categories:
            categories = [to_unicode(c) for c in categories]
        if ttl is not None:
            # Force ints to unicode
            ttl = force_unicode(ttl)
        item = {
            'title': to_unicode(title),
            'link': iri_to_uri(link),
            'description': to_unicode(description),
            'author_email': to_unicode(author_email),
            'author_name': to_unicode(author_name),
            'author_link': iri_to_uri(author_link),
            'pubdate': pubdate,
            'comments': to_unicode(comments),
            'unique_id': to_unicode(unique_id),
            'enclosure': enclosure,
            'categories': categories or (),
            'item_copyright': to_unicode(item_copyright),
            'ttl': ttl,
        }
        item.update(kwargs)
        self.items.append(item)

    def num_items(self):
        return len(self.items)

    def root_attributes(self):
        """
        Return extra attributes to place on the root (i.e. feed/channel) element.
        Called from write().
        """
        return {}

    def add_root_elements(self, handler):
        """
        Add elements in the root (i.e. feed/channel) element. Called
        from write().
        """
        pass

    def item_attributes(self, item):
        """
        Return extra attributes to place on each item (i.e. item/entry) element.
        """
        return {}

    def add_item_elements(self, handler, item):
        """
        Add elements on each item (i.e. item/entry) element.
        """
        pass

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

class Enclosure(object):
    "Represents an RSS enclosure"
    def __init__(self, url, length, mime_type):
        "All args are expected to be Python Unicode objects"
        self.length, self.mime_type = length, mime_type
        self.url = iri_to_uri(url)

class RssFeed(SyndicationFeed):
    mime_type = 'application/rss+xml'
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        handler.startElement(u"rss", self.rss_attributes())
        handler.startElement(u"channel", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement(u"rss")

    def rss_attributes(self):
        return {u"version": self._version,
                u"xmlns:atom": u"http://www.w3.org/2005/Atom"}

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u'item', self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement(u"item")

    def add_root_elements(self, handler):
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", self.feed['link'])
        handler.addQuickElement(u"description", self.feed['description'])
        handler.addQuickElement(u"atom:link", None, {u"rel": u"self", u"href": self.feed['feed_url']})
        if self.feed['language'] is not None:
            handler.addQuickElement(u"language", self.feed['language'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", cat)
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"copyright", self.feed['feed_copyright'])
        handler.addQuickElement(u"lastBuildDate", rfc2822_date(self.latest_post_date()).decode('utf-8'))
        if self.feed['ttl'] is not None:
            handler.addQuickElement(u"ttl", self.feed['ttl'])

    def endChannelElement(self, handler):
        handler.endElement(u"channel")

class RssUserland091Feed(RssFeed):
    _version = u"0.91"
    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", item['link'])
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'])

class Rss201rev2Feed(RssFeed):
    # Spec: http://blogs.law.harvard.edu/tech/rss
    _version = u"2.0"
    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", item['link'])
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'])

        # Author information.
        if item["author_name"] and item["author_email"]:
            handler.addQuickElement(u"author", "%s (%s)" % \
                (item['author_email'], item['author_name']))
        elif item["author_email"]:
            handler.addQuickElement(u"author", item["author_email"])
        elif item["author_name"]:
            handler.addQuickElement(u"dc:creator", item["author_name"], {u"xmlns:dc": u"http://purl.org/dc/elements/1.1/"})

        if item['pubdate'] is not None:
            handler.addQuickElement(u"pubDate", rfc2822_date(item['pubdate']).decode('utf-8'))
        if item['comments'] is not None:
            handler.addQuickElement(u"comments", item['comments'])
        if item['unique_id'] is not None:
            handler.addQuickElement(u"guid", item['unique_id'])
        if item['ttl'] is not None:
            handler.addQuickElement(u"ttl", item['ttl'])

        # Enclosure.
        if item['enclosure'] is not None:
            handler.addQuickElement(u"enclosure", '',
                {u"url": item['enclosure'].url, u"length": item['enclosure'].length,
                    u"type": item['enclosure'].mime_type})

        # Categories.
        for cat in item['categories']:
            handler.addQuickElement(u"category", cat)

class Atom1Feed(SyndicationFeed):
    # Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    mime_type = 'application/atom+xml'
    ns = u"http://www.w3.org/2005/Atom"

    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        handler.startElement(u'feed', self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        handler.endElement(u"feed")

    def root_attributes(self):
        if self.feed['language'] is not None:
            return {u"xmlns": self.ns, u"xml:lang": self.feed['language']}
        else:
            return {u"xmlns": self.ns}

    def add_root_elements(self, handler):
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", "", {u"rel": u"alternate", u"href": self.feed['link']})
        if self.feed['feed_url'] is not None:
            handler.addQuickElement(u"link", "", {u"rel": u"self", u"href": self.feed['feed_url']})
        handler.addQuickElement(u"id", self.feed['id'])
        handler.addQuickElement(u"updated", rfc3339_date(self.latest_post_date()).decode('utf-8'))
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
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"rights", self.feed['feed_copyright'])

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"entry", self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement(u"entry")

    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", u"", {u"href": item['link'], u"rel": u"alternate"})
        if item['pubdate'] is not None:
            handler.addQuickElement(u"updated", rfc3339_date(item['pubdate']).decode('utf-8'))

        # Author information.
        if item['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", item['author_name'])
            if item['author_email'] is not None:
                handler.addQuickElement(u"email", item['author_email'])
            if item['author_link'] is not None:
                handler.addQuickElement(u"uri", item['author_link'])
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

        # Categories.
        for cat in item['categories']:
            handler.addQuickElement(u"category", u"", {u"term": cat})

        # Rights.
        if item['item_copyright'] is not None:
            handler.addQuickElement(u"rights", item['item_copyright'])

# This isolates the decision of what the system default is, so calling code can
# do "feedgenerator.DefaultFeed" instead of "feedgenerator.Rss201rev2Feed".
DefaultFeed = Rss201rev2Feed
