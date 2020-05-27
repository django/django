from django.db import models
from django.test import skipUnlessDBFeature
from django.test.utils import isolate_apps

from . import PostgreSQLTestCase
from .fields import  BigSerialField, DatabaseWrapper, SerialField, SmallSerialField
from .models import SerialModel


@isolate_apps('invalid_models_tests')
class SerialFieldModelTests(PostgreSQLTestCase):
    def test_not_null(self):
        class Model(models.Model):
            id = SerialField(null=True)

        field = Model._meta.get_field('id')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)
        self.assertFalse(field.null)

    def test_primary_key(self):
        class Model(models.Model):
            another = SerialField()

        field = Model._meta.get_field('id')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)

    def test_internal_type(self):
        class Model(models.Model):
            small = SmallSerialField()
            regular = SerialField()
            big = BigSerialField(primary_key=False)

        small = Model._meta.get_field('small')
        regular = Model._meta.get_field('regular')
        big = Model._meta.get_field('big')

        self.assertIn(regular.get_internal_type(), DatabaseWrapper.data_types)
        self.assertIn(small.get_internal_type(), DatabaseWrapper.data_types)
        self.assertIn(big.get_internal_type(), DatabaseWrapper.data_types)

        self.assertEqual(DatabaseWrapper.data_types[regular.get_internal_type()], 'serial')
        self.assertEqual(DatabaseWrapper.data_types[small.get_internal_type()], 'smallserial')
        self.assertEqual(DatabaseWrapper.data_types[big.get_internal_type()], 'bigserial')


@skipUnlessDBFeature('has_native_serial_field')
class SerialFieldTests(PostgreSQLTestCase):
    def test_not_null(self):
        o = SerialModel.objects.create()
        self.assertIsNotNone(o.small)
        self.assertIsNotNone(o.big)

    def test_auto_increment(self):
        o1 = SerialModel.objects.create()
        o2 = SerialModel.objects.create()
        self.assertGreater(o2.regular, o1.regular)
        self.assertGreater(o2.small, o1.small)
        self.assertGreater(o2.big, o1.big)
