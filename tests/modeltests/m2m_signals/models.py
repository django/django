"""
Testing signals emitted on changing m2m relations.
"""

from django.db import models

class Part(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

class Car(models.Model):
    name = models.CharField(max_length=20)
    default_parts = models.ManyToManyField(Part)
    optional_parts = models.ManyToManyField(Part, related_name='cars_optional')

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

class SportsCar(Car):
    price = models.IntegerField()

class Person(models.Model):
    name = models.CharField(max_length=20)
    fans = models.ManyToManyField('self', related_name='idols', symmetrical=False)
    friends = models.ManyToManyField('self')

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

def m2m_changed_test(signal, sender, **kwargs):
    print 'm2m_changed signal'
    print 'instance:', kwargs['instance']
    print 'action:', kwargs['action']
    print 'reverse:', kwargs['reverse']
    print 'model:', kwargs['model']
    if kwargs['pk_set']:
        print 'objects:',kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])


__test__ = {'API_TESTS':"""
# Install a listener on one of the two m2m relations.
>>> models.signals.m2m_changed.connect(m2m_changed_test, Car.optional_parts.through)

# Test the add, remove and clear methods on both sides of the
# many-to-many relation

>>> c1 = Car.objects.create(name='VW')
>>> c2 = Car.objects.create(name='BMW')
>>> c3 = Car.objects.create(name='Toyota')
>>> p1 = Part.objects.create(name='Wheelset')
>>> p2 = Part.objects.create(name='Doors')
>>> p3 = Part.objects.create(name='Engine')
>>> p4 = Part.objects.create(name='Airbag')
>>> p5 = Part.objects.create(name='Sunroof')

# adding a default part to our car - no signal listener installed
>>> c1.default_parts.add(p5)

# Now install a listener
>>> models.signals.m2m_changed.connect(m2m_changed_test, Car.default_parts.through)

>>> c1.default_parts.add(p1, p2, p3)
m2m_changed signal
instance: VW
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>, <Part: Engine>, <Part: Wheelset>]
m2m_changed signal
instance: VW
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>, <Part: Engine>, <Part: Wheelset>]

# give the BMW and Toyata some doors as well
>>> p2.car_set.add(c2, c3)
m2m_changed signal
instance: Doors
action: pre_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: BMW>, <Car: Toyota>]
m2m_changed signal
instance: Doors
action: post_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: BMW>, <Car: Toyota>]

# remove the engine from the VW and the airbag (which is not set but is returned)
>>> c1.default_parts.remove(p3, p4)
m2m_changed signal
instance: VW
action: pre_remove
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Airbag>, <Part: Engine>]
m2m_changed signal
instance: VW
action: post_remove
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Airbag>, <Part: Engine>]

# give the VW some optional parts (second relation to same model)
>>> c1.optional_parts.add(p4,p5)
m2m_changed signal
instance: VW
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Airbag>, <Part: Sunroof>]
m2m_changed signal
instance: VW
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Airbag>, <Part: Sunroof>]

# add airbag to all the cars (even though the VW already has one)
>>> p4.cars_optional.add(c1, c2, c3)
m2m_changed signal
instance: Airbag
action: pre_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: BMW>, <Car: Toyota>]
m2m_changed signal
instance: Airbag
action: post_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: BMW>, <Car: Toyota>]

# remove airbag from the VW (reverse relation with custom related_name)
>>> p4.cars_optional.remove(c1)
m2m_changed signal
instance: Airbag
action: pre_remove
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: VW>]
m2m_changed signal
instance: Airbag
action: post_remove
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: VW>]

# clear all parts of the VW
>>> c1.default_parts.clear()
m2m_changed signal
instance: VW
action: pre_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
m2m_changed signal
instance: VW
action: post_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>

# take all the doors off of cars
>>> p2.car_set.clear()
m2m_changed signal
instance: Doors
action: pre_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
m2m_changed signal
instance: Doors
action: post_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>

# take all the airbags off of cars (clear reverse relation with custom related_name)
>>> p4.cars_optional.clear()
m2m_changed signal
instance: Airbag
action: pre_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
m2m_changed signal
instance: Airbag
action: post_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>

# alternative ways of setting relation:

>>> c1.default_parts.create(name='Windows')
m2m_changed signal
instance: VW
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Windows>]
m2m_changed signal
instance: VW
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Windows>]
<Part: Windows>

# direct assignment clears the set first, then adds
>>> c1.default_parts = [p1,p2,p3]
m2m_changed signal
instance: VW
action: pre_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
m2m_changed signal
instance: VW
action: post_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
m2m_changed signal
instance: VW
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>, <Part: Engine>, <Part: Wheelset>]
m2m_changed signal
instance: VW
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>, <Part: Engine>, <Part: Wheelset>]

# Check that signals still work when model inheritance is involved
>>> c4 = SportsCar.objects.create(name='Bugatti', price='1000000')
>>> c4.default_parts = [p2]
m2m_changed signal
instance: Bugatti
action: pre_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
m2m_changed signal
instance: Bugatti
action: post_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
m2m_changed signal
instance: Bugatti
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>]
m2m_changed signal
instance: Bugatti
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Part'>
objects: [<Part: Doors>]

>>> p3.car_set.add(c4)
m2m_changed signal
instance: Engine
action: pre_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: Bugatti>]
m2m_changed signal
instance: Engine
action: post_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Car'>
objects: [<Car: Bugatti>]

# Now test m2m relations with self
>>> p1 = Person.objects.create(name='Alice')
>>> p2 = Person.objects.create(name='Bob')
>>> p3 = Person.objects.create(name='Chuck')
>>> p4 = Person.objects.create(name='Daisy')

>>> models.signals.m2m_changed.connect(m2m_changed_test, Person.fans.through)
>>> models.signals.m2m_changed.connect(m2m_changed_test, Person.friends.through)

>>> p1.friends = [p2, p3]
m2m_changed signal
instance: Alice
action: pre_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Alice
action: post_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Alice
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Bob>, <Person: Chuck>]
m2m_changed signal
instance: Alice
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Bob>, <Person: Chuck>]

>>> p1.fans = [p4]
m2m_changed signal
instance: Alice
action: pre_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Alice
action: post_clear
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Alice
action: pre_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Daisy>]
m2m_changed signal
instance: Alice
action: post_add
reverse: False
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Daisy>]

>>> p3.idols = [p1,p2]
m2m_changed signal
instance: Chuck
action: pre_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Chuck
action: post_clear
reverse: True
model: <class 'modeltests.m2m_signals.models.Person'>
m2m_changed signal
instance: Chuck
action: pre_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Alice>, <Person: Bob>]
m2m_changed signal
instance: Chuck
action: post_add
reverse: True
model: <class 'modeltests.m2m_signals.models.Person'>
objects: [<Person: Alice>, <Person: Bob>]

# Cleanup - disconnect all signal handlers
>>> models.signals.m2m_changed.disconnect(m2m_changed_test, Car.default_parts.through)
>>> models.signals.m2m_changed.disconnect(m2m_changed_test, Car.optional_parts.through)
>>> models.signals.m2m_changed.disconnect(m2m_changed_test, Person.fans.through)
>>> models.signals.m2m_changed.disconnect(m2m_changed_test, Person.friends.through)

"""}
