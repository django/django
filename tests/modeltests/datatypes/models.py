"""
1. Simple data types testing.

This is a basic model to test saving and loading boolean and date-related
types, which in the past were problematic for some database backends.
"""

from django.db import models

class Donut(models.Model):
    name = models.CharField(maxlength=100)
    is_frosted = models.BooleanField(default=False)
    has_sprinkles = models.NullBooleanField()
    baked_date = models.DateField(null=True)
    baked_time = models.TimeField(null=True)
    consumed_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ('consumed_at',)

    def __str__(self):
        return self.name

__test__ = {'API_TESTS': """
# No donuts are in the system yet.
>>> Donut.objects.all()
[]

>>> d = Donut(name='Apple Fritter')

# Ensure we're getting True and False, not 0 and 1
>>> d.is_frosted
False
>>> d.has_sprinkles
>>> d.has_sprinkles = True
>>> d.has_sprinkles
True
>>> d.save()
>>> d2 = Donut.objects.all()[0]
>>> d2
<Donut: Apple Fritter>
>>> d2.is_frosted
False
>>> d2.has_sprinkles
True

>>> import datetime
>>> d2.baked_date = datetime.date(year=1938, month=6, day=4)
>>> d2.baked_time = datetime.time(hour=5, minute=30)
>>> d2.consumed_at = datetime.datetime(year=2007, month=4, day=20, hour=16, minute=19, second=59)
>>> d2.save()

>>> d3 = Donut.objects.all()[0]
>>> d3.baked_date
datetime.date(1938, 6, 4)
>>> d3.baked_time
datetime.time(5, 30)
>>> d3.consumed_at
datetime.datetime(2007, 4, 20, 16, 19, 59)
"""}
