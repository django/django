from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    facebook_user_id = models.BigIntegerField(null=True)
    raw_data = models.BinaryField(null=True)
    small_int = models.SmallIntegerField()

    class Meta:
        unique_together = ('first_name', 'last_name')

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    body = models.TextField(default='')
    reporter = models.ForeignKey(Reporter)
    response_to = models.ForeignKey('self', null=True)

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)
        index_together = [
            ["headline", "pub_date"],
        ]
