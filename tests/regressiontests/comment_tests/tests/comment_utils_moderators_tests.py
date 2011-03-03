from regressiontests.comment_tests.tests import CommentTestCase, CT, Site
from django.contrib.comments.forms import CommentForm
from django.contrib.comments.models import Comment
from django.contrib.comments.moderation import moderator, CommentModerator, AlreadyModerated
from regressiontests.comment_tests.models import Entry
from django.core import mail

class EntryModerator1(CommentModerator):
    email_notification = True

class EntryModerator2(CommentModerator):
    enable_field = 'enable_comments'

class EntryModerator3(CommentModerator):
    auto_close_field = 'pub_date'
    close_after = 7

class EntryModerator4(CommentModerator):
    auto_moderate_field = 'pub_date'
    moderate_after = 7

class EntryModerator5(CommentModerator):
    auto_moderate_field = 'pub_date'
    moderate_after = 0

class EntryModerator6(CommentModerator):
    auto_close_field = 'pub_date'
    close_after = 0

class CommentUtilsModeratorTests(CommentTestCase):
    fixtures = ["comment_utils.xml"]

    def createSomeComments(self):
        # Tests for the moderation signals must actually post data
        # through the comment views, because only the comment views
        # emit the custom signals moderation listens for.
        e = Entry.objects.get(pk=1)
        data = self.getValidData(e)

        self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")

        # We explicitly do a try/except to get the comment we've just
        # posted because moderation may have disallowed it, in which
        # case we can just return it as None.
        try:
            c1 = Comment.objects.all()[0]
        except IndexError:
            c1 = None

        self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")

        try:
            c2 = Comment.objects.all()[0]
        except IndexError:
            c2 = None
        return c1, c2

    def tearDown(self):
        moderator.unregister(Entry)

    def testRegisterExistingModel(self):
        moderator.register(Entry, EntryModerator1)
        self.assertRaises(AlreadyModerated, moderator.register, Entry, EntryModerator1)

    def testEmailNotification(self):
        moderator.register(Entry, EntryModerator1)
        self.createSomeComments()
        self.assertEqual(len(mail.outbox), 2)

    def testCommentsEnabled(self):
        moderator.register(Entry, EntryModerator2)
        self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 1)

    def testAutoCloseField(self):
        moderator.register(Entry, EntryModerator3)
        self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 0)

    def testAutoModerateField(self):
        moderator.register(Entry, EntryModerator4)
        c1, c2 = self.createSomeComments()
        self.assertEqual(c2.is_public, False)

    def testAutoModerateFieldImmediate(self):
        moderator.register(Entry, EntryModerator5)
        c1, c2 = self.createSomeComments()
        self.assertEqual(c2.is_public, False)

    def testAutoCloseFieldImmediate(self):
        moderator.register(Entry, EntryModerator6)
        c1, c2 = self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 0)