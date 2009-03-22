"""
Regression tests for defer() / only() behavior.
"""

from django.conf import settings
from django.db import connection, models

class Item(models.Model):
    name = models.CharField(max_length=10)
    text = models.TextField(default="xyzzy")
    value = models.IntegerField()
    other_value = models.IntegerField(default=0)

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

>>> settings.DEBUG = False

"""
}

