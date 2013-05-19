"""
Regression tests for proper working of ForeignKey(null=True). Tests these bugs:

    * #7512: including a nullable foreign key reference in Meta ordering has un
xpected results

"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


# The first two models represent a very simple null FK ordering case.
class Author(models.Model):
    name = models.CharField(max_length=150)

@python_2_unicode_compatible
class Article(models.Model):
    title = models.CharField(max_length=150)
    author = models.ForeignKey(Author, null=True)

    def __str__(self):
        return 'Article titled: %s' % (self.title, )

    class Meta:
        ordering = ['author__name', ]


# These following 4 models represent a far more complex ordering case.
class SystemInfo(models.Model):
    system_name = models.CharField(max_length=32)

class Forum(models.Model):
    system_info = models.ForeignKey(SystemInfo)
    forum_name = models.CharField(max_length=32)

@python_2_unicode_compatible
class Post(models.Model):
    forum = models.ForeignKey(Forum, null=True)
    title = models.CharField(max_length=32)

    def __str__(self):
        return self.title

@python_2_unicode_compatible
class Comment(models.Model):
    post = models.ForeignKey(Post, null=True)
    comment_text = models.CharField(max_length=250)

    class Meta:
        ordering = ['post__forum__system_info__system_name', 'comment_text']

    def __str__(self):
        return self.comment_text
