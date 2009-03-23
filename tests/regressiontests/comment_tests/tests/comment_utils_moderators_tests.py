from regressiontests.comment_tests.tests import CommentTestCase, CT, Site
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

class CommentUtilsModeratorTests(CommentTestCase):
    fixtures = ["comment_utils.xml"]

    def createSomeComments(self):
        c1 = Comment.objects.create(
            content_type = CT(Entry),
            object_pk = "1",
            user_name = "Joe Somebody",
            user_email = "jsomebody@example.com",
            user_url = "http://example.com/~joe/",
            comment = "First!",
            site = Site.objects.get_current(),
        )
        c2 = Comment.objects.create(
            content_type = CT(Entry),
            object_pk = "2",
            user_name = "Joe the Plumber",
            user_email = "joetheplumber@whitehouse.gov",
            user_url = "http://example.com/~joe/",
            comment = "Second!",
            site = Site.objects.get_current(),
        )
        return c1, c2

    def tearDown(self):
        moderator.unregister(Entry)

    def testRegisterExistingModel(self):
        moderator.register(Entry, EntryModerator1)
        self.assertRaises(AlreadyModerated, moderator.register, Entry, EntryModerator1)

    def testEmailNotification(self):
        moderator.register(Entry, EntryModerator1)
        c1, c2 = self.createSomeComments()
        self.assertEquals(len(mail.outbox), 2)

    def testCommentsEnabled(self):
        moderator.register(Entry, EntryModerator2)
        c1, c2 = self.createSomeComments()
        self.assertEquals(Comment.objects.all().count(), 1)

    def testAutoCloseField(self):
        moderator.register(Entry, EntryModerator3)
        c1, c2 = self.createSomeComments()
        self.assertEquals(Comment.objects.all().count(), 0)

    def testAutoModerateField(self):
        moderator.register(Entry, EntryModerator4)
        c1, c2 = self.createSomeComments()
        self.assertEquals(c2.is_public, False)
