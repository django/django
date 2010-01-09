"""
This is a basic model to test saving and loading boolean and date-related
types, which in the past were problematic for some database backends.
"""

from django.db import models, DEFAULT_DB_ALIAS
from django.conf import settings

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
>>> d.has_sprinkles == True
True
>>> d.save()
>>> d2 = Donut.objects.all()[0]
>>> d2
<Donut: Apple Fritter>
>>> d2.is_frosted == False
True
>>> d2.has_sprinkles == True
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

# Test for ticket #12059: TimeField wrongly handling datetime.datetime object.

>>> d2.baked_time = datetime.datetime(year=2007, month=4, day=20, hour=16, minute=19, second=59)
>>> d2.save()

>>> d3 = Donut.objects.all()[0]
>>> d3.baked_time
datetime.time(16, 19, 59)

# Year boundary tests (ticket #3689)

>>> d = Donut(name='Date Test 2007', baked_date=datetime.datetime(year=2007, month=12, day=31), consumed_at=datetime.datetime(year=2007, month=12, day=31, hour=23, minute=59, second=59))
>>> d.save()
>>> d1 = Donut(name='Date Test 2006', baked_date=datetime.datetime(year=2006, month=1, day=1), consumed_at=datetime.datetime(year=2006, month=1, day=1))
>>> d1.save()

>>> Donut.objects.filter(baked_date__year=2007)
[<Donut: Date Test 2007>]

>>> Donut.objects.filter(baked_date__year=2006)
[<Donut: Date Test 2006>]

>>> Donut.objects.filter(consumed_at__year=2007).order_by('name')
[<Donut: Apple Fritter>, <Donut: Date Test 2007>]

>>> Donut.objects.filter(consumed_at__year=2006)
[<Donut: Date Test 2006>]

>>> Donut.objects.filter(consumed_at__year=2005)
[]

>>> Donut.objects.filter(consumed_at__year=2008)
[]

# Regression test for #10238: TextField values returned from the database
# should be unicode.
>>> d2 = Donut.objects.create(name=u'Jelly Donut', review=u'Outstanding')
>>> Donut.objects.get(id=d2.id).review
u'Outstanding'

"""}

# Regression test for #8354: the MySQL backend should raise an error if given
# a timezone-aware datetime object.
if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.mysql':
    __test__['API_TESTS'] += """
>>> from django.utils import tzinfo
>>> dt = datetime.datetime(2008, 8, 31, 16, 20, tzinfo=tzinfo.FixedOffset(0))
>>> d = Donut(name='Bear claw', consumed_at=dt)
>>> d.save()
Traceback (most recent call last):
    ....
ValueError: MySQL backend does not support timezone-aware datetimes.
"""
