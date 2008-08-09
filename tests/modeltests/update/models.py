"""
Tests for the update() queryset method that allows in-place, multi-object
updates.
"""

from django.db import models

class DataPoint(models.Model):
    name = models.CharField(max_length=20)
    value = models.CharField(max_length=20)
    another_value = models.CharField(max_length=20, blank=True)

    def __unicode__(self):
        return unicode(self.name)

class RelatedPoint(models.Model):
    name = models.CharField(max_length=20)
    data = models.ForeignKey(DataPoint)

    def __unicode__(self):
        return unicode(self.name)


__test__ = {'API_TESTS': """
>>> DataPoint(name="d0", value="apple").save()
>>> DataPoint(name="d2", value="banana").save()
>>> d3 = DataPoint.objects.create(name="d3", value="banana")
>>> RelatedPoint(name="r1", data=d3).save()

Objects are updated by first filtering the candidates into a queryset and then
calling the update() method. It executes immediately and returns nothing.

>>> DataPoint.objects.filter(value="apple").update(name="d1")
1
>>> DataPoint.objects.filter(value="apple")
[<DataPoint: d1>]

We can update multiple objects at once.

>>> DataPoint.objects.filter(value="banana").update(value="pineapple")
2
>>> DataPoint.objects.get(name="d2").value
u'pineapple'

Foreign key fields can also be updated, although you can only update the object
referred to, not anything inside the related object.

>>> d = DataPoint.objects.get(name="d1")
>>> RelatedPoint.objects.filter(name="r1").update(data=d)
1
>>> RelatedPoint.objects.filter(data__name="d1")
[<RelatedPoint: r1>]

Multiple fields can be updated at once

>>> DataPoint.objects.filter(value="pineapple").update(value="fruit", another_value="peaches")
2
>>> d = DataPoint.objects.get(name="d2")
>>> d.value, d.another_value
(u'fruit', u'peaches')

In the rare case you want to update every instance of a model, update() is also
a manager method.

>>> DataPoint.objects.update(value='thing')
3
>>> DataPoint.objects.values('value').distinct()
[{'value': u'thing'}]

We do not support update on already sliced query sets.

>>> DataPoint.objects.all()[:2].update(another_value='another thing')
Traceback (most recent call last):
    ...
AssertionError: Cannot update a query once a slice has been taken.

"""
}
