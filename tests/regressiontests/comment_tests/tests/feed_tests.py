from __future__ import absolute_import
from xml.etree import ElementTree as ET
from io import BytesIO
from . import CommentTestCase


class CommentFeedTests(CommentTestCase):
    urls = 'regressiontests.comment_tests.urls'
    feed_url = '/rss/comments/'

    def test_feed(self):
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/rss+xml; charset=utf-8')

        doc = ET.parse(BytesIO(response.content))

        rss_elem = doc.getroot()
        self.assertEqual(rss_elem.tag, "rss")
        self.assertEqual(rss_elem.attrib, {"version": "2.0"})

        channel_elem = rss_elem.find("channel")

        title_elem = channel_elem.find("title")
        self.assertEqual(title_elem.text, "example.com comments")

        link_elem = channel_elem.find("link")
        self.assertEqual(link_elem.text, "http://example.com/")

        # check for Atom link
        atomlink_elem = channel_elem.find("{http://www.w3.org/2005/Atom}link")
        self.assertEqual(atomlink_elem.attrib, {"href": "http://example.com/rss/comments/", "rel": "self"})
