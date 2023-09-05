from django.db import models
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import AutoModel, BigAutoModel, SmallAutoModel, TwoAutoModel
from .test_integerfield import (
    BigIntegerFieldTests,
    IntegerFieldTests,
    SmallIntegerFieldTests,
)


class AutoFieldTests(IntegerFieldTests):
    model = AutoModel
    rel_db_type_class = models.IntegerField


class BigAutoFieldTests(BigIntegerFieldTests):
    model = BigAutoModel
    rel_db_type_class = models.BigIntegerField


class SmallAutoFieldTests(SmallIntegerFieldTests):
    model = SmallAutoModel
    rel_db_type_class = models.SmallIntegerField


@skipUnlessDBFeature("supports_multiple_auto_fields")
class MultipleAutoFieldTests(TestCase):
    def test_instance_with_two_autofields(self):
        instance1 = TwoAutoModel.objects.create()
        instance2 = TwoAutoModel.objects.create()
        self.assertGreater(instance2.id, instance1.id)
        self.assertGreater(instance2.auto2, instance1.auto2)


class AutoFieldInheritanceTests(SimpleTestCase):
    def test_isinstance_of_autofield(self):
        for field in (models.BigAutoField, models.SmallAutoField):
            with self.subTest(field.__name__):
                self.assertIsInstance(field(), models.AutoField)

    def test_issubclass_of_autofield(self):
        class MyBigAutoField(models.BigAutoField):
            pass

        class MySmallAutoField(models.SmallAutoField):
            pass

        tests = [
            MyBigAutoField,
            MySmallAutoField,
            models.BigAutoField,
            models.SmallAutoField,
        ]
        for field in tests:
            with self.subTest(field.__name__):
                self.assertTrue(issubclass(field, models.AutoField))
