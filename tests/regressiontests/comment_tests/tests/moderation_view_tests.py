from django.contrib.comments.models import Comment, CommentFlag
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from regressiontests.comment_tests.tests import CommentTestCase
from django.contrib.comments import signals

class FlagViewTests(CommentTestCase):

    def testFlagGet(self):
        """GET the flag view: render a confirmation page."""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/flag/%d/" % pk)
        self.assertTemplateUsed(response, "comments/flag.html")

    def testFlagPost(self):
        """POST the flag view: actually flag the view (nice for XHR)"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/flagged/?c=%d" % pk)
        c = Comment.objects.get(pk=pk)
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)
        return c

    def testFlagPostTwice(self):
        """Users don't get to flag comments more than once."""
        c = self.testFlagPost()
        self.client.post("/flag/%d/" % c.pk)
        self.client.post("/flag/%d/" % c.pk)
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)

    def testFlagAnon(self):
        """GET/POST the flag view while not logged in: redirect to log in."""
        comments = self.createSomeComments()
        pk = comments[0].pk        
        response = self.client.get("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/%d/" % pk)
        response = self.client.post("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/%d/" % pk)

    def testFlaggedView(self):
        comments = self.createSomeComments()
        pk = comments[0].pk        
        response = self.client.get("/flagged/", data={"c":pk})
        self.assertTemplateUsed(response, "comments/flagged.html")

    def testFlagSignals(self):
        """Test signals emitted by the comment flag view"""

        # callback
        def receive(sender, **kwargs):
            self.assertEqual(kwargs['flag'].flag, CommentFlag.SUGGEST_REMOVAL)
            self.assertEqual(kwargs['request'].user.username, "normaluser")
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
        comments = self.createSomeComments()
        pk = comments[0].pk        
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/delete/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/delete/%d/" % pk)

        makeModerator("normaluser")
        response = self.client.get("/delete/%d/" % pk)
        self.assertEqual(response.status_code, 200)

    def testDeletePost(self):
        """POSTing the delete view should mark the comment as removed"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/delete/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/deleted/?c=%d" % pk)
        c = Comment.objects.get(pk=pk)
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
        comments = self.createSomeComments()
        pk = comments[0].pk        
        response = self.client.get("/deleted/", data={"c":pk})
        self.assertTemplateUsed(response, "comments/deleted.html")

class ApproveViewTests(CommentTestCase):

    def testApprovePermissions(self):
        """The delete view should only be accessible to 'moderators'"""
        comments = self.createSomeComments()
        pk = comments[0].pk        
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/approve/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/approve/%d/" % pk)

        makeModerator("normaluser")
        response = self.client.get("/approve/%d/" % pk)
        self.assertEqual(response.status_code, 200)

    def testApprovePost(self):
        """POSTing the delete view should mark the comment as removed"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False; c1.save()

        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/approve/%d/" % c1.pk)
        self.assertEqual(response["Location"], "http://testserver/approved/?c=%d" % c1.pk)
        c = Comment.objects.get(pk=c1.pk)
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
        comments = self.createSomeComments()
        pk = comments[0].pk        
        response = self.client.get("/approved/", data={"c":pk})
        self.assertTemplateUsed(response, "comments/approved.html")

class AdminActionsTests(CommentTestCase):
    urls = "regressiontests.comment_tests.urls_admin"
    
    def setUp(self):
        super(AdminActionsTests, self).setUp()
        
        # Make "normaluser" a moderator
        u = User.objects.get(username="normaluser")
        u.is_staff = True
        perms = Permission.objects.filter(
            content_type__app_label = 'comments', 
            codename__endswith = 'comment'
        )
        for perm in perms:
            u.user_permissions.add(perm)
        u.save()

    def testActionsNonModerator(self):
        comments = self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/admin/comments/comment/")
        self.assertEquals("approve_comments" in response.content, False)

    def testActionsModerator(self):
        comments = self.createSomeComments()
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/admin/comments/comment/")
        self.assertEquals("approve_comments" in response.content, True)
