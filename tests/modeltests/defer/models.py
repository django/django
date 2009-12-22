"""
Tests for defer() and only().
"""

from django.db import models
from django.db.models.query_utils import DeferredAttribute

class Secondary(models.Model):
    first = models.CharField(max_length=50)
    second = models.CharField(max_length=50)

class Primary(models.Model):
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    related = models.ForeignKey(Secondary)

    def __unicode__(self):
        return self.name

class Child(Primary):
    pass

class BigChild(Primary):
    other = models.CharField(max_length=50)

def count_delayed_fields(obj, debug=False):
    """
    Returns the number of delayed attributes on the given model instance.
    """
    count = 0
    for field in obj._meta.fields:
        if isinstance(obj.__class__.__dict__.get(field.attname),
                DeferredAttribute):
            if debug:
                print field.name, field.attname
            count += 1
    return count


__test__ = {"API_TEST": """
To all outward appearances, instances with deferred fields look the same as
normal instances when we examine attribute values. Therefore we test for the
number of deferred fields on returned instances (by poking at the internals),
as a way to observe what is going on.

>>> s1 = Secondary.objects.create(first="x1", second="y1")
>>> p1 = Primary.objects.create(name="p1", value="xx", related=s1)

>>> qs = Primary.objects.all()

>>> count_delayed_fields(qs.defer('name')[0])
1
>>> count_delayed_fields(qs.only('name')[0])
2
>>> count_delayed_fields(qs.defer('related__first')[0])
0
>>> obj = qs.select_related().only('related__first')[0]
>>> count_delayed_fields(obj)
2
>>> obj.related_id == s1.pk
True
>>> count_delayed_fields(qs.defer('name').extra(select={'a': 1})[0])
1
>>> count_delayed_fields(qs.extra(select={'a': 1}).defer('name')[0])
1
>>> count_delayed_fields(qs.defer('name').defer('value')[0])
2
>>> count_delayed_fields(qs.only('name').only('value')[0])
2
>>> count_delayed_fields(qs.only('name').defer('value')[0])
2
>>> count_delayed_fields(qs.only('name', 'value').defer('value')[0])
2
>>> count_delayed_fields(qs.defer('name').only('value')[0])
2
>>> obj = qs.only()[0]
>>> count_delayed_fields(qs.defer(None)[0])
0
>>> count_delayed_fields(qs.only('name').defer(None)[0])
0

User values() won't defer anything (you get the full list of dictionaries
back), but it still works.
>>> qs.defer('name').values()[0] == {'id': p1.id, 'name': u'p1', 'value': 'xx', 'related_id': s1.id}
True
>>> qs.only('name').values()[0] == {'id': p1.id, 'name': u'p1', 'value': 'xx', 'related_id': s1.id}
True

Using defer() and only() with get() is also valid.
>>> count_delayed_fields(qs.defer('name').get(pk=p1.pk))
1
>>> count_delayed_fields(qs.only('name').get(pk=p1.pk))
2

# KNOWN NOT TO WORK: >>> count_delayed_fields(qs.only('name').select_related('related')[0])
# KNOWN NOT TO WORK >>> count_delayed_fields(qs.defer('related').select_related('related')[0])

# Saving models with deferred fields is possible (but inefficient, since every
# field has to be retrieved first).

>>> obj = Primary.objects.defer("value").get(name="p1")
>>> obj.name = "a new name"
>>> obj.save()
>>> Primary.objects.all()
[<Primary: a new name>]

# Regression for #10572 - A subclass with no extra fields can defer fields from the base class
>>> _ = Child.objects.create(name="c1", value="foo", related=s1)

# You can defer a field on a baseclass when the subclass has no fields
>>> obj = Child.objects.defer("value").get(name="c1")
>>> count_delayed_fields(obj)
1
>>> obj.name
u"c1"
>>> obj.value
u"foo"
>>> obj.name = "c2"
>>> obj.save()

# You can retrive a single column on a base class with no fields
>>> obj = Child.objects.only("name").get(name="c2")
>>> count_delayed_fields(obj)
3
>>> obj.name
u"c2"
>>> obj.value
u"foo"
>>> obj.name = "cc"
>>> obj.save()

>>> _ = BigChild.objects.create(name="b1", value="foo", related=s1, other="bar")

# You can defer a field on a baseclass
>>> obj = BigChild.objects.defer("value").get(name="b1")
>>> count_delayed_fields(obj)
1
>>> obj.name
u"b1"
>>> obj.value
u"foo"
>>> obj.other
u"bar"
>>> obj.name = "b2"
>>> obj.save()

# You can defer a field on a subclass
>>> obj = BigChild.objects.defer("other").get(name="b2")
>>> count_delayed_fields(obj)
1
>>> obj.name
u"b2"
>>> obj.value
u"foo"
>>> obj.other
u"bar"
>>> obj.name = "b3"
>>> obj.save()

# You can retrieve a single field on a baseclass
>>> obj = BigChild.objects.only("name").get(name="b3")
>>> count_delayed_fields(obj)
4
>>> obj.name
u"b3"
>>> obj.value
u"foo"
>>> obj.other
u"bar"
>>> obj.name = "b4"
>>> obj.save()

# You can retrieve a single field on a baseclass
>>> obj = BigChild.objects.only("other").get(name="b4")
>>> count_delayed_fields(obj)
4
>>> obj.name
u"b4"
>>> obj.value
u"foo"
>>> obj.other
u"bar"
>>> obj.name = "bb"
>>> obj.save()

"""}
