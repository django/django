from django.test import TestCase

from .models import Article, Author, Comment, Forum, Post, SystemInfo


class NullFkOrderingTests(TestCase):
    def test_ordering_across_null_fk(self):
        """
        Regression test for #7512

        ordering across nullable Foreign Keys shouldn't exclude results
        """
        author_1 = Author.objects.create(name="Tom Jones")
        author_2 = Author.objects.create(name="Bob Smith")
        Article.objects.create(title="No author on this article")
        Article.objects.create(
            author=author_1, title="This article written by Tom Jones"
        )
        Article.objects.create(
            author=author_2, title="This article written by Bob Smith"
        )

        # We can't compare results directly (since different databases sort
        # NULLs to different ends of the ordering), but we can check that all
        # results are returned.
        self.assertEqual(len(list(Article.objects.all())), 3)

        s = SystemInfo.objects.create(system_name="System Info")
        f = Forum.objects.create(system_info=s, forum_name="First forum")
        p = Post.objects.create(forum=f, title="First Post")
        Comment.objects.create(post=p, comment_text="My first comment")
        Comment.objects.create(comment_text="My second comment")
        s2 = SystemInfo.objects.create(system_name="More System Info")
        f2 = Forum.objects.create(system_info=s2, forum_name="Second forum")
        p2 = Post.objects.create(forum=f2, title="Second Post")
        Comment.objects.create(comment_text="Another first comment")
        Comment.objects.create(post=p2, comment_text="Another second comment")

        # We have to test this carefully. Some databases sort NULL values
        # before everything else, some sort them afterward. So we extract the
        # ordered list and check the length. Before the fix, this list was too
        # short (some values were omitted).
        self.assertEqual(len(list(Comment.objects.all())), 4)
