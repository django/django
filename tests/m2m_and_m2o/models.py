"""
Many-to-many and many-to-one relationships to the same table

Make sure to set ``related_name`` if you use relationships to the same table.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class User(models.Model):
    username = models.CharField(max_length=20)


@python_2_unicode_compatible
class Issue(models.Model):
    num = models.IntegerField()
    cc = models.ManyToManyField(User, blank=True, related_name='test_issue_cc')
    client = models.ForeignKey(User, models.CASCADE, related_name='test_issue_client')

    def __str__(self):
        return six.text_type(self.num)

    class Meta:
        ordering = ('num',)


class UnicodeReferenceModel(models.Model):
    others = models.ManyToManyField("UnicodeReferenceModel")
