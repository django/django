"""
Regression tests for proper working of ForeignKey(null=True).
"""

from django.db import models

class SystemDetails(models.Model):
    details = models.TextField()

class SystemInfo(models.Model):
    system_details = models.ForeignKey(SystemDetails)
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
        ordering = ('comment_text',)

    def __unicode__(self):
        return self.comment_text

__test__ = {'API_TESTS':"""

>>> d = SystemDetails.objects.create(details='First details')
>>> s = SystemInfo.objects.create(system_name='First forum', system_details=d)
>>> f = Forum.objects.create(system_info=s, forum_name='First forum')
>>> p = Post.objects.create(forum=f, title='First Post')
>>> c1 = Comment.objects.create(post=p, comment_text='My first comment')
>>> c2 = Comment.objects.create(comment_text='My second comment')

# Starting from comment, make sure that a .select_related(...) with a specified
# set of fields will properly LEFT JOIN multiple levels of NULLs (and the things
# that come after the NULLs, or else data that should exist won't). Regression
# test for #7369.
>>> c = Comment.objects.select_related().get(id=1)
>>> c.post
<Post: First Post>
>>> c = Comment.objects.select_related().get(id=2)
>>> print c.post
None

>>> comments = Comment.objects.select_related('post__forum__system_info').all()
>>> [(c.id, c.comment_text, c.post) for c in comments]
[(1, u'My first comment', <Post: First Post>), (2, u'My second comment', None)]

# Regression test for #7530, #7716.
>>> Comment.objects.select_related('post').filter(post__isnull=True)[0].post is None
True

>>> comments = Comment.objects.select_related('post__forum__system_info__system_details')
>>> [(c.id, c.comment_text, c.post) for c in comments]
[(1, u'My first comment', <Post: First Post>), (2, u'My second comment', None)]

"""}
