"""
Existing related object instance caching.

Queries are not redone when going back through known relations.
"""

from django.db import models


class Tournament(models.Model):
    name = models.CharField(max_length=30)


class Organiser(models.Model):
    name = models.CharField(max_length=30)


class Pool(models.Model):
    name = models.CharField(max_length=30)
    tournament = models.ForeignKey(Tournament, models.CASCADE)
    organiser = models.ForeignKey(Organiser, models.CASCADE)


class PoolStyle(models.Model):
    name = models.CharField(max_length=30)
    pool = models.OneToOneField(Pool, models.CASCADE)
    another_pool = models.OneToOneField(
        Pool, models.CASCADE, null=True, related_name="another_style"
    )
