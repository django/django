"""
Regression tests for defer() / only() behavior.
"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
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
    second_child = models.ForeignKey(Child, related_name="other", null=True)
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
>>> c2 = Child.objects.create(name="c2", value=37)
>>> obj = Leaf.objects.create(name="l1", child=c1, second_child=c2)

>>> obj = Leaf.objects.only("name", "child").select_related()[0]
>>> obj.child.name
u'c1'
>>> Leaf.objects.select_related().only("child__name", "second_child__name")
[<Leaf_Deferred_name_value: l1>]

Models instances with deferred fields should still return the same content
types as their non-deferred versions (bug #10738).
>>> ctype = ContentType.objects.get_for_model
>>> c1 = ctype(Item.objects.all()[0])
>>> c2 = ctype(Item.objects.defer("name")[0])
>>> c3 = ctype(Item.objects.only("name")[0])
>>> c1 is c2 is c3
True

# Regression for #10733 - only() can be used on a model with two foreign keys.
>>> results = Leaf.objects.all().only('name', 'child', 'second_child').select_related()
>>> results[0].child.name
u'c1'
>>> results[0].second_child.name
u'c2'

>>> results = Leaf.objects.all().only('name', 'child', 'second_child', 'child__name', 'second_child__name').select_related()
>>> results[0].child.name
u'c1'
>>> results[0].second_child.name
u'c2'

# Test for #12163 - Pickling error saving session with unsaved model instances.
>>> from django.contrib.sessions.backends.db import SessionStore
>>> SESSION_KEY = '2b1189a188b44ad18c35e1baac6ceead'
>>> item = Item()
>>> item._deferred
False
>>> s = SessionStore(SESSION_KEY)
>>> s.clear()
>>> s['item'] = item
>>> s.save()
>>> s = SessionStore(SESSION_KEY)
>>> s.modified = True
>>> s.save()
>>> i2 = s['item']
>>> i2._deferred # Item must still be non-deferred
False

# Finally, we need to flush the app cache for the defer module.
# Using only/defer creates some artifical entries in the app cache
# that messes up later tests. Purge all entries, just to be sure.
>>> from django.db.models.loading import cache
>>> cache.app_models['defer_regress'] = {}

"""
}
