"""
Tests for forcing insert and update queries (instead of Django's normal
automatic behaviour).
"""
from django.db import models, transaction

class Counter(models.Model):
    name = models.CharField(max_length = 10)
    value = models.IntegerField()

class WithCustomPK(models.Model):
    name = models.IntegerField(primary_key=True)
    value = models.IntegerField()

__test__ = {"API_TESTS": """
>>> c = Counter.objects.create(name="one", value=1)

# The normal case
>>> c.value = 2
>>> c.save()

# Same thing, via an update
>>> c.value = 3
>>> c.save(force_update=True)

# Won't work because force_update and force_insert are mutually exclusive
>>> c.value = 4
>>> c.save(force_insert=True, force_update=True)
Traceback (most recent call last):
...
ValueError: Cannot force both insert and updating in model saving.

# Try to update something that doesn't have a primary key in the first place.
>>> c1 = Counter(name="two", value=2)
>>> c1.save(force_update=True)
Traceback (most recent call last):
...
ValueError: Cannot force an update in save() with no primary key.

>>> c1.save(force_insert=True)

# Won't work because we can't insert a pk of the same value.
>>> sid = transaction.savepoint()
>>> c.value = 5
>>> c.save(force_insert=True)
Traceback (most recent call last):
...
IntegrityError: ...
>>> transaction.savepoint_rollback(sid)

# Trying to update should still fail, even with manual primary keys, if the
# data isn't in the database already.
>>> obj = WithCustomPK(name=1, value=1)
>>> obj.save(force_update=True)
Traceback (most recent call last):
...
DatabaseError: ...

"""
}
