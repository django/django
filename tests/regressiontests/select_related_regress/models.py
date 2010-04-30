from django.db import models

class Building(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return u"Building: %s" % self.name

class Device(models.Model):
    building = models.ForeignKey('Building')
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return u"device '%s' in building %s" % (self.name, self.building)

class Port(models.Model):
    device = models.ForeignKey('Device')
    port_number = models.CharField(max_length=10)

    def __unicode__(self):
        return u"%s/%s" % (self.device.name, self.port_number)

class Connection(models.Model):
    start = models.ForeignKey(Port, related_name='connection_start',
            unique=True)
    end = models.ForeignKey(Port, related_name='connection_end', unique=True)

    def __unicode__(self):
        return u"%s to %s" % (self.start, self.end)

# Another non-tree hierarchy that exercises code paths similar to the above
# example, but in a slightly different configuration.
class TUser(models.Model):
    name = models.CharField(max_length=200)

class Person(models.Model):
    user = models.ForeignKey(TUser, unique=True)

class Organizer(models.Model):
    person = models.ForeignKey(Person)

class Student(models.Model):
    person = models.ForeignKey(Person)

class Class(models.Model):
    org = models.ForeignKey(Organizer)

class Enrollment(models.Model):
    std = models.ForeignKey(Student)
    cls = models.ForeignKey(Class)

# Models for testing bug #8036.
class Country(models.Model):
    name = models.CharField(max_length=50)

class State(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country)

class ClientStatus(models.Model):
    name = models.CharField(max_length=50)

class Client(models.Model):
    name = models.CharField(max_length=50)
    state = models.ForeignKey(State, null=True)
    status = models.ForeignKey(ClientStatus)

class SpecialClient(Client):
    value = models.IntegerField()

# Some model inheritance exercises
class Parent(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

class Child(Parent):
    value = models.IntegerField()

class Item(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child, null=True)

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS': """
Regression test for bug #7110. When using select_related(), we must query the
Device and Building tables using two different aliases (each) in order to
differentiate the start and end Connection fields. The net result is that both
the "connections = ..." queries here should give the same results without
pulling in more than the absolute minimum number of tables (history has
shown that it's easy to make a mistake in the implementation and include some
unnecessary bonus joins).

>>> b=Building.objects.create(name='101')
>>> dev1=Device.objects.create(name="router", building=b)
>>> dev2=Device.objects.create(name="switch", building=b)
>>> dev3=Device.objects.create(name="server", building=b)
>>> port1=Port.objects.create(port_number='4',device=dev1)
>>> port2=Port.objects.create(port_number='7',device=dev2)
>>> port3=Port.objects.create(port_number='1',device=dev3)
>>> c1=Connection.objects.create(start=port1, end=port2)
>>> c2=Connection.objects.create(start=port2, end=port3)

>>> connections=Connection.objects.filter(start__device__building=b, end__device__building=b).order_by('id')
>>> [(c.id, unicode(c.start), unicode(c.end)) for c in connections]
[(1, u'router/4', u'switch/7'), (2, u'switch/7', u'server/1')]

>>> connections=Connection.objects.filter(start__device__building=b, end__device__building=b).select_related().order_by('id')
>>> [(c.id, unicode(c.start), unicode(c.end)) for c in connections]
[(1, u'router/4', u'switch/7'), (2, u'switch/7', u'server/1')]

# This final query should only join seven tables (port, device and building
# twice each, plus connection once).
>>> connections.query.count_active_tables()
7

Regression test for bug #8106. Same sort of problem as the previous test, but
this time there are more extra tables to pull in as part of the
select_related() and some of them could potentially clash (so need to be kept
separate).

>>> us = TUser.objects.create(name="std")
>>> usp = Person.objects.create(user=us)
>>> uo = TUser.objects.create(name="org")
>>> uop = Person.objects.create(user=uo)
>>> s = Student.objects.create(person = usp)
>>> o = Organizer.objects.create(person = uop)
>>> c = Class.objects.create(org=o)
>>> e = Enrollment.objects.create(std=s, cls=c)

>>> e_related = Enrollment.objects.all().select_related()[0]
>>> e_related.std.person.user.name
u"std"
>>> e_related.cls.org.person.user.name
u"org"

Regression test for bug #8036: the first related model in the tests below
("state") is empty and we try to select the more remotely related
state__country. The regression here was not skipping the empty column results
for country before getting status.

>>> australia = Country.objects.create(name='Australia')
>>> active = ClientStatus.objects.create(name='active')
>>> client = Client.objects.create(name='client', status=active)

>>> client.status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related()[0].status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related('state')[0].status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related('state', 'status')[0].status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related('state__country')[0].status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related('state__country', 'status')[0].status
<ClientStatus: ClientStatus object>
>>> Client.objects.select_related('status')[0].status
<ClientStatus: ClientStatus object>

Exercising select_related() with multi-table model inheritance.
>>> c1 = Child.objects.create(name="child1", value=42)
>>> _ = Item.objects.create(name="item1", child=c1)
>>> _ = Item.objects.create(name="item2")
>>> Item.objects.select_related("child").order_by("name")
[<Item: item1>, <Item: item2>]

# Regression for #12851 - Deferred fields are used correctly if you
# select_related a subset of fields.
>>> wa = State.objects.create(name="Western Australia", country=australia)
>>> _ = Client.objects.create(name='Brian Burke', state=wa, status=active)
>>> burke = Client.objects.select_related('state').defer('state__name').get(name='Brian Burke')
>>> burke.name
u'Brian Burke'
>>> burke.state.name
u'Western Australia'

# Still works if we're dealing with an inherited class
>>> _ = SpecialClient.objects.create(name='Troy Buswell', state=wa, status=active, value=42)
>>> troy = SpecialClient.objects.select_related('state').defer('state__name').get(name='Troy Buswell')
>>> troy.name
u'Troy Buswell'
>>> troy.value
42
>>> troy.state.name
u'Western Australia'

# Still works if we defer an attribute on the inherited class
>>> troy = SpecialClient.objects.select_related('state').defer('value', 'state__name').get(name='Troy Buswell')
>>> troy.name
u'Troy Buswell'
>>> troy.value
42
>>> troy.state.name
u'Western Australia'

# Also works if you use only, rather than defer
>>> troy = SpecialClient.objects.select_related('state').only('name').get(name='Troy Buswell')
>>> troy.name
u'Troy Buswell'
>>> troy.value
42
>>> troy.state.name
u'Western Australia'

"""}
