"""
update_or_create()

``update_or_create()`` does what it says: it tries to look up an object with the
given parameters and update If an object isn't found, it creates one with the given
parameters.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class SalesRank(models.Model):
    product_name = models.CharField(max_length=100)
    total_rank = models.IntegerField()
    num_of_likes = models.IntegerField(default=0)

    def __str__(self):
        return self.product_name


class ManualPrimaryKeyTest(models.Model):
    id = models.IntegerField(primary_key=True)
    data = models.CharField(max_length=100)


class Product(models.Model):
    sales_rank = models.ForeignKey(SalesRank, primary_key=True)
