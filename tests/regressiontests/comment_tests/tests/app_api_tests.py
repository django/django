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


class CustomCommentTest(CommentTestCase):
    urls = 'regressiontests.comment_tests.urls'

    def setUp(self):
        self.old_comments_app = getattr(settings, 'COMMENTS_APP', None)
        settings.COMMENTS_APP = 'regressiontests.comment_tests.custom_comments'
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [settings.COMMENTS_APP,]

    def tearDown(self):
        del settings.INSTALLED_APPS[-1]
        settings.COMMENTS_APP = self.old_comments_app
        if settings.COMMENTS_APP is None:
            del settings._wrapped.COMMENTS_APP

    def testGetCommentApp(self):
        from regressiontests.comment_tests import custom_comments
        self.assertEqual(comments.get_comment_app(), custom_comments)

    def testGetModel(self):
        from regressiontests.comment_tests.custom_comments.models import CustomComment
        self.assertEqual(comments.get_model(), CustomComment)

    def testGetForm(self):
        from regressiontests.comment_tests.custom_comments.forms import CustomCommentForm
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
