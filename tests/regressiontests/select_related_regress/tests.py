from django.test import TestCase
from regressiontests.select_related_regress.models import *

class SelectRelatedRegressTests(TestCase):

    def test_regression_7110(self):
        """
        Regression test for bug #7110.

        When using select_related(), we must query the
        Device and Building tables using two different aliases (each) in order to
        differentiate the start and end Connection fields. The net result is that
        both the "connections = ..." queries here should give the same results
        without pulling in more than the absolute minimum number of tables
        (history has shown that it's easy to make a mistake in the implementation
        and include some unnecessary bonus joins).
        """

        b=Building.objects.create(name='101')
        dev1=Device.objects.create(name="router", building=b)
        dev2=Device.objects.create(name="switch", building=b)
        dev3=Device.objects.create(name="server", building=b)
        port1=Port.objects.create(port_number='4',device=dev1)
        port2=Port.objects.create(port_number='7',device=dev2)
        port3=Port.objects.create(port_number='1',device=dev3)
        c1=Connection.objects.create(start=port1, end=port2)
        c2=Connection.objects.create(start=port2, end=port3)

        connections=Connection.objects.filter(start__device__building=b, end__device__building=b).order_by('id')
        self.assertEqual([(c.id, unicode(c.start), unicode(c.end)) for c in connections],
            [(c1.id, u'router/4', u'switch/7'), (c2.id, u'switch/7', u'server/1')])

        connections=Connection.objects.filter(start__device__building=b, end__device__building=b).select_related().order_by('id')
        self.assertEqual([(c.id, unicode(c.start), unicode(c.end)) for c in connections],
            [(c1.id, u'router/4', u'switch/7'), (c2.id, u'switch/7', u'server/1')])

        # This final query should only join seven tables (port, device and building
        # twice each, plus connection once).
        self.assertEqual(connections.query.count_active_tables(), 7)


    def test_regression_8106(self):
        """
        Regression test for bug #8106.

        Same sort of problem as the previous test, but this time there are
        more extra tables to pull in as part of the select_related() and some
        of them could potentially clash (so need to be kept separate).
        """

        us = TUser.objects.create(name="std")
        usp = Person.objects.create(user=us)
        uo = TUser.objects.create(name="org")
        uop = Person.objects.create(user=uo)
        s = Student.objects.create(person = usp)
        o = Organizer.objects.create(person = uop)
        c = Class.objects.create(org=o)
        e = Enrollment.objects.create(std=s, cls=c)

        e_related = Enrollment.objects.all().select_related()[0]
        self.assertEqual(e_related.std.person.user.name, u"std")
        self.assertEqual(e_related.cls.org.person.user.name, u"org")

    def test_regression_8036(self):
        """
        Regression test for bug #8036

        the first related model in the tests below
        ("state") is empty and we try to select the more remotely related
        state__country. The regression here was not skipping the empty column results
        for country before getting status.
        """

        australia = Country.objects.create(name='Australia')
        active = ClientStatus.objects.create(name='active')
        client = Client.objects.create(name='client', status=active)

        self.assertEqual(client.status, active)
        self.assertEqual(Client.objects.select_related()[0].status, active)
        self.assertEqual(Client.objects.select_related('state')[0].status, active)
        self.assertEqual(Client.objects.select_related('state', 'status')[0].status, active)
        self.assertEqual(Client.objects.select_related('state__country')[0].status, active)
        self.assertEqual(Client.objects.select_related('state__country', 'status')[0].status, active)
        self.assertEqual(Client.objects.select_related('status')[0].status, active)

    def test_multi_table_inheritance(self):
        """ Exercising select_related() with multi-table model inheritance. """
        c1 = Child.objects.create(name="child1", value=42)
        i1 = Item.objects.create(name="item1", child=c1)
        i2 = Item.objects.create(name="item2")

        self.assertQuerysetEqual(
                Item.objects.select_related("child").order_by("name"),
                ["<Item: item1>", "<Item: item2>"]
        )

    def test_regression_12851(self):
        """
        Regression for #12851

        Deferred fields are used correctly if you select_related a subset
        of fields.
        """
        australia = Country.objects.create(name='Australia')
        active = ClientStatus.objects.create(name='active')

        wa = State.objects.create(name="Western Australia", country=australia)
        c1 = Client.objects.create(name='Brian Burke', state=wa, status=active)
        burke = Client.objects.select_related('state').defer('state__name').get(name='Brian Burke')

        self.assertEqual(burke.name, u'Brian Burke')
        self.assertEqual(burke.state.name, u'Western Australia')

        # Still works if we're dealing with an inherited class
        sc1 = SpecialClient.objects.create(name='Troy Buswell', state=wa, status=active, value=42)
        troy = SpecialClient.objects.select_related('state').defer('state__name').get(name='Troy Buswell')

        self.assertEqual(troy.name, u'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, u'Western Australia')

        # Still works if we defer an attribute on the inherited class
        troy = SpecialClient.objects.select_related('state').defer('value', 'state__name').get(name='Troy Buswell')

        self.assertEqual(troy.name, u'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, u'Western Australia')

        # Also works if you use only, rather than defer
        troy = SpecialClient.objects.select_related('state').only('name').get(name='Troy Buswell')

        self.assertEqual(troy.name, u'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, u'Western Australia')
