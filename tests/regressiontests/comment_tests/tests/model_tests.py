from __future__ import absolute_import, with_statement

from django.contrib.comments.models import Comment

from . import CommentTestCase
from ..models import Author, Article


class CommentModelTests(CommentTestCase):
    def testSave(self):
        for c in self.createSomeComments():
            self.assertNotEqual(c.submit_date, None)

    def testUserProperties(self):
        c1, c2, c3, c4 = self.createSomeComments()
        self.assertEqual(c1.name, "Joe Somebody")
        self.assertEqual(c2.email, "jsomebody@example.com")
        self.assertEqual(c3.name, "Frank Nobody")
        self.assertEqual(c3.url, "http://example.com/~frank/")
        self.assertEqual(c1.user, None)
        self.assertEqual(c3.user, c4.user)

class CommentManagerTests(CommentTestCase):

    def testInModeration(self):
        """Comments that aren't public are considered in moderation"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False
        c2.is_public = False
        c1.save()
        c2.save()
        moderated_comments = list(Comment.objects.in_moderation().order_by("id"))
        self.assertEqual(moderated_comments, [c1, c2])

    def testRemovedCommentsNotInModeration(self):
        """Removed comments are not considered in moderation"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False
        c2.is_public = False
        c2.is_removed = True
        c1.save()
        c2.save()
        moderated_comments = list(Comment.objects.in_moderation())
        self.assertEqual(moderated_comments, [c1])

    def testForModel(self):
        c1, c2, c3, c4 = self.createSomeComments()
        article_comments = list(Comment.objects.for_model(Article).order_by("id"))
        author_comments = list(Comment.objects.for_model(Author.objects.get(pk=1)))
        self.assertEqual(article_comments, [c1, c3])
        self.assertEqual(author_comments, [c2])

    def testPrefetchRelated(self):
        c1, c2, c3, c4 = self.createSomeComments()
        # one for comments, one for Articles, one for Author
        with self.assertNumQueries(3):
            qs = Comment.objects.prefetch_related('content_object')
            [c.content_object for c in qs]
