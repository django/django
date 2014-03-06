from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db import models


class Topic(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class Post(models.Model):
    topic = GenericRelation(Topic, related_query_name='appone_posts')


class Message(models.Model):
    topic = GenericRelation(Topic, related_query_name='messages')
