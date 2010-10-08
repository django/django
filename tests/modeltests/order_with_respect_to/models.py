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
