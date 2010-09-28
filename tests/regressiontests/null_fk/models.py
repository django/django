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
