"""
15. Transactions

Django handles transactions in three different ways. The default is to commit
each transaction upon a write, but you can decorate a function to get
commit-on-success behavior. Alternatively, you can manage the transaction
manually.
"""

from django.db import models


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ('first_name', 'last_name')

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)