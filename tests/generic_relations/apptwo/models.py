from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class Post(models.Model):
    topic = GenericRelation('appone.Topic', related_query_name='apptwo_posts')


class Message(models.Model):
    topic = GenericRelation('appone.Topic', related_query_name='messages')
