from io import StringIO

from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase

from .models import (
    Car, CarDriver, Driver, Group, Membership, Person, UserMembership,
)


class M2MThroughTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = Person.objects.create(name="Bob")
        cls.jim = Person.objects.create(name="Jim")

        cls.rock = Group.objects.create(name="Rock")
        cls.roll = Group.objects.create(name="Roll")

        cls.frank = User.objects.create_user("frank", "frank@example.com", "password")
        cls.jane = User.objects.create_user("jane", "jane@example.com", "password")

        # normal intermediate model
        cls.bob_rock = Membership.objects.create(person=cls.bob, group=cls.rock)
        cls.bob_roll = Membership.objects.create(person=cls.bob, group=cls.roll, price=50)
        cls.jim_rock = Membership.objects.create(person=cls.jim, group=cls.rock, price=50)

        # intermediate model with custom id column
        cls.frank_rock = UserMembership.objects.create(user=cls.frank, group=cls.rock)
        cls.frank_roll = UserMembership.objects.create(user=cls.frank, group=cls.roll)
        cls.jane_rock = UserMembership.objects.create(user=cls.jane, group=cls.rock)

    def test_retrieve_reverse_m2m_items(self):
        self.assertQuerysetEqual(
            self.bob.group_set.all(), [
                "<Group: Rock>",
                "<Group: Roll>",
            ],
            ordered=False
        )

    def test_retrieve_forward_m2m_items(self):
        self.assertQuerysetEqual(
            self.roll.members.all(), [
                "<Person: Bob>",
            ]
        )

    def test_retrieve_reverse_m2m_items_via_custom_id_intermediary(self):
        self.assertQuerysetEqual(
            self.frank.group_set.all(), [
                "<Group: Rock>",
                "<Group: Roll>",
            ],
            ordered=False
        )

    def test_retrieve_forward_m2m_items_via_custom_id_intermediary(self):
        self.assertQuerysetEqual(
            self.roll.user_members.all(), [
                "<User: frank>",
            ]
        )

    def test_join_trimming_forwards(self):
        """
        Too many copies of the intermediate table aren't involved when doing a
        join (#8046, #8254).
        """
        self.assertQuerysetEqual(
            self.rock.members.filter(membership__price=50), [
                "<Person: Jim>",
            ]
        )

    def test_join_trimming_reverse(self):
        self.assertQuerysetEqual(
            self.bob.group_set.filter(membership__price=50), [
                "<Group: Roll>",
            ]
        )


class M2MThroughSerializationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = Person.objects.create(name="Bob")
        cls.roll = Group.objects.create(name="Roll")
        cls.bob_roll = Membership.objects.create(person=cls.bob, group=cls.roll)

    def test_serialization(self):
        "m2m-through models aren't serialized as m2m fields. Refs #8134"
        pks = {"p_pk": self.bob.pk, "g_pk": self.roll.pk, "m_pk": self.bob_roll.pk}

        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="json", stdout=out)
        self.assertJSONEqual(
            out.getvalue().strip(),
            '[{"pk": %(m_pk)s, "model": "m2m_through_regress.membership", "fields": {"person": %(p_pk)s, "price": '
            '100, "group": %(g_pk)s}}, {"pk": %(p_pk)s, "model": "m2m_through_regress.person", "fields": {"name": '
            '"Bob"}}, {"pk": %(g_pk)s, "model": "m2m_through_regress.group", "fields": {"name": "Roll"}}]'
            % pks
        )

        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="xml", indent=2, stdout=out)
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


class ToFieldThroughTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.car = Car.objects.create(make="Toyota")
        cls.driver = Driver.objects.create(name="Ryan Briscoe")
        CarDriver.objects.create(car=cls.car, driver=cls.driver)
        # We are testing if wrong objects get deleted due to using wrong
        # field value in m2m queries. So, it is essential that the pk
        # numberings do not match.
        # Create one intentionally unused driver to mix up the autonumbering
        cls.unused_driver = Driver.objects.create(name="Barney Gumble")
        # And two intentionally unused cars.
        cls.unused_car1 = Car.objects.create(make="Trabant")
        cls.unused_car2 = Car.objects.create(make="Wartburg")

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

    def test_m2m_relations_unusable_on_null_to_field(self):
        nullcar = Car(make=None)
        msg = (
            '"<Car: None>" needs to have a value for field "make" before this '
            'many-to-many relationship can be used.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            nullcar.drivers.all()

    def test_m2m_relations_unusable_on_null_pk_obj(self):
        msg = (
            "'Car' instance needs to have a primary key value before a "
            "many-to-many relationship can be used."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Car(make='Ford').drivers.all()

    def test_add_related_null(self):
        nulldriver = Driver.objects.create(name=None)
        msg = 'Cannot add "<Driver: None>": the value for field "driver" is None'
        with self.assertRaisesMessage(ValueError, msg):
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
        msg = 'Cannot add "<Car: None>": the value for field "car" is None'
        with self.assertRaisesMessage(ValueError, msg):
            self.driver.car_set._add_items('driver', 'car', nullcar)

    def test_add_null_reverse_related(self):
        nulldriver = Driver.objects.create(name=None)
        msg = (
            '"<Driver: None>" needs to have a value for field "name" before '
            'this many-to-many relationship can be used.'
        )
        with self.assertRaisesMessage(ValueError, msg):
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
        """
        Sequences on an m2m_through are created for the through model, not a
        phantom auto-generated m2m table (#11107).
        """
        out = StringIO()
        management.call_command("dumpdata", "m2m_through_regress", format="json", stdout=out)
        self.assertJSONEqual(
            out.getvalue().strip(),
            '[{"pk": 1, "model": "m2m_through_regress.usermembership", "fields": {"price": 100, "group": 1, "user"'
            ': 1}}, {"pk": 1, "model": "m2m_through_regress.person", "fields": {"name": "Guido"}}, {"pk": 1, '
            '"model": "m2m_through_regress.group", "fields": {"name": "Python Core Group"}}]'
        )
