from __future__ import unicode_literals

from django.test import TestCase
from django.utils import six

from .models import (
    A, B, Building, C, Chick, Child, Class, Client, ClientStatus, Connection,
    Country, Device, Enrollment, Hen, Item, Organizer, Person, Port,
    SpecialClient, State, Student, TUser,
)


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

        b = Building.objects.create(name='101')
        dev1 = Device.objects.create(name="router", building=b)
        dev2 = Device.objects.create(name="switch", building=b)
        dev3 = Device.objects.create(name="server", building=b)
        port1 = Port.objects.create(port_number='4', device=dev1)
        port2 = Port.objects.create(port_number='7', device=dev2)
        port3 = Port.objects.create(port_number='1', device=dev3)
        c1 = Connection.objects.create(start=port1, end=port2)
        c2 = Connection.objects.create(start=port2, end=port3)

        connections = Connection.objects.filter(start__device__building=b, end__device__building=b).order_by('id')
        self.assertEqual([(c.id, six.text_type(c.start), six.text_type(c.end)) for c in connections],
            [(c1.id, 'router/4', 'switch/7'), (c2.id, 'switch/7', 'server/1')])

        connections = Connection.objects.filter(start__device__building=b, end__device__building=b).select_related().order_by('id')
        self.assertEqual([(c.id, six.text_type(c.start), six.text_type(c.end)) for c in connections],
            [(c1.id, 'router/4', 'switch/7'), (c2.id, 'switch/7', 'server/1')])

        # This final query should only have seven tables (port, device and building
        # twice each, plus connection once). Thus, 6 joins plus the FROM table.
        self.assertEqual(str(connections.query).count(" JOIN "), 6)

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
        s = Student.objects.create(person=usp)
        o = Organizer.objects.create(person=uop)
        c = Class.objects.create(org=o)
        Enrollment.objects.create(std=s, cls=c)

        e_related = Enrollment.objects.all().select_related()[0]
        self.assertEqual(e_related.std.person.user.name, "std")
        self.assertEqual(e_related.cls.org.person.user.name, "org")

    def test_regression_8036(self):
        """
        Regression test for bug #8036

        the first related model in the tests below
        ("state") is empty and we try to select the more remotely related
        state__country. The regression here was not skipping the empty column results
        for country before getting status.
        """

        Country.objects.create(name='Australia')
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
        Item.objects.create(name="item1", child=c1)
        Item.objects.create(name="item2")

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
        Client.objects.create(name='Brian Burke', state=wa, status=active)
        burke = Client.objects.select_related('state').defer('state__name').get(name='Brian Burke')

        self.assertEqual(burke.name, 'Brian Burke')
        self.assertEqual(burke.state.name, 'Western Australia')

        # Still works if we're dealing with an inherited class
        SpecialClient.objects.create(name='Troy Buswell', state=wa, status=active, value=42)
        troy = SpecialClient.objects.select_related('state').defer('state__name').get(name='Troy Buswell')

        self.assertEqual(troy.name, 'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, 'Western Australia')

        # Still works if we defer an attribute on the inherited class
        troy = SpecialClient.objects.select_related('state').defer('value', 'state__name').get(name='Troy Buswell')

        self.assertEqual(troy.name, 'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, 'Western Australia')

        # Also works if you use only, rather than defer
        troy = SpecialClient.objects.select_related('state').only('name', 'state').get(name='Troy Buswell')

        self.assertEqual(troy.name, 'Troy Buswell')
        self.assertEqual(troy.value, 42)
        self.assertEqual(troy.state.name, 'Western Australia')

    def test_null_join_promotion(self):
        australia = Country.objects.create(name='Australia')
        active = ClientStatus.objects.create(name='active')

        wa = State.objects.create(name="Western Australia", country=australia)
        bob = Client.objects.create(name='Bob', status=active)
        jack = Client.objects.create(name='Jack', status=active, state=wa)
        qs = Client.objects.filter(state=wa).select_related('state')
        with self.assertNumQueries(1):
            self.assertEqual(list(qs), [jack])
            self.assertEqual(qs[0].state, wa)
            # The select_related join wasn't promoted as there was already an
            # existing (even if trimmed) inner join to state.
            self.assertNotIn('LEFT OUTER', str(qs.query))
        qs = Client.objects.select_related('state').order_by('name')
        with self.assertNumQueries(1):
            self.assertEqual(list(qs), [bob, jack])
            self.assertIs(qs[0].state, None)
            self.assertEqual(qs[1].state, wa)
            # The select_related join was promoted as there is already an
            # existing join.
            self.assertIn('LEFT OUTER', str(qs.query))

    def test_regression_19870(self):
        hen = Hen.objects.create(name='Hen')
        Chick.objects.create(name='Chick', mother=hen)

        self.assertEqual(Chick.objects.all()[0].mother.name, 'Hen')
        self.assertEqual(Chick.objects.select_related()[0].mother.name, 'Hen')

    def test_regression_10733(self):
        a = A.objects.create(name='a', lots_of_text='lots_of_text_a', a_field='a_field')
        b = B.objects.create(name='b', lots_of_text='lots_of_text_b', b_field='b_field')
        c = C.objects.create(name='c', lots_of_text='lots_of_text_c', is_published=True,
                             c_a=a, c_b=b)
        results = C.objects.all().only('name', 'lots_of_text', 'c_a', 'c_b', 'c_b__lots_of_text',
                                       'c_a__name', 'c_b__name').select_related()
        self.assertQuerysetEqual(results, [c], lambda x: x)
        with self.assertNumQueries(0):
            qs_c = results[0]
            self.assertEqual(qs_c.name, 'c')
            self.assertEqual(qs_c.lots_of_text, 'lots_of_text_c')
            self.assertEqual(qs_c.c_b.lots_of_text, 'lots_of_text_b')
            self.assertEqual(qs_c.c_a.name, 'a')
            self.assertEqual(qs_c.c_b.name, 'b')

    def test_regression_22508(self):
        building = Building.objects.create(name='101')
        device = Device.objects.create(name="router", building=building)
        Port.objects.create(port_number='1', device=device)

        device = Device.objects.get()
        port = device.port_set.select_related('device__building').get()
        with self.assertNumQueries(0):
            port.device.building
