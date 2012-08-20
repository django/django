"""
15. Transactions

Django handles transactions in three different ways. The default is to commit
each transaction upon a write, but you can decorate a function to get
commit-on-success behavior. Alternatively, you can manage the transaction
manually.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ('first_name', 'last_name')

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)
