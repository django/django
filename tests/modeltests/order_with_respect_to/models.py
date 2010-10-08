"""
Tests for the order_with_respect_to Meta attribute.
"""

from django.db import models


class Question(models.Model):
    text = models.CharField(max_length=200)

class Answer(models.Model):
    text = models.CharField(max_length=200)
    question = models.ForeignKey(Question)

    class Meta:
        order_with_respect_to = 'question'

    def __unicode__(self):
        return unicode(self.text)

class Post(models.Model):
    title = models.CharField(max_length=200)
    parent = models.ForeignKey("self", related_name="children", null=True)

    class Meta:
        order_with_respect_to = "parent"

    def __unicode__(self):
        return self.title
