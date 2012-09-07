from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Comment(models.Model):
    pass


@python_2_unicode_compatible
class Post(models.Model):
    comments = models.ManyToManyField('Comment')


@python_2_unicode_compatible
class UserPost(models.Model):
    uuid = models.CharField(max_length=120, db_index=True)
