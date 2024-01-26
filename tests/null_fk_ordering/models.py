"""
Regression tests for proper working of ForeignKey(null=True). Tests these bugs:

    * #7512: including a nullable foreign key reference in Meta ordering has
unexpected results

"""

from django.db import models


# The first two models represent a very simple null FK ordering case.
class Author(models.Model):
    name = models.CharField(max_length=150)


class Article(models.Model):
    title = models.CharField(max_length=150)
    author = models.ForeignKey(Author, models.SET_NULL, null=True)

    class Meta:
        ordering = ["author__name"]


# These following 4 models represent a far more complex ordering case.
class SystemInfo(models.Model):
    system_name = models.CharField(max_length=32)


class Forum(models.Model):
    system_info = models.ForeignKey(SystemInfo, models.CASCADE)
    forum_name = models.CharField(max_length=32)


class Post(models.Model):
    forum = models.ForeignKey(Forum, models.SET_NULL, null=True)
    title = models.CharField(max_length=32)


class Comment(models.Model):
    post = models.ForeignKey(Post, models.SET_NULL, null=True)
    comment_text = models.CharField(max_length=250)

    class Meta:
        ordering = ["post__forum__system_info__system_name", "comment_text"]
