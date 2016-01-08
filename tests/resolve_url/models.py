"""
Regression tests for the resolve_url function.
"""

from django.db import models


class UnimportantThing(models.Model):
    importance = models.IntegerField()

    class Meta:
        managed = False

    def get_absolute_url(self):
        return '/importance/%d/' % (self.importance,)
