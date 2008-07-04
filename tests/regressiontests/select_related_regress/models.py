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

__test__ = {'API_TESTS': """
Regression test for bug #7110. When using select_related(), we must query the
Device and Building tables using two different aliases (each) in order to
differentiate the start and end Connection fields. The net result is that both
the "connections = ..." queries here should give the same results.

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

"""}
