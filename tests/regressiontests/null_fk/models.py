"""
Regression tests for proper working of ForeignKey(null=True). Tests these bugs:

    * #7369: FK non-null after null relationship on select_related() generates an invalid query

"""

from django.db import models

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

    def __unicode__(self):
        return self.comment_text

__test__ = {'API_TESTS':"""

>>> s = SystemInfo.objects.create(system_name='First forum')
>>> f = Forum.objects.create(system_info=s, forum_name='First forum')
>>> p = Post.objects.create(forum=f, title='First Post')
>>> c1 = Comment.objects.create(post=p, comment_text='My first comment')
>>> c2 = Comment.objects.create(comment_text='My second comment')

# Starting from comment, make sure that a .select_related(...) with a specified
# set of fields will properly LEFT JOIN multiple levels of NULLs (and the things
# that come after the NULLs, or else data that should exist won't).
>>> c = Comment.objects.select_related().get(id=1)
>>> c.post
<Post: First Post>
>>> c = Comment.objects.select_related().get(id=2)
>>> print c.post
None

>>> comments = Comment.objects.select_related('post__forum__system_info').all()
>>> [(c.id, c.post.id) for c in comments]
[(1, 1), (2, None)]
>>> [(c.comment_text, c.post.title) for c in comments]
[(u'My first comment', u'First Post'), (u'My second comment', None)]

"""}
