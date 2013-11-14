"""
Existing related object instance caching.

Test that queries are not redone when going back through known relations.
"""

from django.db import models


class Tournament(models.Model):
    name = models.CharField(max_length=30)


class Organiser(models.Model):
    name = models.CharField(max_length=30)


class Pool(models.Model):
    name = models.CharField(max_length=30)
    tournament = models.ForeignKey(Tournament)
    organiser = models.ForeignKey(Organiser)


class PoolStyle(models.Model):
    name = models.CharField(max_length=30)
    pool = models.OneToOneField(Pool)
