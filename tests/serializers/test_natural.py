from django.core import serializers
from django.db import connection
from django.test import TestCase

from .models import (
    Customer, Employee, FKDataNaturalKey, NaturalKeyAnchor, Person,
    PremiumCustomer,
)
from .tests import register_tests


class NaturalKeySerializerTests(TestCase):
    pass


def natural_key_serializer_test(format, self):
    # Create all the objects defined in the test data
    with connection.constraint_checks_disabled():
        objects = [
            NaturalKeyAnchor.objects.create(id=1100, data="Natural Key Anghor"),
            FKDataNaturalKey.objects.create(id=1101, data_id=1100),
            FKDataNaturalKey.objects.create(id=1102, data_id=None),
        ]
    # Serialize the test database
    serialized_data = serializers.serialize(format, objects, indent=2, use_natural_foreign_keys=True)

    for obj in serializers.deserialize(format, serialized_data):
        obj.save()

    # Assert that the deserialized data is the same
    # as the original source
    for obj in objects:
        instance = obj.__class__.objects.get(id=obj.pk)
        self.assertEqual(
            obj.data, instance.data,
            "Objects with PK=%d not equal; expected '%s' (%s), got '%s' (%s)" % (
                obj.pk, obj.data, type(obj.data), instance, type(instance.data),
            )
        )


def natural_key_test(format, self):
    book1 = {
        'data': '978-1590597255',
        'title': 'The Definitive Guide to Django: Web Development Done Right',
    }
    book2 = {'data': '978-1590599969', 'title': 'Practical Django Projects'}

    # Create the books.
    adrian = NaturalKeyAnchor.objects.create(**book1)
    james = NaturalKeyAnchor.objects.create(**book2)

    # Serialize the books.
    string_data = serializers.serialize(
        format, NaturalKeyAnchor.objects.all(), indent=2,
        use_natural_foreign_keys=True, use_natural_primary_keys=True,
    )

    # Delete one book (to prove that the natural key generation will only
    # restore the primary keys of books found in the database via the
    # get_natural_key manager method).
    james.delete()

    # Deserialize and test.
    books = list(serializers.deserialize(format, string_data))
    self.assertEqual(len(books), 2)
    self.assertEqual(books[0].object.title, book1['title'])
    self.assertEqual(books[0].object.pk, adrian.pk)
    self.assertEqual(books[1].object.title, book2['title'])
    self.assertIsNone(books[1].object.pk)


def natural_pk_mti_test(format, self):
    x1 = Person.objects.create(firstname='alphonse', lastname='allais')
    x2 = Customer.objects.create(firstname='alban', lastname='berg', cnum=1885)
    x3 = PremiumCustomer.objects.create(firstname='vladimir', lastname='jankelevitch', cnum=1903, level=81)
    x4 = Employee.objects.create(firstname='daksiputra', lastname='panini', enum=-400)

    self.assertEqual(len(Person.objects.all()), 4)
    self.assertEqual(len(Customer.objects.all()), 2)
    self.assertEqual(len(PremiumCustomer.objects.all()), 1)
    self.assertEqual(len(Employee.objects.all()), 1)

    # test with 2 different serialization orders to ensure that correctness
    # does not accidentally rely on the order in which instances are serialized

    objs1 = []
    objs1.extend(Person.objects.all())
    objs1.extend(Customer.objects.all())
    objs1.extend(PremiumCustomer.objects.all())
    objs1.extend(Employee.objects.all())

    objs2 = []
    objs2.extend(reversed(Person.objects.all()))
    objs2.extend(Employee.objects.all())
    objs2.extend(Customer.objects.all())
    objs2.extend(PremiumCustomer.objects.all())

    # check that roundtripping through serialization indeed returns the same data
    def get_data():
        objs = []
        objs.extend(reversed(Person.objects.all()))
        objs.extend(Employee.objects.all())
        objs.extend(Customer.objects.all())
        objs.extend(PremiumCustomer.objects.all())
        return sorted(x.data() for x in objs)

    data = get_data()

    string_data1 = serializers.serialize(
        format, objs1,
        use_natural_foreign_keys=True, use_natural_primary_keys=True,
    )

    string_data2 = serializers.serialize(
        format, objs2,
        use_natural_foreign_keys=True, use_natural_primary_keys=True,
    )

    x1.delete()
    x2.delete()
    x3.delete()
    x4.delete()

    self.assertEqual(len(Person.objects.all()), 0)
    self.assertEqual(len(Customer.objects.all()), 0)
    self.assertEqual(len(PremiumCustomer.objects.all()), 0)
    self.assertEqual(len(Employee.objects.all()), 0)

    for obj in serializers.deserialize(format, string_data1):
        obj.save()

    self.assertEqual(len(Person.objects.all()), 4)
    self.assertEqual(len(Customer.objects.all()), 2)
    self.assertEqual(len(PremiumCustomer.objects.all()), 1)
    self.assertEqual(len(Employee.objects.all()), 1)
    self.assertEqual(data, get_data())

    Employee.objects.all().delete()
    PremiumCustomer.objects.all().delete()
    Customer.objects.all().delete()
    Person.objects.all().delete()

    for obj in serializers.deserialize(format, string_data2):
        obj.save()

    self.assertEqual(len(Person.objects.all()), 4)
    self.assertEqual(len(Customer.objects.all()), 2)
    self.assertEqual(len(PremiumCustomer.objects.all()), 1)
    self.assertEqual(len(Employee.objects.all()), 1)
    self.assertEqual(data, get_data())


# Dynamically register tests for each serializer
register_tests(NaturalKeySerializerTests, 'test_%s_natural_key_serializer', natural_key_serializer_test)
register_tests(NaturalKeySerializerTests, 'test_%s_serializer_natural_keys', natural_key_test)
register_tests(NaturalKeySerializerTests, 'test_%s_serializer_natural_pks_mti', natural_pk_mti_test)
