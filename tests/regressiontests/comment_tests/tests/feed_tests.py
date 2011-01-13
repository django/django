import warnings

from django.test.utils import get_warnings_state, restore_warnings_state

from regressiontests.comment_tests.tests import CommentTestCase


class CommentFeedTests(CommentTestCase):
    urls = 'regressiontests.comment_tests.urls'
    feed_url = '/rss/comments/'

    def test_feed(self):
        response = self.client.get(self.feed_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/rss+xml')
        self.assertContains(response, '<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0">')
        self.assertContains(response, '<title>example.com comments</title>')
        self.assertContains(response, '<link>http://example.com/</link>')
        self.assertContains(response, '</rss>')


class LegacyCommentFeedTests(CommentFeedTests):
    feed_url = '/rss/legacy/comments/'

    def setUp(self):
        self._warnings_state = get_warnings_state()
        warnings.filterwarnings("ignore", category=DeprecationWarning,
                                module='django.contrib.syndication.views')
        warnings.filterwarnings("ignore", category=DeprecationWarning,
                                module='django.contrib.syndication.feeds')

    def tearDown(self):
        restore_warnings_state(self._warnings_state)
