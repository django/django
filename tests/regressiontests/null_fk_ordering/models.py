"""
Regression tests for proper working of ForeignKey(null=True). Tests these bugs:

    * #7512: including a nullable foreign key reference in Meta ordering has un
xpected results

"""

from django.db import models

# The first two models represent a very simple null FK ordering case.
class Author(models.Model):
    name = models.CharField(max_length=150)

class Article(models.Model):
    title = models.CharField(max_length=150)
    author = models.ForeignKey(Author, null=True)

    def __unicode__(self):
        return u'Article titled: %s' % (self.title, )

    class Meta:
        ordering = ['author__name', ]


# These following 4 models represent a far more complex ordering case.
class SystemInfo(models.Model):
    system_name = models.CharField(max_length=32)

class Forum(models.Model):
    system_info = models.ForeignKey(SystemInfo)
    forum_name = models.CharField(max_length=32)

class Post(models.Model):
    forum = models.ForeignKey(Forum, null=True)
    title = models.CharField(max_length=32)

    def __unicode__(self):
        return self.title

class Comment(models.Model):
    post = models.ForeignKey(Post, null=True)
    comment_text = models.CharField(max_length=250)

    class Meta:
        ordering = ['post__forum__system_info__system_name', 'comment_text']

    def __unicode__(self):
        return self.comment_text

class Comment(models.Model):
    post = models.ForeignKey(Post, null=True)
    comment_text = models.CharField(max_length=250)

    class Meta:
        ordering = ['post__forum__system_info__system_name', 'comment_text']

    def __unicode__(self):
        return self.comment_text

__test__ = {'API_TESTS': """
# Regression test for #7512 -- ordering across nullable Foreign Keys shouldn't
# exclude results
>>> author_1 = Author.objects.create(name='Tom Jones')
>>> author_2 = Author.objects.create(name='Bob Smith')
>>> article_1 = Article.objects.create(title='No author on this article')
>>> article_2 = Article.objects.create(author=author_1, title='This article written by Tom Jones')
>>> article_3 = Article.objects.create(author=author_2, title='This article written by Bob Smith')

# We can't compare results directly (since different databases sort NULLs to
# different ends of the ordering), but we can check that all results are
# returned.
>>> len(list(Article.objects.all())) == 3
True

>>> s = SystemInfo.objects.create(system_name='System Info')
>>> f = Forum.objects.create(system_info=s, forum_name='First forum')
>>> p = Post.objects.create(forum=f, title='First Post')
>>> c1 = Comment.objects.create(post=p, comment_text='My first comment')
>>> c2 = Comment.objects.create(comment_text='My second comment')
>>> s2 = SystemInfo.objects.create(system_name='More System Info')
>>> f2 = Forum.objects.create(system_info=s2, forum_name='Second forum')
>>> p2 = Post.objects.create(forum=f2, title='Second Post')
>>> c3 = Comment.objects.create(comment_text='Another first comment')
>>> c4 = Comment.objects.create(post=p2, comment_text='Another second comment')

# We have to test this carefully. Some databases sort NULL values before
# everything else, some sort them afterwards. So we extract the ordered list
# and check the length. Before the fix, this list was too short (some values
# were omitted).
>>> len(list(Comment.objects.all())) == 4
True

"""
}
