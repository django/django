from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.utils.six import StringIO

from .models import (
    Car, CarDriver, Driver, Group, Membership, Person, UserMembership,
)


class M2MThroughTestCase(TestCase):

    def test_everything(self):
        bob = Person.objects.create(name="Bob")
        jim = Person.objects.create(name="Jim")

        rock = Group.objects.create(name="Rock")
        roll = Group.objects.create(name="Roll")

        frank = User.objects.create_user("frank", "frank@example.com", "password")
        jane = User.objects.create_user("jane", "jane@example.com", "password")

        Membership.objects.create(person=bob, group=rock)
        Membership.objects.create(person=bob, group=roll)
        Membership.objects.create(person=jim, group=rock)

        self.assertQuerysetEqual(
            bob.group_set.all(), [
                "<Group: Rock>",
                "<Group: Roll>",
            ],
            ordered=False
        )

        self.assertQuerysetEqual(
            roll.members.all(), [
                "<Person: Bob>",
            ]
        )

        self.assertRaises(AttributeError, setattr, bob, "group_set", [])
        self.assertRaises(AttributeError, setattr, roll, "members", [])

        self.assertRaises(AttributeError, rock.members.create, name="Anne")
        self.assertRaises(AttributeError, bob.group_set.create, name="Funk")

        UserMembership.objects.create(user=frank, group=rock)
        UserMembership.objects.create(user=frank, group=roll)
        UserMembership.objects.create(user=jane, group=rock)

        self.assertQuerysetEqual(
            frank.group_set.all(), [
                "<Group: Rock>",
                "<Group: Roll>",
            ],
            ordered=False
        )

        self.assertQuerysetEqual(
            roll.user_members.all(), [
                "<User: frank>",
            ]
        )

    def test_serialization(self):
        "m2m-through models aren't serialized as m2m fields. Refs #8134"

        p = Person.objects.create(name="Bob")
        g = Group.objects.create(name="Roll")
        m = Membership.objects.create(person=p, group=g)

        pks = {"p_pk": p.pk, "g_pk": g.pk, "m_pk": m.pk}

        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="json", stdout=out)
        self.assertJSONEqual(out.getvalue().strip(), """[{"pk": %(m_pk)s, "model": "m2m_through_regress.membership", "fields": {"person": %(p_pk)s, "price": 100, "group": %(g_pk)s}}, {"pk": %(p_pk)s, "model": "m2m_through_regress.person", "fields": {"name": "Bob"}}, {"pk": %(g_pk)s, "model": "m2m_through_regress.group", "fields": {"name": "Roll"}}]""" % pks)

        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="xml",
            indent=2, stdout=out)
        self.assertXMLEqual(out.getvalue().strip(), """
<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object pk="%(m_pk)s" model="m2m_through_regress.membership">
    <field to="m2m_through_regress.person" name="person" rel="ManyToOneRel">%(p_pk)s</field>
    <field to="m2m_through_regress.group" name="group" rel="ManyToOneRel">%(g_pk)s</field>
    <field type="IntegerField" name="price">100</field>
  </object>
  <object pk="%(p_pk)s" model="m2m_through_regress.person">
    <field type="CharField" name="name">Bob</field>
  </object>
  <object pk="%(g_pk)s" model="m2m_through_regress.group">
    <field type="CharField" name="name">Roll</field>
  </object>
</django-objects>
        """.strip() % pks)

    def test_join_trimming(self):
        "Check that we don't involve too many copies of the intermediate table when doing a join. Refs #8046, #8254"
        bob = Person.objects.create(name="Bob")
        jim = Person.objects.create(name="Jim")

        rock = Group.objects.create(name="Rock")
        roll = Group.objects.create(name="Roll")

        Membership.objects.create(person=bob, group=rock)
        Membership.objects.create(person=jim, group=rock, price=50)
        Membership.objects.create(person=bob, group=roll, price=50)

        self.assertQuerysetEqual(
            rock.members.filter(membership__price=50), [
                "<Person: Jim>",
            ]
        )

        self.assertQuerysetEqual(
            bob.group_set.filter(membership__price=50), [
                "<Group: Roll>",
            ]
        )


class ToFieldThroughTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(make="Toyota")
        self.driver = Driver.objects.create(name="Ryan Briscoe")
        CarDriver.objects.create(car=self.car, driver=self.driver)
        # We are testing if wrong objects get deleted due to using wrong
        # field value in m2m queries. So, it is essential that the pk
        # numberings do not match.
        # Create one intentionally unused driver to mix up the autonumbering
        self.unused_driver = Driver.objects.create(name="Barney Gumble")
        # And two intentionally unused cars.
        self.unused_car1 = Car.objects.create(make="Trabant")
        self.unused_car2 = Car.objects.create(make="Wartburg")

    def test_to_field(self):
        self.assertQuerysetEqual(
            self.car.drivers.all(),
            ["<Driver: Ryan Briscoe>"]
        )

    def test_to_field_reverse(self):
        self.assertQuerysetEqual(
            self.driver.car_set.all(),
            ["<Car: Toyota>"]
        )

    def test_to_field_clear_reverse(self):
        self.driver.car_set.clear()
        self.assertQuerysetEqual(
            self.driver.car_set.all(), [])

    def test_to_field_clear(self):
        self.car.drivers.clear()
        self.assertQuerysetEqual(
            self.car.drivers.all(), [])

    # Low level tests for _add_items and _remove_items. We test these methods
    # because .add/.remove aren't available for m2m fields with through, but
    # through is the only way to set to_field currently. We do want to make
    # sure these methods are ready if the ability to use .add or .remove with
    # to_field relations is added some day.
    def test_add(self):
        self.assertQuerysetEqual(
            self.car.drivers.all(),
            ["<Driver: Ryan Briscoe>"]
        )
        # Yikes - barney is going to drive...
        self.car.drivers._add_items('car', 'driver', self.unused_driver)
        self.assertQuerysetEqual(
            self.car.drivers.all(),
            ["<Driver: Barney Gumble>", "<Driver: Ryan Briscoe>"]
        )

    def test_add_null(self):
        nullcar = Car.objects.create(make=None)
        with self.assertRaises(ValueError):
            nullcar.drivers._add_items('car', 'driver', self.unused_driver)

    def test_add_related_null(self):
        nulldriver = Driver.objects.create(name=None)
        with self.assertRaises(ValueError):
            self.car.drivers._add_items('car', 'driver', nulldriver)

    def test_add_reverse(self):
        car2 = Car.objects.create(make="Honda")
        self.assertQuerysetEqual(
            self.driver.car_set.all(),
            ["<Car: Toyota>"]
        )
        self.driver.car_set._add_items('driver', 'car', car2)
        self.assertQuerysetEqual(
            self.driver.car_set.all(),
            ["<Car: Toyota>", "<Car: Honda>"],
            ordered=False
        )

    def test_add_null_reverse(self):
        nullcar = Car.objects.create(make=None)
        with self.assertRaises(ValueError):
            self.driver.car_set._add_items('driver', 'car', nullcar)

    def test_add_null_reverse_related(self):
        nulldriver = Driver.objects.create(name=None)
        with self.assertRaises(ValueError):
            nulldriver.car_set._add_items('driver', 'car', self.car)

    def test_remove(self):
        self.assertQuerysetEqual(
            self.car.drivers.all(),
            ["<Driver: Ryan Briscoe>"]
        )
        self.car.drivers._remove_items('car', 'driver', self.driver)
        self.assertQuerysetEqual(
            self.car.drivers.all(), [])

    def test_remove_reverse(self):
        self.assertQuerysetEqual(
            self.driver.car_set.all(),
            ["<Car: Toyota>"]
        )
        self.driver.car_set._remove_items('driver', 'car', self.car)
        self.assertQuerysetEqual(
            self.driver.car_set.all(), [])


class ThroughLoadDataTestCase(TestCase):
    fixtures = ["m2m_through"]

    def test_sequence_creation(self):
        "Check that sequences on an m2m_through are created for the through model, not a phantom auto-generated m2m table. Refs #11107"
        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="json", stdout=out)
        self.assertJSONEqual(out.getvalue().strip(), """[{"pk": 1, "model": "m2m_through_regress.usermembership", "fields": {"price": 100, "group": 1, "user": 1}}, {"pk": 1, "model": "m2m_through_regress.person", "fields": {"name": "Guido"}}, {"pk": 1, "model": "m2m_through_regress.group", "fields": {"name": "Python Core Group"}}]""")
