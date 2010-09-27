"""
This is a basic model to test saving and loading boolean and date-related
types, which in the past were problematic for some database backends.
"""

from django.db import models

class Donut(models.Model):
    name = models.CharField(max_length=100)
    is_frosted = models.BooleanField(default=False)
    has_sprinkles = models.NullBooleanField()
    baked_date = models.DateField(null=True)
    baked_time = models.TimeField(null=True)
    consumed_at = models.DateTimeField(null=True)
    review = models.TextField()

    class Meta:
        ordering = ('consumed_at',)

    def __str__(self):
        return self.name
