from django.db import models
from datetime import datetime
from django.contrib.auth.models import User

# Forward declared intermediate model
class Membership(models.Model):
    person = models.ForeignKey('Person')
    group = models.ForeignKey('Group')
    date_joined = models.DateTimeField(default=datetime.now)
    
    def __unicode__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

class UserMembership(models.Model):
    user = models.ForeignKey(User)
    group = models.ForeignKey('Group')
    date_joined = models.DateTimeField(default=datetime.now)
    
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

"""}