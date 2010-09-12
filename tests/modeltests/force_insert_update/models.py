"""
Tests for forcing insert and update queries (instead of Django's normal
automatic behaviour).
"""
from django.db import models, transaction, IntegrityError

class Counter(models.Model):
    name = models.CharField(max_length = 10)
    value = models.IntegerField()

class WithCustomPK(models.Model):
    name = models.IntegerField(primary_key=True)
    value = models.IntegerField()
