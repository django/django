"""
9. Many-to-many relationships via an intermediary table

For many-to-many relationships that need extra fields on the intermediary
table, use an intermediary model.

In this example, an ``Article`` can have multiple ``Reporter`` objects, and
each ``Article``-``Reporter`` combination (a ``Writer``) has a ``position``
field, which specifies the ``Reporter``'s position for the given article
(e.g. "Staff writer").
"""

from django.db import models


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()

    def __unicode__(self):
        return self.headline

class Writer(models.Model):
    reporter = models.ForeignKey(Reporter)
    article = models.ForeignKey(Article)
    position = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s (%s)' % (self.reporter, self.position)

