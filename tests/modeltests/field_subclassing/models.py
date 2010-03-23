"""
Tests for field subclassing.
"""

from django.core import serializers
from django.db import models
from django.utils.encoding import force_unicode

from fields import Small, SmallField, JSONField


class MyModel(models.Model):
    name = models.CharField(max_length=10)
    data = SmallField('small field')

    def __unicode__(self):
        return force_unicode(self.name)

class DataModel(models.Model):
    data = JSONField()

__test__ = {'API_TESTS': ur"""
# Creating a model with custom fields is done as per normal.
>>> s = Small(1, 2)
>>> print s
12
>>> m = MyModel(name='m', data=s)
>>> m.save()

# Custom fields still have normal field's attributes.
>>> m._meta.get_field('data').verbose_name
'small field'

# The m.data attribute has been initialised correctly. It's a Small object.
>>> m.data.first, m.data.second
(1, 2)

# The data loads back from the database correctly and 'data' has the right type.
>>> m1 = MyModel.objects.get(pk=m.pk)
>>> isinstance(m1.data, Small)
True
>>> print m1.data
12

# We can do normal filtering on the custom field (and will get an error when we
# use a lookup type that does not make sense).
>>> s1 = Small(1, 3)
>>> s2 = Small('a', 'b')
>>> MyModel.objects.filter(data__in=[s, s1, s2])
[<MyModel: m>]
>>> MyModel.objects.filter(data__lt=s)
Traceback (most recent call last):
...
TypeError: Invalid lookup type: 'lt'

# Serialization works, too.
>>> stream = serializers.serialize("json", MyModel.objects.all())
>>> stream
'[{"pk": 1, "model": "field_subclassing.mymodel", "fields": {"data": "12", "name": "m"}}]'
>>> obj = list(serializers.deserialize("json", stream))[0]
>>> obj.object == m
True

# Test retrieving custom field data
>>> m.delete()
>>> m1 = MyModel(name="1", data=Small(1, 2))
>>> m1.save()
>>> m2 = MyModel(name="2", data=Small(2, 3))
>>> m2.save()
>>> for m in MyModel.objects.all(): print unicode(m.data)
12
23
"""}
