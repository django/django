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
normal instances when we examine attribut values. Therefore we test for the
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

"""}
