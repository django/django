from __future__ import absolute_import

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
        self.assertContains(response, '<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0">')
        self.assertContains(response, '<title>example.com comments</title>')
        self.assertContains(response, '<link>http://example.com/</link>')
        self.assertContains(response, '</rss>')
        self.assertNotContains(response, "A comment for the second site.")
