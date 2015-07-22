from __future__ import unicode_literals

import copy
import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class RevisionableModel(models.Model):
    base = models.ForeignKey('self', models.SET_NULL, null=True)
    title = models.CharField(blank=True, max_length=255)
    when = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return "%s (%s, %s)" % (self.title, self.id, self.base.id)

    def save(self, *args, **kwargs):
        super(RevisionableModel, self).save(*args, **kwargs)
        if not self.base:
            self.base = self
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
            super(RevisionableModel, self).save(*args, **kwargs)

    def new_revision(self):
        new_revision = copy.copy(self)
        new_revision.pk = None
        return new_revision


class Order(models.Model):
    created_by = models.ForeignKey(User, models.CASCADE)
    text = models.TextField()


@python_2_unicode_compatible
class TestObject(models.Model):
    first = models.CharField(max_length=20)
    second = models.CharField(max_length=20)
    third = models.CharField(max_length=20)

    def __str__(self):
        return 'TestObject: %s,%s,%s' % (self.first, self.second, self.third)
