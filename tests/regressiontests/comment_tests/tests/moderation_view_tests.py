from django.contrib.comments.models import Comment, CommentFlag
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from regressiontests.comment_tests.tests import CommentTestCase
from django.contrib.comments import signals

class FlagViewTests(CommentTestCase):

    def testFlagGet(self):
        """GET the flag view: render a confirmation page."""
        self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/flag/1/")
        self.assertTemplateUsed(response, "comments/flag.html")

    def testFlagPost(self):
        """POST the flag view: actually flag the view (nice for XHR)"""
        self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/flag/1/")
        self.assertEqual(response["Location"], "http://testserver/flagged/?c=1")
        c = Comment.objects.get(pk=1)
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)
        return c

    def testFlagPostTwice(self):
        """Users don't get to flag comments more than once."""
        c = self.testFlagPost()
        self.client.post("/flag/1/")
        self.client.post("/flag/1/")
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)

    def testFlagAnon(self):
        """GET/POST the flag view while not logged in: redirect to log in."""
        self.createSomeComments()
        response = self.client.get("/flag/1/")
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/1/")
        response = self.client.post("/flag/1/")
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/1/")

    def testFlaggedView(self):
        self.createSomeComments()
        response = self.client.get("/flagged/", data={"c":1})
        self.assertTemplateUsed(response, "comments/flagged.html")

    def testFlagSignals(self):
        """Test signals emitted by the comment flag view"""

        # callback
        def receive(sender, **kwargs):
            flag = sender.flags.get(id=1)
            self.assertEqual(flag.flag, CommentFlag.SUGGEST_REMOVAL)
            self.assertEqual(flag.user.username, "normaluser")
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testFlagPost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

def makeModerator(username):
    u = User.objects.get(username=username)
    ct = ContentType.objects.get_for_model(Comment)
    p = Permission.objects.get(content_type=ct, codename="can_moderate")
    u.user_permissions.add(p)

class DeleteViewTests(CommentTestCase):

    def testDeletePermissions(self):
        """The delete view should only be accessible to 'moderators'"""
        self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/delete/1/")
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/delete/1/")

        makeModerator("normaluser")
        response = self.client.get("/delete/1/")
        self.assertEqual(response.status_code, 200)

    def testDeletePost(self):
        """POSTing the delete view should mark the comment as removed"""
        self.createSomeComments()
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/delete/1/")
        self.assertEqual(response["Location"], "http://testserver/deleted/?c=1")
        c = Comment.objects.get(pk=1)
        self.failUnless(c.is_removed)
        self.assertEqual(c.flags.filter(flag=CommentFlag.MODERATOR_DELETION, user__username="normaluser").count(), 1)

    def testDeleteSignals(self):
        def receive(sender, **kwargs):
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testDeletePost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

    def testDeletedView(self):
        self.createSomeComments()
        response = self.client.get("/deleted/", data={"c":1})
        self.assertTemplateUsed(response, "comments/deleted.html")

class ApproveViewTests(CommentTestCase):

    def testApprovePermissions(self):
        """The delete view should only be accessible to 'moderators'"""
        self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/approve/1/")
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/approve/1/")

        makeModerator("normaluser")
        response = self.client.get("/approve/1/")
        self.assertEqual(response.status_code, 200)

    def testApprovePost(self):
        """POSTing the delete view should mark the comment as removed"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False; c1.save()

        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/approve/1/")
        self.assertEqual(response["Location"], "http://testserver/approved/?c=1")
        c = Comment.objects.get(pk=1)
        self.failUnless(c.is_public)
        self.assertEqual(c.flags.filter(flag=CommentFlag.MODERATOR_APPROVAL, user__username="normaluser").count(), 1)

    def testApproveSignals(self):
        def receive(sender, **kwargs):
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testApprovePost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

    def testApprovedView(self):
        self.createSomeComments()
        response = self.client.get("/approved/", data={"c":1})
        self.assertTemplateUsed(response, "comments/approved.html")


class ModerationQueueTests(CommentTestCase):

    def testModerationQueuePermissions(self):
        """Only moderators can view the moderation queue"""
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/moderate/")
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/moderate/")

        makeModerator("normaluser")
        response = self.client.get("/moderate/")
        self.assertEqual(response.status_code, 200)

    def testModerationQueueContents(self):
        """Moderation queue should display non-public, non-removed comments."""
        c1, c2, c3, c4 = self.createSomeComments()
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")

        c1.is_public = c2.is_public = False
        c1.save(); c2.save()
        response = self.client.get("/moderate/")
        self.assertEqual(list(response.context[0]["comments"]), [c1, c2])

        c2.is_removed = True
        c2.save()
        response = self.client.get("/moderate/")
        self.assertEqual(list(response.context[0]["comments"]), [c1])
