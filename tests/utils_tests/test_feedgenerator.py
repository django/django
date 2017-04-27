import datetime
import unittest

from django.test import TestCase
from django.utils import feedgenerator
from django.utils.timezone import get_fixed_timezone, utc
from django.utils.translation import gettext_lazy as _


class FeedgeneratorTest(unittest.TestCase):
    """
    Tests for the low-level syndication feed framework.
    """

    def test_get_tag_uri(self):
        """
        get_tag_uri() correctly generates TagURIs.
        """
        self.assertEqual(
            feedgenerator.get_tag_uri('http://example.org/foo/bar#headline', datetime.date(2004, 10, 25)),
            'tag:example.org,2004-10-25:/foo/bar/headline')

    def test_get_tag_uri_with_port(self):
        """
        get_tag_uri() correctly generates TagURIs from URLs with port numbers.
        """
        self.assertEqual(
            feedgenerator.get_tag_uri(
                'http://www.example.org:8000/2008/11/14/django#headline',
                datetime.datetime(2008, 11, 14, 13, 37, 0),
            ),
            'tag:www.example.org,2008-11-14:/2008/11/14/django/headline')

    def test_rfc2822_date(self):
        """
        rfc2822_date() correctly formats datetime objects.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.datetime(2008, 11, 14, 13, 37, 0)),
            "Fri, 14 Nov 2008 13:37:00 -0000"
        )

    def test_rfc2822_date_with_timezone(self):
        """
        rfc2822_date() correctly formats datetime objects with tzinfo.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.datetime(2008, 11, 14, 13, 37, 0, tzinfo=get_fixed_timezone(60))),
            "Fri, 14 Nov 2008 13:37:00 +0100"
        )

    def test_rfc2822_date_without_time(self):
        """
        rfc2822_date() correctly formats date objects.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.date(2008, 11, 14)),
            "Fri, 14 Nov 2008 00:00:00 -0000"
        )

    def test_rfc3339_date(self):
        """
        rfc3339_date() correctly formats datetime objects.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.datetime(2008, 11, 14, 13, 37, 0)),
            "2008-11-14T13:37:00Z"
        )

    def test_rfc3339_date_with_timezone(self):
        """
        rfc3339_date() correctly formats datetime objects with tzinfo.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.datetime(2008, 11, 14, 13, 37, 0, tzinfo=get_fixed_timezone(120))),
            "2008-11-14T13:37:00+02:00"
        )

    def test_rfc3339_date_without_time(self):
        """
        rfc3339_date() correctly formats date objects.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.date(2008, 11, 14)),
            "2008-11-14T00:00:00Z"
        )

    def test_atom1_mime_type(self):
        """
        Atom MIME type has UTF8 Charset parameter set
        """
        atom_feed = feedgenerator.Atom1Feed("title", "link", "description")
        self.assertEqual(
            atom_feed.content_type, "application/atom+xml; charset=utf-8"
        )

    def test_rss_mime_type(self):
        """
        RSS MIME type has UTF8 Charset parameter set
        """
        rss_feed = feedgenerator.Rss201rev2Feed("title", "link", "description")
        self.assertEqual(
            rss_feed.content_type, "application/rss+xml; charset=utf-8"
        )

    # Two regression tests for #14202

    def test_feed_without_feed_url_gets_rendered_without_atom_link(self):
        feed = feedgenerator.Rss201rev2Feed('title', '/link/', 'descr')
        self.assertIsNone(feed.feed['feed_url'])
        feed_content = feed.writeString('utf-8')
        self.assertNotIn('<atom:link', feed_content)
        self.assertNotIn('href="/feed/"', feed_content)
        self.assertNotIn('rel="self"', feed_content)

    def test_feed_with_feed_url_gets_rendered_with_atom_link(self):
        feed = feedgenerator.Rss201rev2Feed('title', '/link/', 'descr', feed_url='/feed/')
        self.assertEqual(feed.feed['feed_url'], '/feed/')
        feed_content = feed.writeString('utf-8')
        self.assertIn('<atom:link', feed_content)
        self.assertIn('href="/feed/"', feed_content)
        self.assertIn('rel="self"', feed_content)

    def test_atom_add_item(self):
        # Not providing any optional arguments to Atom1Feed.add_item()
        feed = feedgenerator.Atom1Feed('title', '/link/', 'descr')
        feed.add_item('item_title', 'item_link', 'item_description')
        feed.writeString('utf-8')


class CategoryTest(unittest.TestCase):
    """
    Tests for category object support in low-level syndication feed framework.
    """

    def test_can_be_instantiated_with_one_argument(self):
        term = 'django'
        cat = feedgenerator.Category(term)
        self.assertEqual(cat.term, term)
        self.assertIsNone(cat.label)
        self.assertIsNone(cat.scheme)
        self.assertIsNone(cat.domain)

    def test_arguments_can_be_lazy(self):
        term, scheme, label = _('term'), _('scheme'), _('label')
        cat = feedgenerator.Category(term, scheme=scheme, label=label)
        self.assertEqual(cat.term, str(term))
        self.assertEqual(cat.label, str(label))
        self.assertEqual(cat.scheme, str(scheme))

    def test_label_is_none_is_not_provided(self):
        cat = feedgenerator.Category('term')
        self.assertIsNone(cat.label)

    def test_label_is_string_if_provided(self):
        label = 123
        cat = feedgenerator.Category('term', label=label)
        self.assertEqual(cat.label, str(label))

    def test_domain_is_used_if_scheme_is_not_provided(self):
        domain = '1'
        cat = feedgenerator.Category('term', domain=domain)
        self.assertEqual(cat.scheme, domain)
        self.assertEqual(cat.domain, domain)

    def test_scheme_is_used_if_domain_is_not_provided(self):
        scheme = '2'
        cat = feedgenerator.Category('term', scheme=scheme)
        self.assertEqual(cat.scheme, scheme)
        self.assertEqual(cat.domain, scheme)

    def test_scheme_is_used_if_domain_is_also_provided(self):
        scheme, domain = '1', '2'
        cat = feedgenerator.Category('term', scheme=scheme, domain=domain)
        self.assertEqual(cat.scheme, scheme)
        self.assertEqual(cat.domain, scheme)

    def test_atom_support(self):
        feed_categories = (feedgenerator.Category('etc', label=4), )
        item_categories = (feedgenerator.Category('in-item', scheme='thing'), )
        feed = feedgenerator.Atom1Feed(
            'title', 'link', 'description', categories=feed_categories)
        feed.add_item(
            'item_title', 'item_link', 'item_description',
            categories=item_categories)
        feed_content = feed.writeString('utf-8')
        self.assertIn('term="etc"', feed_content)
        self.assertIn('term="in-item"', feed_content)
        self.assertIn('label="4"', feed_content)
        self.assertIn('scheme="thing"', feed_content)

    def test_rss091_support(self):
        feed_categories = (feedgenerator.Category('etc', label=4), )
        item_categories = (feedgenerator.Category('in-item', scheme='thing'), )
        feed = feedgenerator.RssUserland091Feed(
            'title', 'link', 'description', categories=feed_categories)
        feed.add_item(
            'item_title', 'item_link', 'item_description',
            categories=item_categories)
        feed_content = feed.writeString('utf-8')
        self.assertIn('<category atom:label="4">etc</category>', feed_content)
        self.assertNotIn(
            '<category domain="thing">in-item</category>', feed_content)

    def test_rss2_support(self):
        feed_categories = (feedgenerator.Category('etc', label=4), )
        item_categories = (feedgenerator.Category('in-item', scheme='thing'), )
        feed = feedgenerator.Rss201rev2Feed(
            'title', 'link', 'description', categories=feed_categories)
        feed.add_item(
            'item_title', 'item_link', 'item_description',
            categories=item_categories)
        feed_content = feed.writeString('utf-8')
        self.assertIn('<category atom:label="4">etc</category>', feed_content)
        self.assertIn(
            '<category domain="thing">in-item</category>', feed_content)


class FeedgeneratorDBTest(TestCase):

    # setting the timezone requires a database query on PostgreSQL.
    def test_latest_post_date_returns_utc_time(self):
        for use_tz in (True, False):
            with self.settings(USE_TZ=use_tz):
                rss_feed = feedgenerator.Rss201rev2Feed('title', 'link', 'description')
                self.assertEqual(rss_feed.latest_post_date().tzinfo, utc)
