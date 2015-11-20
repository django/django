"""
Tests for the order_with_respect_to Meta attribute.
"""

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class Question(models.Model):
    text = models.CharField(max_length=200)


@python_2_unicode_compatible
class Answer(models.Model):
    text = models.CharField(max_length=200)
    question = models.ForeignKey(Question)

    class Meta:
        order_with_respect_to = 'question'

    def __str__(self):
        return six.text_type(self.text)


@python_2_unicode_compatible
class Post(models.Model):
    title = models.CharField(max_length=200)
    parent = models.ForeignKey("self", related_name="children", null=True)

    class Meta:
        order_with_respect_to = "parent"

    def __str__(self):
        return self.title


# order_with_respect_to points to a model with a OneToOneField primary key.
class Entity(models.Model):
    pass


class Dimension(models.Model):
    entity = models.OneToOneField('Entity', primary_key=True)


class Component(models.Model):
    dimension = models.ForeignKey('Dimension')

    class Meta:
        order_with_respect_to = 'dimension'
