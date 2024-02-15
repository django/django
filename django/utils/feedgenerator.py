"""
Syndication feed generation library -- used for generating RSS, etc.

Sample usage:

>>> from django.utils import feedgenerator
>>> feed = feedgenerator.Rss201rev2Feed(
...     title="Poynter E-Media Tidbits",
...     link="http://www.poynter.org/column.asp?id=31",
...     description="A group blog by the sharpest minds in online journalism.",
...     language="en",
... )
>>> feed.add_item(
...     title="Hello",
...     link="http://www.holovaty.com/test/",
...     description="Testing."
... )
>>> with open('test.rss', 'w') as fp:
...     feed.write(fp, 'utf-8')

For definitions of the different versions of RSS, see:
https://web.archive.org/web/20110718035220/http://diveintomark.org/archives/2004/02/04/incompatible-rss
"""

import datetime
import email
from io import StringIO
from urllib.parse import urlparse

from django.utils.encoding import iri_to_uri
from django.utils.xmlutils import SimplerXMLGenerator


def rfc2822_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time())
    return email.utils.format_datetime(date)


def rfc3339_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time())
    return date.isoformat() + ("Z" if date.utcoffset() is None else "")


def get_tag_uri(url, date):
    """
    Create a TagURI.

    See
    https://web.archive.org/web/20110514113830/http://diveintomark.org/archives/2004/05/28/howto-atom-id
    """
    bits = urlparse(url)
    d = ""
    if date is not None:
        d = ",%s" % date.strftime("%Y-%m-%d")
    return "tag:%s%s:%s/%s" % (bits.hostname, d, bits.path, bits.fragment)


class SyndicationFeed:
    "Base class for all syndication feeds. Subclasses should provide write()"

    def __init__(
        self,
        title,
        link,
        description,
        language=None,
        author_email=None,
        author_name=None,
        author_link=None,
        subtitle=None,
        categories=None,
        feed_url=None,
        feed_copyright=None,
        feed_guid=None,
        ttl=None,
        **kwargs,
    ):
        def to_str(s):
            return str(s) if s is not None else s

        categories = categories and [str(c) for c in categories]
        self.feed = {
            "title": to_str(title),
            "link": iri_to_uri(link),
            "description": to_str(description),
            "language": to_str(language),
            "author_email": to_str(author_email),
            "author_name": to_str(author_name),
            "author_link": iri_to_uri(author_link),
            "subtitle": to_str(subtitle),
            "categories": categories or (),
            "feed_url": iri_to_uri(feed_url),
            "feed_copyright": to_str(feed_copyright),
            "id": feed_guid or link,
            "ttl": to_str(ttl),
            **kwargs,
        }
        self.items = []

    def add_item(
        self,
        title,
        link,
        description,
        author_email=None,
        author_name=None,
        author_link=None,
        pubdate=None,
        comments=None,
        unique_id=None,
        unique_id_is_permalink=None,
        categories=(),
        item_copyright=None,
        ttl=None,
        updateddate=None,
        enclosures=None,
        **kwargs,
    ):
        """
        Add an item to the feed. All args are expected to be strings except
        pubdate and updateddate, which are datetime.datetime objects, and
        enclosures, which is an iterable of instances of the Enclosure class.
        """

        def to_str(s):
            return str(s) if s is not None else s

        categories = categories and [to_str(c) for c in categories]
        self.items.append(
            {
                "title": to_str(title),
                "link": iri_to_uri(link),
                "description": to_str(description),
                "author_email": to_str(author_email),
                "author_name": to_str(author_name),
                "author_link": iri_to_uri(author_link),
                "pubdate": pubdate,
                "updateddate": updateddate,
                "comments": to_str(comments),
                "unique_id": to_str(unique_id),
                "unique_id_is_permalink": unique_id_is_permalink,
                "enclosures": enclosures or (),
                "categories": categories or (),
                "item_copyright": to_str(item_copyright),
                "ttl": to_str(ttl),
                **kwargs,
            }
        )

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
        Output the feed in the given encoding to outfile, which is a file-like
        object. Subclasses should override this.
        """
        raise NotImplementedError(
            "subclasses of SyndicationFeed must provide a write() method"
        )

    def writeString(self, encoding):
        """
        Return the feed in the given encoding as a string.
        """
        s = StringIO()
        self.write(s, encoding)
        return s.getvalue()

    def latest_post_date(self):
        """
        Return the latest item's pubdate or updateddate. If no items
        have either of these attributes this return the current UTC date/time.
        """
        latest_date = None
        date_keys = ("updateddate", "pubdate")

        for item in self.items:
            for date_key in date_keys:
                item_date = item.get(date_key)
                if item_date:
                    if latest_date is None or item_date > latest_date:
                        latest_date = item_date

        return latest_date or datetime.datetime.now(tz=datetime.timezone.utc)


class Enclosure:
    """An RSS enclosure"""

    def __init__(self, url, length, mime_type):
        "All args are expected to be strings"
        self.length, self.mime_type = length, mime_type
        self.url = iri_to_uri(url)


class RssFeed(SyndicationFeed):
    content_type = "application/rss+xml; charset=utf-8"

    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding, short_empty_elements=True)
        handler.startDocument()
        handler.startElement("rss", self.rss_attributes())
        handler.startElement("channel", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement("rss")

    def rss_attributes(self):
        return {
            "version": self._version,
            "xmlns:atom": "http://www.w3.org/2005/Atom",
        }

    def write_items(self, handler):
        for item in self.items:
            handler.startElement("item", self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement("item")

    def add_root_elements(self, handler):
        handler.addQuickElement("title", self.feed["title"])
        handler.addQuickElement("link", self.feed["link"])
        handler.addQuickElement("description", self.feed["description"])
        if self.feed["feed_url"] is not None:
            handler.addQuickElement(
                "atom:link", None, {"rel": "self", "href": self.feed["feed_url"]}
            )
        if self.feed["language"] is not None:
            handler.addQuickElement("language", self.feed["language"])
        for cat in self.feed["categories"]:
            handler.addQuickElement("category", cat)
        if self.feed["feed_copyright"] is not None:
            handler.addQuickElement("copyright", self.feed["feed_copyright"])
        handler.addQuickElement("lastBuildDate", rfc2822_date(self.latest_post_date()))
        if self.feed["ttl"] is not None:
            handler.addQuickElement("ttl", self.feed["ttl"])

    def endChannelElement(self, handler):
        handler.endElement("channel")


class RssUserland091Feed(RssFeed):
    _version = "0.91"

    def add_item_elements(self, handler, item):
        handler.addQuickElement("title", item["title"])
        handler.addQuickElement("link", item["link"])
        if item["description"] is not None:
            handler.addQuickElement("description", item["description"])


class Rss201rev2Feed(RssFeed):
    # Spec: https://cyber.harvard.edu/rss/rss.html
    _version = "2.0"

    def add_item_elements(self, handler, item):
        handler.addQuickElement("title", item["title"])
        handler.addQuickElement("link", item["link"])
        if item["description"] is not None:
            handler.addQuickElement("description", item["description"])

        # Author information.
        if item["author_name"] and item["author_email"]:
            handler.addQuickElement(
                "author", "%s (%s)" % (item["author_email"], item["author_name"])
            )
        elif item["author_email"]:
            handler.addQuickElement("author", item["author_email"])
        elif item["author_name"]:
            handler.addQuickElement(
                "dc:creator",
                item["author_name"],
                {"xmlns:dc": "http://purl.org/dc/elements/1.1/"},
            )

        if item["pubdate"] is not None:
            handler.addQuickElement("pubDate", rfc2822_date(item["pubdate"]))
        if item["comments"] is not None:
            handler.addQuickElement("comments", item["comments"])
        if item["unique_id"] is not None:
            guid_attrs = {}
            if isinstance(item.get("unique_id_is_permalink"), bool):
                guid_attrs["isPermaLink"] = str(item["unique_id_is_permalink"]).lower()
            handler.addQuickElement("guid", item["unique_id"], guid_attrs)
        if item["ttl"] is not None:
            handler.addQuickElement("ttl", item["ttl"])

        # Enclosure.
        if item["enclosures"]:
            enclosures = list(item["enclosures"])
            if len(enclosures) > 1:
                raise ValueError(
                    "RSS feed items may only have one enclosure, see "
                    "http://www.rssboard.org/rss-profile#element-channel-item-enclosure"
                )
            enclosure = enclosures[0]
            handler.addQuickElement(
                "enclosure",
                "",
                {
                    "url": enclosure.url,
                    "length": enclosure.length,
                    "type": enclosure.mime_type,
                },
            )

        # Categories.
        for cat in item["categories"]:
            handler.addQuickElement("category", cat)


class Atom1Feed(SyndicationFeed):
    # Spec: https://tools.ietf.org/html/rfc4287
    content_type = "application/atom+xml; charset=utf-8"
    ns = "http://www.w3.org/2005/Atom"

    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding, short_empty_elements=True)
        handler.startDocument()
        handler.startElement("feed", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        handler.endElement("feed")

    def root_attributes(self):
        if self.feed["language"] is not None:
            return {"xmlns": self.ns, "xml:lang": self.feed["language"]}
        else:
            return {"xmlns": self.ns}

    def add_root_elements(self, handler):
        handler.addQuickElement("title", self.feed["title"])
        handler.addQuickElement(
            "link", "", {"rel": "alternate", "href": self.feed["link"]}
        )
        if self.feed["feed_url"] is not None:
            handler.addQuickElement(
                "link", "", {"rel": "self", "href": self.feed["feed_url"]}
            )
        handler.addQuickElement("id", self.feed["id"])
        handler.addQuickElement("updated", rfc3339_date(self.latest_post_date()))
        if self.feed["author_name"] is not None:
            handler.startElement("author", {})
            handler.addQuickElement("name", self.feed["author_name"])
            if self.feed["author_email"] is not None:
                handler.addQuickElement("email", self.feed["author_email"])
            if self.feed["author_link"] is not None:
                handler.addQuickElement("uri", self.feed["author_link"])
            handler.endElement("author")
        if self.feed["subtitle"] is not None:
            handler.addQuickElement("subtitle", self.feed["subtitle"])
        for cat in self.feed["categories"]:
            handler.addQuickElement("category", "", {"term": cat})
        if self.feed["feed_copyright"] is not None:
            handler.addQuickElement("rights", self.feed["feed_copyright"])

    def write_items(self, handler):
        for item in self.items:
            handler.startElement("entry", self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement("entry")

    def add_item_elements(self, handler, item):
        handler.addQuickElement("title", item["title"])
        handler.addQuickElement("link", "", {"href": item["link"], "rel": "alternate"})

        if item["pubdate"] is not None:
            handler.addQuickElement("published", rfc3339_date(item["pubdate"]))

        if item["updateddate"] is not None:
            handler.addQuickElement("updated", rfc3339_date(item["updateddate"]))

        # Author information.
        if item["author_name"] is not None:
            handler.startElement("author", {})
            handler.addQuickElement("name", item["author_name"])
            if item["author_email"] is not None:
                handler.addQuickElement("email", item["author_email"])
            if item["author_link"] is not None:
                handler.addQuickElement("uri", item["author_link"])
            handler.endElement("author")

        # Unique ID.
        if item["unique_id"] is not None:
            unique_id = item["unique_id"]
        else:
            unique_id = get_tag_uri(item["link"], item["pubdate"])
        handler.addQuickElement("id", unique_id)

        # Summary.
        if item["description"] is not None:
            handler.addQuickElement("summary", item["description"], {"type": "html"})

        # Enclosures.
        for enclosure in item["enclosures"]:
            handler.addQuickElement(
                "link",
                "",
                {
                    "rel": "enclosure",
                    "href": enclosure.url,
                    "length": enclosure.length,
                    "type": enclosure.mime_type,
                },
            )

        # Categories.
        for cat in item["categories"]:
            handler.addQuickElement("category", "", {"term": cat})

        # Rights.
        if item["item_copyright"] is not None:
            handler.addQuickElement("rights", item["item_copyright"])


# This isolates the decision of what the system default is, so calling code can
# do "feedgenerator.DefaultFeed" instead of "feedgenerator.Rss201rev2Feed".
DefaultFeed = Rss201rev2Feed
