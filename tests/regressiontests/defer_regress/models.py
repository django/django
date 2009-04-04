"""
Regression tests for defer() / only() behavior.
"""

from django.conf import settings
from django.db import connection, models

class Item(models.Model):
    name = models.CharField(max_length=15)
    text = models.TextField(default="xyzzy")
    value = models.IntegerField()
    other_value = models.IntegerField(default=0)

    def __unicode__(self):
        return self.name

class RelatedItem(models.Model):
    item = models.ForeignKey(Item)

class Child(models.Model):
    name = models.CharField(max_length=10)
    value = models.IntegerField()

class Leaf(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child)
    value = models.IntegerField(default=42)

    def __unicode__(self):
        return self.name

__test__ = {"regression_tests": """
Deferred fields should really be deferred and not accidentally use the field's
default value just because they aren't passed to __init__.

>>> settings.DEBUG = True
>>> _ = Item.objects.create(name="first", value=42)
>>> obj = Item.objects.only("name", "other_value").get(name="first")

# Accessing "name" doesn't trigger a new database query. Accessing "value" or
# "text" should.
>>> num = len(connection.queries)
>>> obj.name
u"first"
>>> obj.other_value
0
>>> len(connection.queries) == num
True
>>> obj.value
42
>>> len(connection.queries) == num + 1      # Effect of values lookup.
True
>>> obj.text
u"xyzzy"
>>> len(connection.queries) == num + 2      # Effect of text lookup.
True
>>> obj.text
u"xyzzy"
>>> len(connection.queries) == num + 2
True

>>> settings.DEBUG = False

Regression test for #10695. Make sure different instances don't inadvertently
share data in the deferred descriptor objects.

>>> i = Item.objects.create(name="no I'm first", value=37)
>>> items = Item.objects.only('value').order_by('-value')
>>> items[0].name
u'first'
>>> items[1].name
u"no I'm first"

>>> _ = RelatedItem.objects.create(item=i)
>>> r = RelatedItem.objects.defer('item').get()
>>> r.item_id == i.id
True
>>> r.item == i
True

Some further checks for select_related() and inherited model behaviour
(regression for #10710).

>>> c1 = Child.objects.create(name="c1", value=42)
>>> obj = Leaf.objects.create(name="l1", child=c1)

>>> obj = Leaf.objects.only("name", "child").select_related()[0]
>>> obj.child.name
u'c1'

"""
}
