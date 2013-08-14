# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class SimpleModel(models.Model):
    field = models.IntegerField()
    manager = models.manager.Manager()


class Book(models.Model):
    title = models.CharField(max_length=250)
    is_published = models.BooleanField(default=False)


class BlogPost(models.Model):
    title = models.CharField(max_length=250)
    is_published = models.BooleanField(default=False)
