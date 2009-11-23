"""
Spanning tests for all the operations that F() expressions can perform.
"""
from django.conf import settings
from django.db import models, DEFAULT_DB_ALIAS

#
# Model for testing arithmetic expressions.
#

class Number(models.Model):
    integer = models.IntegerField(db_column='the_integer')
    float = models.FloatField(null=True, db_column='the_float')

    def __unicode__(self):
        return u'%i, %.3f' % (self.integer, self.float)


__test__ = {'API_TESTS': """
>>> from django.db.models import F

>>> Number(integer=-1).save()
>>> Number(integer=42).save()
>>> Number(integer=1337).save()

We can fill a value in all objects with an other value of the same object.

>>> Number.objects.update(float=F('integer'))
3
>>> Number.objects.all()
[<Number: -1, -1.000>, <Number: 42, 42.000>, <Number: 1337, 1337.000>]

We can increment a value of all objects in a query set.

>>> Number.objects.filter(integer__gt=0).update(integer=F('integer') + 1)
2
>>> Number.objects.all()
[<Number: -1, -1.000>, <Number: 43, 42.000>, <Number: 1338, 1337.000>]

We can filter for objects, where a value is not equals the value of an other field.

>>> Number.objects.exclude(float=F('integer'))
[<Number: 43, 42.000>, <Number: 1338, 1337.000>]

Complex expressions of different connection types are possible.

>>> n = Number.objects.create(integer=10, float=123.45)

>>> Number.objects.filter(pk=n.pk).update(float=F('integer') + F('float') * 2)
1
>>> Number.objects.get(pk=n.pk)
<Number: 10, 256.900>

# All supported operators work as expected.

>>> n = Number.objects.create(integer=42, float=15.5)

# Left hand operators

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') + 15, float=F('float') + 42.7)
>>> Number.objects.get(pk=n.pk) # LH Addition of floats and integers
<Number: 57, 58.200>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') - 15, float=F('float') - 42.7)
>>> Number.objects.get(pk=n.pk) # LH Subtraction of floats and integers
<Number: 27, -27.200>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') * 15, float=F('float') * 42.7)
>>> Number.objects.get(pk=n.pk) # Multiplication of floats and integers
<Number: 630, 661.850>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') / 2, float=F('float') / 42.7)
>>> Number.objects.get(pk=n.pk) # LH Division of floats and integers
<Number: 21, 0.363>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') % 20)
>>> Number.objects.get(pk=n.pk) # LH Modulo arithmetic on integers
<Number: 2, 15.500>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') & 56)
>>> Number.objects.get(pk=n.pk) # LH Bitwise ands on integers
<Number: 40, 15.500>

# Right hand operators

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=15 + F('integer'), float=42.7 + F('float'))
>>> Number.objects.get(pk=n.pk) # RH Addition of floats and integers
<Number: 57, 58.200>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=15 - F('integer'), float=42.7 - F('float'))
>>> Number.objects.get(pk=n.pk) # RH Subtraction of floats and integers
<Number: -27, 27.200>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=15 * F('integer'), float=42.7 * F('float'))
>>> Number.objects.get(pk=n.pk) # RH Multiplication of floats and integers
<Number: 630, 661.850>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=640 / F('integer'), float=42.7 / F('float'))
>>> Number.objects.get(pk=n.pk) # RH Division of floats and integers
<Number: 15, 2.755>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=69 % F('integer'))
>>> Number.objects.get(pk=n.pk) # RH Modulo arithmetic on integers
<Number: 27, 15.500>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=15 & F('integer'))
>>> Number.objects.get(pk=n.pk) # RH Bitwise ands on integers
<Number: 10, 15.500>
"""}

# Oracle doesn't support the Bitwise OR operator.
if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != 'django.db.backends.oracle':
    __test__['API_TESTS'] += """

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=F('integer') | 48)
>>> Number.objects.get(pk=n.pk) # LH Bitwise or on integers
<Number: 58, 15.500>

>>> _ = Number.objects.filter(pk=n.pk).update(integer=42, float=15.5)
>>> _ = Number.objects.filter(pk=n.pk).update(integer=15 | F('integer'))
>>> Number.objects.get(pk=n.pk) # RH Bitwise or on integers
<Number: 47, 15.500>

"""
