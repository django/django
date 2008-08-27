"""
Tests for field subclassing.
"""

from django.db import models
from django.utils.encoding import force_unicode
from django.core import serializers
from django.core.exceptions import FieldError

class Small(object):
    """
    A simple class to show that non-trivial Python objects can be used as
    attributes.
    """
    def __init__(self, first, second):
        self.first, self.second = first, second

    def __unicode__(self):
        return u'%s%s' % (force_unicode(self.first), force_unicode(self.second))

    def __str__(self):
        return unicode(self).encode('utf-8')

class SmallField(models.Field):
    """
    Turns the "Small" class into a Django field. Because of the similarities
    with normal character fields and the fact that Small.__unicode__ does
    something sensible, we don't need to implement a lot here.
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2
        super(SmallField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if isinstance(value, Small):
            return value
        return Small(value[0], value[1])

    def get_db_prep_save(self, value):
        return unicode(value)

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return force_unicode(value)
        if lookup_type == 'in':
            return [force_unicode(v) for v in value]
        if lookup_type == 'isnull':
            return []
        raise FieldError('Invalid lookup type: %r' % lookup_type)

class MyModel(models.Model):
    name = models.CharField(max_length=10)
    data = SmallField('small field')

    def __unicode__(self):
        return force_unicode(self.name)

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
FieldError: Invalid lookup type: 'lt'

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
