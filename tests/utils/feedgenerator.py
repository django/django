from __future__ import unicode_literals

import datetime

from django.utils import feedgenerator, tzinfo, unittest

class FeedgeneratorTest(unittest.TestCase):
    """
    Tests for the low-level syndication feed framework.
    """

    def test_get_tag_uri(self):
        """
        Test get_tag_uri() correctly generates TagURIs.
        """
        self.assertEqual(
            feedgenerator.get_tag_uri('http://example.org/foo/bar#headline', datetime.date(2004, 10, 25)),
            'tag:example.org,2004-10-25:/foo/bar/headline')

    def test_get_tag_uri_with_port(self):
        """
        Test that get_tag_uri() correctly generates TagURIs from URLs with port
        numbers.
        """
        self.assertEqual(
            feedgenerator.get_tag_uri('http://www.example.org:8000/2008/11/14/django#headline', datetime.datetime(2008, 11, 14, 13, 37, 0)),
            'tag:www.example.org,2008-11-14:/2008/11/14/django/headline')

    def test_rfc2822_date(self):
        """
        Test rfc2822_date() correctly formats datetime objects.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.datetime(2008, 11, 14, 13, 37, 0)),
            "Fri, 14 Nov 2008 13:37:00 -0000"
        )

    def test_rfc2822_date_with_timezone(self):
        """
        Test rfc2822_date() correctly formats datetime objects with tzinfo.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.datetime(2008, 11, 14, 13, 37, 0, tzinfo=tzinfo.FixedOffset(datetime.timedelta(minutes=60)))),
            "Fri, 14 Nov 2008 13:37:00 +0100"
        )

    def test_rfc2822_date_without_time(self):
        """
        Test rfc2822_date() correctly formats date objects.
        """
        self.assertEqual(
            feedgenerator.rfc2822_date(datetime.date(2008, 11, 14)),
            "Fri, 14 Nov 2008 00:00:00 -0000"
        )

    def test_rfc3339_date(self):
        """
        Test rfc3339_date() correctly formats datetime objects.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.datetime(2008, 11, 14, 13, 37, 0)),
            "2008-11-14T13:37:00Z"
        )

    def test_rfc3339_date_with_timezone(self):
        """
        Test rfc3339_date() correctly formats datetime objects with tzinfo.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.datetime(2008, 11, 14, 13, 37, 0, tzinfo=tzinfo.FixedOffset(datetime.timedelta(minutes=120)))),
            "2008-11-14T13:37:00+02:00"
        )

    def test_rfc3339_date_without_time(self):
        """
        Test rfc3339_date() correctly formats date objects.
        """
        self.assertEqual(
            feedgenerator.rfc3339_date(datetime.date(2008, 11, 14)),
            "2008-11-14T00:00:00Z"
        )

    def test_atom1_mime_type(self):
        """
        Test to make sure Atom MIME type has UTF8 Charset parameter set
        """
        atom_feed = feedgenerator.Atom1Feed("title", "link", "description")
        self.assertEqual(
            atom_feed.mime_type, "application/atom+xml; charset=utf-8"
        )

    def test_rss_mime_type(self):
        """
        Test to make sure RSS MIME type has UTF8 Charset parameter set
        """
        rss_feed = feedgenerator.Rss201rev2Feed("title", "link", "description")
        self.assertEqual(
            rss_feed.mime_type, "application/rss+xml; charset=utf-8"
        )

    # Two regression tests for #14202

    def test_feed_without_feed_url_gets_rendered_without_atom_link(self):
        feed = feedgenerator.Rss201rev2Feed('title', '/link/', 'descr')
        self.assertEqual(feed.feed['feed_url'], None)
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
