from __future__ import absolute_import

from xml.etree import ElementTree as ET

from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from . import CommentTestCase
from ..models import Article


class CommentFeedTests(CommentTestCase):
    urls = 'regressiontests.comment_tests.urls'
    feed_url = '/rss/comments/'

    def setUp(self):
        site_2 = Site.objects.create(id=settings.SITE_ID+1,
            domain="example2.com", name="example2.com")
        # A comment for another site
        c5 = Comment.objects.create(
            content_type = ContentType.objects.get_for_model(Article),
            object_pk = "1",
            user_name = "Joe Somebody",
            user_email = "jsomebody@example.com",
            user_url = "http://example.com/~joe/",
            comment = "A comment for the second site.",
            site = site_2,
        )

    def test_feed(self):
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/rss+xml; charset=utf-8')

        rss_elem = ET.fromstring(response.content)

        self.assertEqual(rss_elem.tag, "rss")
        self.assertEqual(rss_elem.attrib, {"version": "2.0"})

        channel_elem = rss_elem.find("channel")

        title_elem = channel_elem.find("title")
        self.assertEqual(title_elem.text, "example.com comments")

        link_elem = channel_elem.find("link")
        self.assertEqual(link_elem.text, "http://example.com/")

        atomlink_elem = channel_elem.find("{http://www.w3.org/2005/Atom}link")
        self.assertEqual(atomlink_elem.attrib, {"href": "http://example.com/rss/comments/", "rel": "self"})

        self.assertNotContains(response, "A comment for the second site.")
