from django.conf import settings
from django.contrib import comments
from django.contrib.comments.models import Comment
from django.contrib.comments.forms import CommentForm
from django.core.apps import app_cache
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings
from django.utils import six

from . import CommentTestCase


class CommentAppAPITests(CommentTestCase):
    """Tests for the "comment app" API"""

    def testGetCommentApp(self):
        self.assertEqual(comments.get_comment_app(), comments)

    def testGetForm(self):
        self.assertEqual(comments.get_form(), CommentForm)

    def testGetFormTarget(self):
        self.assertEqual(comments.get_form_target(), "/post/")

    def testGetFlagURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_flag_url(c), "/flag/12345/")

    def getGetDeleteURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_delete_url(c), "/delete/12345/")

    def getGetApproveURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_approve_url(c), "/approve/12345/")


@override_settings(COMMENTS_APP='comment_tests.custom_comments')
class CustomCommentTest(CommentTestCase):
    urls = 'comment_tests.urls'

    def setUp(self):
        self._with_custom_comments = app_cache._begin_with_app('comment_tests.custom_comments')

    def tearDown(self):
        app_cache._end_with_app(self._with_custom_comments)

    def testGetCommentApp(self):
        from comment_tests import custom_comments
        self.assertEqual(comments.get_comment_app(), custom_comments)

    def testGetModel(self):
        from comment_tests.custom_comments.models import CustomComment
        self.assertEqual(comments.get_model(), CustomComment)

    def testGetForm(self):
        from comment_tests.custom_comments.forms import CustomCommentForm
        self.assertEqual(comments.get_form(), CustomCommentForm)

    def testGetFormTarget(self):
        self.assertEqual(comments.get_form_target(), "/post/")

    def testGetFlagURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_flag_url(c), "/flag/12345/")

    def getGetDeleteURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_delete_url(c), "/delete/12345/")

    def getGetApproveURL(self):
        c = Comment(id=12345)
        self.assertEqual(comments.get_approve_url(c), "/approve/12345/")
