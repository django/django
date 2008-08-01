from django.db import models
from datetime import datetime

# M2M described on one of the models
class Person(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ('name',)
        
    def __unicode__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Person, through='Membership')
    custom_members = models.ManyToManyField(Person, through='CustomMembership', related_name="custom")
    nodefaultsnonulls = models.ManyToManyField(Person, through='TestNoDefaultsOrNulls', related_name="testnodefaultsnonulls")

    class Meta:
        ordering = ('name',)
            
    def __unicode__(self):
        return self.name

class Membership(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    date_joined = models.DateTimeField(default=datetime.now)
    invite_reason = models.CharField(max_length=64, null=True)

    class Meta:
        ordering = ('date_joined', 'invite_reason', 'group')
    
    def __unicode__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

class CustomMembership(models.Model):
    person = models.ForeignKey(Person, db_column="custom_person_column", related_name="custom_person_related_name")
    group = models.ForeignKey(Group)
    weird_fk = models.ForeignKey(Membership, null=True)
    date_joined = models.DateTimeField(default=datetime.now)
    
    def __unicode__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)
    
    class Meta:
        db_table = "test_table"

class TestNoDefaultsOrNulls(models.Model):
    person = models.ForeignKey(Person)
    group = models.ForeignKey(Group)
    nodefaultnonull = models.CharField(max_length=5)

class PersonSelfRefM2M(models.Model):
    name = models.CharField(max_length=5)
    friends = models.ManyToManyField('self', through="Friendship", symmetrical=False)
    
    def __unicode__(self):
        return self.name

class Friendship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2M, related_name="rel_to_set")
    date_friended = models.DateTimeField()

__test__ = {'API_TESTS':"""
>>> from datetime import datetime

### Creation and Saving Tests ###

>>> bob = Person.objects.create(name='Bob')
>>> jim = Person.objects.create(name='Jim')
>>> jane = Person.objects.create(name='Jane')
>>> rock = Group.objects.create(name='Rock')
>>> roll = Group.objects.create(name='Roll')

# We start out by making sure that the Group 'rock' has no members.
>>> rock.members.all()
[]

# To make Jim a member of Group Rock, simply create a Membership object.
>>> m1 = Membership.objects.create(person=jim, group=rock)

# We can do the same for Jane and Rock.
>>> m2 = Membership.objects.create(person=jane, group=rock)

# Let's check to make sure that it worked.  Jane and Jim should be members of Rock.
>>> rock.members.all()
[<Person: Jane>, <Person: Jim>]

# Now we can add a bunch more Membership objects to test with.
>>> m3 = Membership.objects.create(person=bob, group=roll)
>>> m4 = Membership.objects.create(person=jim, group=roll)
>>> m5 = Membership.objects.create(person=jane, group=roll)

# We can get Jim's Group membership as with any ForeignKey.
>>> jim.group_set.all()
[<Group: Rock>, <Group: Roll>]

# Querying the intermediary model works like normal.  
# In this case we get Jane's membership to Rock.
>>> m = Membership.objects.get(person=jane, group=rock)
>>> m
<Membership: Jane is a member of Rock>

# Now we set some date_joined dates for further testing.
>>> m2.invite_reason = "She was just awesome."
>>> m2.date_joined = datetime(2006, 1, 1)
>>> m2.save()

>>> m5.date_joined = datetime(2004, 1, 1)
>>> m5.save()

>>> m3.date_joined = datetime(2004, 1, 1)
>>> m3.save()

# It's not only get that works. Filter works like normal as well.
>>> Membership.objects.filter(person=jim)
[<Membership: Jim is a member of Rock>, <Membership: Jim is a member of Roll>]


### Forward Descriptors Tests ###

# Due to complications with adding via an intermediary model, 
# the add method is not provided.
>>> rock.members.add(bob)
Traceback (most recent call last):
...
AttributeError: 'ManyRelatedManager' object has no attribute 'add'

# Create is also disabled as it suffers from the same problems as add.
>>> rock.members.create(name='Anne')
Traceback (most recent call last):
...
AttributeError: Cannot use create() on a ManyToManyField which specifies an intermediary model. Use Membership's Manager instead.

# Remove has similar complications, and is not provided either.
>>> rock.members.remove(jim)
Traceback (most recent call last):
...
AttributeError: 'ManyRelatedManager' object has no attribute 'remove'

# Here we back up the list of all members of Rock.
>>> backup = list(rock.members.all())

# ...and we verify that it has worked.
>>> backup
[<Person: Jane>, <Person: Jim>]

# The clear function should still work.
>>> rock.members.clear()

# Now there will be no members of Rock.
>>> rock.members.all()
[]

# Assignment should not work with models specifying a through model for many of
# the same reasons as adding.
>>> rock.members = backup
Traceback (most recent call last):
...
AttributeError: Cannot set values on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

# Let's re-save those instances that we've cleared.
>>> m1.save()
>>> m2.save()

# Verifying that those instances were re-saved successfully.
>>> rock.members.all()
[<Person: Jane>, <Person: Jim>]


### Reverse Descriptors Tests ###

# Due to complications with adding via an intermediary model, 
# the add method is not provided.
>>> bob.group_set.add(rock)
Traceback (most recent call last):
...
AttributeError: 'ManyRelatedManager' object has no attribute 'add'

# Create is also disabled as it suffers from the same problems as add.
>>> bob.group_set.create(name='Funk')
Traceback (most recent call last):
...
AttributeError: Cannot use create() on a ManyToManyField which specifies an intermediary model. Use Membership's Manager instead.

# Remove has similar complications, and is not provided either.
>>> jim.group_set.remove(rock)
Traceback (most recent call last):
...
AttributeError: 'ManyRelatedManager' object has no attribute 'remove'

# Here we back up the list of all of Jim's groups.
>>> backup = list(jim.group_set.all())
>>> backup
[<Group: Rock>, <Group: Roll>]

# The clear function should still work.
>>> jim.group_set.clear()

# Now Jim will be in no groups.
>>> jim.group_set.all()
[]

# Assignment should not work with models specifying a through model for many of
# the same reasons as adding.
>>> jim.group_set = backup
Traceback (most recent call last):
...
AttributeError: Cannot set values on a ManyToManyField which specifies an intermediary model.  Use Membership's Manager instead.

# Let's re-save those instances that we've cleared.
>>> m1.save()
>>> m4.save()

# Verifying that those instances were re-saved successfully.
>>> jim.group_set.all()
[<Group: Rock>, <Group: Roll>]

### Custom Tests ###

# Let's see if we can query through our second relationship.
>>> rock.custom_members.all()
[]

# We can query in the opposite direction as well.
>>> bob.custom.all()
[]

# Let's create some membership objects in this custom relationship.
>>> cm1 = CustomMembership.objects.create(person=bob, group=rock)
>>> cm2 = CustomMembership.objects.create(person=jim, group=rock)

# If we get the number of people in Rock, it should be both Bob and Jim.
>>> rock.custom_members.all()
[<Person: Bob>, <Person: Jim>]

# Bob should only be in one custom group.
>>> bob.custom.all()
[<Group: Rock>]

# Let's make sure our new descriptors don't conflict with the FK related_name.
>>> bob.custom_person_related_name.all()
[<CustomMembership: Bob is a member of Rock>]

### SELF-REFERENTIAL TESTS ###

# Let's first create a person who has no friends.
>>> tony = PersonSelfRefM2M.objects.create(name="Tony")
>>> tony.friends.all()
[]

# Now let's create another person for Tony to be friends with.
>>> chris = PersonSelfRefM2M.objects.create(name="Chris")
>>> f = Friendship.objects.create(first=tony, second=chris, date_friended=datetime.now())

# Tony should now show that Chris is his friend.
>>> tony.friends.all()
[<PersonSelfRefM2M: Chris>]

# But we haven't established that Chris is Tony's Friend.
>>> chris.friends.all()
[]

# So let's do that now.
>>> f2 = Friendship.objects.create(first=chris, second=tony, date_friended=datetime.now())

# Having added Chris as a friend, let's make sure that his friend set reflects
# that addition.
>>> chris.friends.all()
[<PersonSelfRefM2M: Tony>]

# Chris gets mad and wants to get rid of all of his friends.
>>> chris.friends.clear()

# Now he should not have any more friends.
>>> chris.friends.all()
[]

# Since this isn't a symmetrical relation, Tony's friend link still exists.
>>> tony.friends.all()
[<PersonSelfRefM2M: Chris>]



### QUERY TESTS ###

# We can query for the related model by using its attribute name (members, in 
# this case).
>>> Group.objects.filter(members__name='Bob')
[<Group: Roll>]

# To query through the intermediary model, we specify its model name.
# In this case, membership.
>>> Group.objects.filter(membership__invite_reason="She was just awesome.")
[<Group: Rock>]

# If we want to query in the reverse direction by the related model, use its
# model name (group, in this case).
>>> Person.objects.filter(group__name="Rock")
[<Person: Jane>, <Person: Jim>]

# If the m2m field has specified a related_name, using that will work.
>>> Person.objects.filter(custom__name="Rock")
[<Person: Bob>, <Person: Jim>]

# To query through the intermediary model in the reverse direction, we again
# specify its model name (membership, in this case).
>>> Person.objects.filter(membership__invite_reason="She was just awesome.")
[<Person: Jane>]

# Let's see all of the groups that Jane joined after 1 Jan 2005:
>>> Group.objects.filter(membership__date_joined__gt=datetime(2005, 1, 1), membership__person =jane)
[<Group: Rock>]

# Queries also work in the reverse direction: Now let's see all of the people 
# that have joined Rock since 1 Jan 2005:
>>> Person.objects.filter(membership__date_joined__gt=datetime(2005, 1, 1), membership__group=rock)
[<Person: Jane>, <Person: Jim>]

# Conceivably, queries through membership could return correct, but non-unique
# querysets.  To demonstrate this, we query for all people who have joined a 
# group after 2004:
>>> Person.objects.filter(membership__date_joined__gt=datetime(2004, 1, 1))
[<Person: Jane>, <Person: Jim>, <Person: Jim>]

# Jim showed up twice, because he joined two groups ('Rock', and 'Roll'):
>>> [(m.person.name, m.group.name) for m in 
... Membership.objects.filter(date_joined__gt=datetime(2004, 1, 1))]
[(u'Jane', u'Rock'), (u'Jim', u'Rock'), (u'Jim', u'Roll')]

# QuerySet's distinct() method can correct this problem.
>>> Person.objects.filter(membership__date_joined__gt=datetime(2004, 1, 1)).distinct()
[<Person: Jane>, <Person: Jim>]
"""}