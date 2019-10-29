import datetime
import decimal
import ipaddress
import uuid

from django.db import models
from django.test import SimpleTestCase
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


class Suit(models.IntegerChoices):
    DIAMOND = 1, _('Diamond')
    SPADE = 2, _('Spade')
    HEART = 3, _('Heart')
    CLUB = 4, _('Club')


class YearInSchool(models.TextChoices):
    FRESHMAN = 'FR', _('Freshman')
    SOPHOMORE = 'SO', _('Sophomore')
    JUNIOR = 'JR', _('Junior')
    SENIOR = 'SR', _('Senior')
    GRADUATE = 'GR', _('Graduate')


class Vehicle(models.IntegerChoices):
    CAR = 1, 'Carriage'
    TRUCK = 2
    JET_SKI = 3

    __empty__ = _('(Unknown)')


class Gender(models.TextChoices):
    MALE = 'M'
    FEMALE = 'F'
    NOT_SPECIFIED = 'X'

    __empty__ = '(Undeclared)'


class ChoicesTests(SimpleTestCase):
    def test_integerchoices(self):
        self.assertEqual(Suit.choices, [(1, 'Diamond'), (2, 'Spade'), (3, 'Heart'), (4, 'Club')])
        self.assertEqual(Suit.labels, ['Diamond', 'Spade', 'Heart', 'Club'])
        self.assertEqual(Suit.values, [1, 2, 3, 4])
        self.assertEqual(Suit.names, ['DIAMOND', 'SPADE', 'HEART', 'CLUB'])

        self.assertEqual(repr(Suit.DIAMOND), '<Suit.DIAMOND: 1>')
        self.assertEqual(Suit.DIAMOND.label, 'Diamond')
        self.assertEqual(Suit.DIAMOND.value, 1)
        self.assertEqual(Suit['DIAMOND'], Suit.DIAMOND)
        self.assertEqual(Suit(1), Suit.DIAMOND)

        self.assertIsInstance(Suit, type(models.Choices))
        self.assertIsInstance(Suit.DIAMOND, Suit)
        self.assertIsInstance(Suit.DIAMOND.label, Promise)
        self.assertIsInstance(Suit.DIAMOND.value, int)

    def test_integerchoices_auto_label(self):
        self.assertEqual(Vehicle.CAR.label, 'Carriage')
        self.assertEqual(Vehicle.TRUCK.label, 'Truck')
        self.assertEqual(Vehicle.JET_SKI.label, 'Jet Ski')

    def test_integerchoices_empty_label(self):
        self.assertEqual(Vehicle.choices[0], (None, '(Unknown)'))
        self.assertEqual(Vehicle.labels[0], '(Unknown)')
        self.assertIsNone(Vehicle.values[0])
        self.assertEqual(Vehicle.names[0], '__empty__')

    def test_integerchoices_functional_api(self):
        Place = models.IntegerChoices('Place', 'FIRST SECOND THIRD')
        self.assertEqual(Place.labels, ['First', 'Second', 'Third'])
        self.assertEqual(Place.values, [1, 2, 3])
        self.assertEqual(Place.names, ['FIRST', 'SECOND', 'THIRD'])

    def test_integerchoices_containment(self):
        self.assertIn(Suit.DIAMOND, Suit)
        self.assertIn(1, Suit)
        self.assertNotIn(0, Suit)

    def test_textchoices(self):
        self.assertEqual(YearInSchool.choices, [
            ('FR', 'Freshman'), ('SO', 'Sophomore'), ('JR', 'Junior'), ('SR', 'Senior'), ('GR', 'Graduate'),
        ])
        self.assertEqual(YearInSchool.labels, ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate'])
        self.assertEqual(YearInSchool.values, ['FR', 'SO', 'JR', 'SR', 'GR'])
        self.assertEqual(YearInSchool.names, ['FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR', 'GRADUATE'])

        self.assertEqual(repr(YearInSchool.FRESHMAN), "<YearInSchool.FRESHMAN: 'FR'>")
        self.assertEqual(YearInSchool.FRESHMAN.label, 'Freshman')
        self.assertEqual(YearInSchool.FRESHMAN.value, 'FR')
        self.assertEqual(YearInSchool['FRESHMAN'], YearInSchool.FRESHMAN)
        self.assertEqual(YearInSchool('FR'), YearInSchool.FRESHMAN)

        self.assertIsInstance(YearInSchool, type(models.Choices))
        self.assertIsInstance(YearInSchool.FRESHMAN, YearInSchool)
        self.assertIsInstance(YearInSchool.FRESHMAN.label, Promise)
        self.assertIsInstance(YearInSchool.FRESHMAN.value, str)

    def test_textchoices_auto_label(self):
        self.assertEqual(Gender.MALE.label, 'Male')
        self.assertEqual(Gender.FEMALE.label, 'Female')
        self.assertEqual(Gender.NOT_SPECIFIED.label, 'Not Specified')

    def test_textchoices_empty_label(self):
        self.assertEqual(Gender.choices[0], (None, '(Undeclared)'))
        self.assertEqual(Gender.labels[0], '(Undeclared)')
        self.assertIsNone(Gender.values[0])
        self.assertEqual(Gender.names[0], '__empty__')

    def test_textchoices_functional_api(self):
        Medal = models.TextChoices('Medal', 'GOLD SILVER BRONZE')
        self.assertEqual(Medal.labels, ['Gold', 'Silver', 'Bronze'])
        self.assertEqual(Medal.values, ['GOLD', 'SILVER', 'BRONZE'])
        self.assertEqual(Medal.names, ['GOLD', 'SILVER', 'BRONZE'])

    def test_textchoices_containment(self):
        self.assertIn(YearInSchool.FRESHMAN, YearInSchool)
        self.assertIn('FR', YearInSchool)
        self.assertNotIn('XX', YearInSchool)

    def test_textchoices_blank_value(self):
        class BlankStr(models.TextChoices):
            EMPTY = '', '(Empty)'
            ONE = 'ONE', 'One'

        self.assertEqual(BlankStr.labels, ['(Empty)', 'One'])
        self.assertEqual(BlankStr.values, ['', 'ONE'])
        self.assertEqual(BlankStr.names, ['EMPTY', 'ONE'])

    def test_invalid_definition(self):
        msg = "'str' object cannot be interpreted as an integer"
        with self.assertRaisesMessage(TypeError, msg):
            class InvalidArgumentEnum(models.IntegerChoices):
                # A string is not permitted as the second argument to int().
                ONE = 1, 'X', 'Invalid'

        msg = "duplicate values found in <enum 'Fruit'>: PINEAPPLE -> APPLE"
        with self.assertRaisesMessage(ValueError, msg):
            class Fruit(models.IntegerChoices):
                APPLE = 1, 'Apple'
                PINEAPPLE = 1, 'Pineapple'

    def test_str(self):
        for test in [Gender, Suit, YearInSchool, Vehicle]:
            for member in test:
                with self.subTest(member=member):
                    self.assertEqual(str(test[member.name]), str(member.value))


class Separator(bytes, models.Choices):
    FS = b'\x1c', 'File Separator'
    GS = b'\x1d', 'Group Separator'
    RS = b'\x1e', 'Record Separator'
    US = b'\x1f', 'Unit Separator'


class Constants(float, models.Choices):
    PI = 3.141592653589793, 'π'
    TAU = 6.283185307179586, 'τ'


class Set(frozenset, models.Choices):
    A = {1, 2}
    B = {2, 3}
    UNION = A | B
    DIFFERENCE = A - B
    INTERSECTION = A & B


class MoonLandings(datetime.date, models.Choices):
    APOLLO_11 = 1969, 7, 20, 'Apollo 11 (Eagle)'
    APOLLO_12 = 1969, 11, 19, 'Apollo 12 (Intrepid)'
    APOLLO_14 = 1971, 2, 5, 'Apollo 14 (Antares)'
    APOLLO_15 = 1971, 7, 30, 'Apollo 15 (Falcon)'
    APOLLO_16 = 1972, 4, 21, 'Apollo 16 (Orion)'
    APOLLO_17 = 1972, 12, 11, 'Apollo 17 (Challenger)'


class DateAndTime(datetime.datetime, models.Choices):
    A = 2010, 10, 10, 10, 10, 10
    B = 2011, 11, 11, 11, 11, 11
    C = 2012, 12, 12, 12, 12, 12


class MealTimes(datetime.time, models.Choices):
    BREAKFAST = 7, 0
    LUNCH = 13, 0
    DINNER = 18, 30


class Frequency(datetime.timedelta, models.Choices):
    WEEK = 0, 0, 0, 0, 0, 0, 1, 'Week'
    DAY = 1, 'Day'
    HOUR = 0, 0, 0, 0, 0, 1, 'Hour'
    MINUTE = 0, 0, 0, 0, 1, 'Hour'
    SECOND = 0, 1, 'Second'


class Number(decimal.Decimal, models.Choices):
    E = 2.718281828459045, 'e'
    PI = '3.141592653589793', 'π'
    TAU = decimal.Decimal('6.283185307179586'), 'τ'


class IPv4Address(ipaddress.IPv4Address, models.Choices):
    LOCALHOST = '127.0.0.1', 'Localhost'
    GATEWAY = '192.168.0.1', 'Gateway'
    BROADCAST = '192.168.0.255', 'Broadcast'


class IPv6Address(ipaddress.IPv6Address, models.Choices):
    LOCALHOST = '::1', 'Localhost'
    UNSPECIFIED = '::', 'Unspecified'


class IPv4Network(ipaddress.IPv4Network, models.Choices):
    LOOPBACK = '127.0.0.0/8', 'Loopback'
    LINK_LOCAL = '169.254.0.0/16', 'Link-Local'
    PRIVATE_USE_A = '10.0.0.0/8', 'Private-Use (Class A)'


class IPv6Network(ipaddress.IPv6Network, models.Choices):
    LOOPBACK = '::1/128', 'Loopback'
    UNSPECIFIED = '::/128', 'Unspecified'
    UNIQUE_LOCAL = 'fc00::/7', 'Unique-Local'
    LINK_LOCAL_UNICAST = 'fe80::/10', 'Link-Local Unicast'


class CustomChoicesTests(SimpleTestCase):
    def test_labels_valid(self):
        enums = (
            Separator, Constants, Set, MoonLandings, DateAndTime, MealTimes,
            Frequency, Number, IPv4Address, IPv6Address, IPv4Network,
            IPv6Network,
        )
        for choice_enum in enums:
            with self.subTest(choice_enum.__name__):
                self.assertNotIn(None, choice_enum.labels)

    def test_bool_unsupported(self):
        msg = "type 'bool' is not an acceptable base type"
        with self.assertRaisesMessage(TypeError, msg):
            class Boolean(bool, models.Choices):
                pass

    def test_timezone_unsupported(self):
        msg = "type 'datetime.timezone' is not an acceptable base type"
        with self.assertRaisesMessage(TypeError, msg):
            class Timezone(datetime.timezone, models.Choices):
                pass

    def test_uuid_unsupported(self):
        msg = 'UUID objects are immutable'
        with self.assertRaisesMessage(TypeError, msg):
            class Identifier(uuid.UUID, models.Choices):
                A = '972ce4eb-a95f-4a56-9339-68c208a76f18'
