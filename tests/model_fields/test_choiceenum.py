from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase

from .models import Foo


class TestChoiceEnumDefinition(SimpleTestCase):

    def test_simple_definition_int(self):

        class MyEnum(models.ChoiceIntEnum):
            ONE = 1, 'One'
            TWO = 2, 'Two'

        self.assertEqual(MyEnum.ONE, 1)
        self.assertEqual(MyEnum.TWO.display, 'Two')
        self.assertSequenceEqual(MyEnum.choices, [(1, 'One'), (2, 'Two')])

    def test_simple_definition_int_default_display(self):
        class MyEnum(models.ChoiceIntEnum):
            ONE = 1, 'One'
            ONE_PLUS_ONE = 2
            THREE = 3

        self.assertEqual(MyEnum.ONE.display, 'One')
        self.assertEqual(MyEnum.ONE_PLUS_ONE.display, 'One Plus One')
        self.assertSequenceEqual(MyEnum.choices, [(1, 'One'), (2, 'One Plus One'), (3, 'Three')])

    def test_simple_definition_str(self):

        class MyEnum(str, models.ChoiceEnum):
            ONE = '1', 'One'
            TWO = '2', 'Two'

        self.assertEqual(MyEnum.ONE, '1')
        self.assertEqual(MyEnum.TWO.display, 'Two')
        self.assertSequenceEqual(MyEnum.choices, [('1', 'One'), ('2', 'Two')])

    def test_simple_definition_str_default_display(self):
        class MyEnum(str, models.ChoiceEnum):
            ONE = '1', 'One'
            ONE_PLUS_ONE = '2'
            THREE = '3'

        self.assertEqual(MyEnum.ONE.display, 'One')
        self.assertEqual(MyEnum.ONE_PLUS_ONE.display, 'One Plus One')
        self.assertSequenceEqual(MyEnum.choices, [('1', 'One'), ('2', 'One Plus One'), ('3', 'Three')])

    def test_invalid_definition(self):
        with self.assertRaisesRegex(ValueError, '.*[Ii]nvalid.*ONE.*'):
            class MyEnum(models.ChoiceIntEnum):
                ONE = 1, 'One', 'One too many'


class TestChoiceEnumValidation(SimpleTestCase):

    class IntEnum(models.ChoiceIntEnum):
        ONE = 1, 'One'
        TWO = 2, 'Two'

    class StrEnum(str, models.ChoiceEnum):
        ONE = '1', 'One'
        ONE_PLUS_ONE = '2'
        THREE = '3'

    def test_validates_valid_value(self):
        self.IntEnum.validate(1)
        self.StrEnum.validate('2')

    def test_invalidates_correctly_typed_value(self):
        with self.assertRaises(ValidationError):
            self.IntEnum.validate(7)
        with self.assertRaises(ValidationError):
            self.StrEnum.validate('monster')

    def test_invalidates_incorrectly_typed_value(self):
        with self.assertRaises(ValidationError):
            self.IntEnum.validate('not int')
        with self.assertRaises(ValidationError):
            self.StrEnum.validate(b'2')


class TestStrChoiceEnumInDatabase(TestCase):

    class StrEnum(str, models.ChoiceEnum):
        ONE = '1', 'One'
        ONE_PLUS_ONE = '2'
        THREE = '3'

    def test_value_saved(self):
        foo = Foo.objects.create(a=self.StrEnum.ONE, d=1.0)
        foo.refresh_from_db()
        self.assertEquals(foo.a, self.StrEnum.ONE)
        self.assertEquals(foo.a, '1')

    def test_value_query(self):
        foo = Foo.objects.create(a=self.StrEnum.ONE_PLUS_ONE, d=2.0)
        bar = Foo.objects.get(a=self.StrEnum.ONE_PLUS_ONE)
        self.assertEquals(bar.a, self.StrEnum.ONE_PLUS_ONE)
        self.assertEquals(bar.a, '2')
        baz = Foo.objects.get(a='2')
        self.assertEquals(bar, baz)
        self.assertEquals(baz.a, self.StrEnum.ONE_PLUS_ONE)
