import copy
import datetime

from django.contrib.auth.models import User
from django.db import models


class RevisionableModel(models.Model):
    base = models.ForeignKey('self', null=True)
    title = models.CharField(blank=True, max_length=255)
    when = models.DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return u"%s (%s, %s)" % (self.title, self.id, self.base.id)

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
    created_by = models.ForeignKey(User)
    text = models.TextField()

class TestObject(models.Model):
    first = models.CharField(max_length=20)
    second = models.CharField(max_length=20)
    third = models.CharField(max_length=20)

    def __unicode__(self):
        return u'TestObject: %s,%s,%s' % (self.first,self.second,self.third)

