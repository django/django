"""
Regression tests for proper working of ForeignKey(null=True).
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class SystemDetails(models.Model):
    details = models.TextField()

class SystemInfo(models.Model):
    system_details = models.ForeignKey(SystemDetails)
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
        ordering = ('comment_text',)

    def __str__(self):
        return self.comment_text

# Ticket 15823

class Item(models.Model):
    title = models.CharField(max_length=100)

class PropertyValue(models.Model):
    label = models.CharField(max_length=100)

class Property(models.Model):
    item = models.ForeignKey(Item, related_name='props')
    key = models.CharField(max_length=100)
    value = models.ForeignKey(PropertyValue, null=True)
