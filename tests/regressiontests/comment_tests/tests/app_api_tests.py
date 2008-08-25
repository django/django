from django.conf import settings
from django.contrib import comments
from django.contrib.comments.models import Comment
from django.contrib.comments.forms import CommentForm
from regressiontests.comment_tests.tests import CommentTestCase

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

