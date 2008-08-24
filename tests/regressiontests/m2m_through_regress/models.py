from datetime import datetime
from django.contrib.auth.models import User
from django.core import management
from django.db import models

# Forward declared intermediate model
class Membership(models.Model):
    person = models.ForeignKey('Person')
    group = models.ForeignKey('Group')
    price = models.IntegerField(default=100)

    def __unicode__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

class UserMembership(models.Model):
    user = models.ForeignKey(User)
    group = models.ForeignKey('Group')
    price = models.IntegerField(default=100)

    def __unicode__(self):
        return "%s is a user and member of %s" % (self.user.username, self.group.name)

class Person(models.Model):
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=128)
    # Membership object defined as a class
    members = models.ManyToManyField(Person, through=Membership)
    user_members = models.ManyToManyField(User, through='UserMembership')

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS':"""
# Create some dummy data
>>> bob = Person.objects.create(name='Bob')
>>> jim = Person.objects.create(name='Jim')

>>> rock = Group.objects.create(name='Rock')
>>> roll = Group.objects.create(name='Roll')

>>> frank = User.objects.create_user('frank','frank@example.com','password')
>>> jane = User.objects.create_user('jane','jane@example.com','password')

# Now test that the forward declared Membership works
>>> Membership.objects.create(person=bob, group=rock)
<Membership: Bob is a member of Rock>

>>> Membership.objects.create(person=bob, group=roll)
<Membership: Bob is a member of Roll>

>>> Membership.objects.create(person=jim, group=rock)
<Membership: Jim is a member of Rock>

>>> bob.group_set.all()
[<Group: Rock>, <Group: Roll>]

>>> roll.members.all()
[<Person: Bob>]

# Error messages use the model name, not repr of the class name
>>> bob.group_set = []
Traceback (most recent call last):
...
AttributeError: Cannot set values on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

>>> roll.members = []
Traceback (most recent call last):
...
AttributeError: Cannot set values on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

>>> rock.members.create(name='Anne')
Traceback (most recent call last):
...
AttributeError: Cannot use create() on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

>>> bob.group_set.create(name='Funk')
Traceback (most recent call last):
...
AttributeError: Cannot use create() on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

# Now test that the intermediate with a relationship outside
# the current app (i.e., UserMembership) workds
>>> UserMembership.objects.create(user=frank, group=rock)
<UserMembership: frank is a user and member of Rock>

>>> UserMembership.objects.create(user=frank, group=roll)
<UserMembership: frank is a user and member of Roll>

>>> UserMembership.objects.create(user=jane, group=rock)
<UserMembership: jane is a user and member of Rock>

>>> frank.group_set.all()
[<Group: Rock>, <Group: Roll>]

>>> roll.user_members.all()
[<User: frank>]

# Regression test for #8134 --
# m2m-through models shouldn't be serialized as m2m fields on the model.

# First, clean up a lot of objects we don't need.
# The serialization test only requires three objects to work -
# one for each end of the m2m, plus the through model.

>>> User.objects.all().delete()
>>> UserMembership.objects.all().delete()
>>> frank.delete()
>>> rock.delete()
>>> jim.delete()

# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'm2m_through_regress', format='json', indent=2)
[
  {
    "pk": 2,
    "model": "m2m_through_regress.membership",
    "fields": {
      "person": 1,
      "price": 100,
      "group": 2
    }
  },
  {
    "pk": 1,
    "model": "m2m_through_regress.person",
    "fields": {
      "name": "Bob"
    }
  },
  {
    "pk": 2,
    "model": "m2m_through_regress.group",
    "fields": {
      "name": "Roll"
    }
  }
]

# Check the XML serializer too, since it doesn't use the common implementation
>>> management.call_command('dumpdata', 'm2m_through_regress', format='xml', indent=2)
<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object pk="2" model="m2m_through_regress.membership">
    <field to="m2m_through_regress.person" name="person" rel="ManyToOneRel">1</field>
    <field to="m2m_through_regress.group" name="group" rel="ManyToOneRel">2</field>
    <field type="IntegerField" name="price">100</field>
  </object>
  <object pk="1" model="m2m_through_regress.person">
    <field type="CharField" name="name">Bob</field>
  </object>
  <object pk="2" model="m2m_through_regress.group">
    <field type="CharField" name="name">Roll</field>
  </object>
</django-objects>

## Regression test for #8046:
Check that we don't involve too many copies of the intermediate table when
doing a join.

>>> bob = Person.objects.create(name='Bob')
>>> jim = Person.objects.create(name='Jim')
>>> rock = Group.objects.create(name='Rock')
>>> roll = Group.objects.create(name='Roll')
>>> _ = Membership.objects.create(person=bob, group=rock)
>>> _ = Membership.objects.create(person=jim, group=rock, price=50)
>>> _ = Membership.objects.create(person=bob, group=roll, price=50)
>>> rock.members.filter(membership__price=50)
[<Person: Jim>]

## Regression test for #8254
>>> bob.group_set.filter(membership__price=50)
[<Group: Roll>]

"""}
