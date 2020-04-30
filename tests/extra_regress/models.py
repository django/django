import copy
import datetime

from django.contrib.auth.models import User
from django.db import models


class RevisionableModel(models.Model):
    base = models.ForeignKey('self', models.SET_NULL, null=True)
    title = models.CharField(blank=True, max_length=255)
    when = models.DateTimeField(default=datetime.datetime.now)

    def save(self, *args, force_insert=None, force_update=None, **kwargs):
        super().save(*args, force_insert=force_insert, force_update=force_update, **kwargs)
        if not self.base:
            self.base = self
            super().save(*args, **kwargs)

    def new_revision(self):
        new_revision = copy.copy(self)
        new_revision.pk = None
        return new_revision


class Order(models.Model):
    created_by = models.ForeignKey(User, models.CASCADE)
    text = models.TextField()


class TestObject(models.Model):
    first = models.CharField(max_length=20)
    second = models.CharField(max_length=20)
    third = models.CharField(max_length=20)

    def __str__(self):
        return 'TestObject: %s,%s,%s' % (self.first, self.second, self.third)
