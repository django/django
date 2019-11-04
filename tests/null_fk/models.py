"""
Regression tests for proper working of ForeignKey(null=True).
"""

from django.db import models


class SystemDetails(models.Model):
    details = models.TextField()


class SystemInfo(models.Model):
    system_details = models.ForeignKey(SystemDetails, models.CASCADE)
    system_name = models.CharField(max_length=32)


class Forum(models.Model):
    system_info = models.ForeignKey(SystemInfo, models.CASCADE)
    forum_name = models.CharField(max_length=32)


class Post(models.Model):
    forum = models.ForeignKey(Forum, models.SET_NULL, null=True)
    title = models.CharField(max_length=32)

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, models.SET_NULL, null=True)
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
    item = models.ForeignKey(Item, models.CASCADE, related_name='props')
    key = models.CharField(max_length=100)
    value = models.ForeignKey(PropertyValue, models.SET_NULL, null=True)
