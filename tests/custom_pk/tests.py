from django.db import IntegrityError, transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .fields import MyWrapper
from .models import Bar, Business, CustomAutoFieldModel, Employee, Foo


class BasicCustomPKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dan = Employee.objects.create(
            employee_code=123,
            first_name="Dan",
            last_name="Jones",
        )
        cls.fran = Employee.objects.create(
            employee_code=456,
            first_name="Fran",
            last_name="Bones",
        )
        cls.business = Business.objects.create(name="Sears")
        cls.business.employees.add(cls.dan, cls.fran)

    def test_querysets(self):
        """
        Both pk and custom attribute_name can be used in filter and friends
        """
        self.assertSequenceEqual(Employee.objects.filter(pk=123), [self.dan])
        self.assertSequenceEqual(Employee.objects.filter(employee_code=123), [self.dan])
        self.assertSequenceEqual(
            Employee.objects.filter(pk__in=[123, 456]),
            [self.fran, self.dan],
        )
        self.assertSequenceEqual(Employee.objects.all(), [self.fran, self.dan])

        self.assertQuerySetEqual(
            Business.objects.filter(name="Sears"), ["Sears"], lambda b: b.name
        )
        self.assertQuerySetEqual(
            Business.objects.filter(pk="Sears"),
            [
                "Sears",
            ],
            lambda b: b.name,
        )

    def test_querysets_related_name(self):
        """
        Custom pk doesn't affect related_name based lookups
        """
        self.assertSequenceEqual(
            self.business.employees.all(),
            [self.fran, self.dan],
        )
        self.assertQuerySetEqual(
            self.fran.business_set.all(),
            [
                "Sears",
            ],
            lambda b: b.name,
        )

    def test_querysets_relational(self):
        """
        Queries across tables, involving primary key
        """
        self.assertSequenceEqual(
            Employee.objects.filter(business__name="Sears"),
            [self.fran, self.dan],
        )
        self.assertSequenceEqual(
            Employee.objects.filter(business__pk="Sears"),
            [self.fran, self.dan],
        )

        self.assertQuerySetEqual(
            Business.objects.filter(employees__employee_code=123),
            [
                "Sears",
            ],
            lambda b: b.name,
        )
        self.assertQuerySetEqual(
            Business.objects.filter(employees__pk=123),
            [
                "Sears",
            ],
            lambda b: b.name,
        )

        self.assertQuerySetEqual(
            Business.objects.filter(employees__first_name__startswith="Fran"),
            [
                "Sears",
            ],
            lambda b: b.name,
        )

    def test_get(self):
        """
        Get can accept pk or the real attribute name
        """
        self.assertEqual(Employee.objects.get(pk=123), self.dan)
        self.assertEqual(Employee.objects.get(pk=456), self.fran)

        with self.assertRaises(Employee.DoesNotExist):
            Employee.objects.get(pk=42)

        # Use the name of the primary key, rather than pk.
        self.assertEqual(Employee.objects.get(employee_code=123), self.dan)

    def test_pk_attributes(self):
        """
        pk and attribute name are available on the model
        No default id attribute is added
        """
        # pk can be used as a substitute for the primary key.
        # The primary key can be accessed via the pk property on the model.
        e = Employee.objects.get(pk=123)
        self.assertEqual(e.pk, 123)
        self.assertEqual(e.pk_str, "123")
        # Or we can use the real attribute name for the primary key:
        self.assertEqual(e.employee_code, 123)

        with self.assertRaisesMessage(
            AttributeError, "'Employee' object has no attribute 'id'"
        ):
            e.id

    def test_in_bulk(self):
        """
        Custom pks work with in_bulk, both for integer and non-integer types
        """
        emps = Employee.objects.in_bulk([123, 456])
        self.assertEqual(emps[123], self.dan)

        self.assertEqual(
            Business.objects.in_bulk(["Sears"]),
            {
                "Sears": self.business,
            },
        )

    def test_save(self):
        """
        custom pks do not affect save
        """
        fran = Employee.objects.get(pk=456)
        fran.last_name = "Jones"
        fran.save()

        self.assertSequenceEqual(
            Employee.objects.filter(last_name="Jones"),
            [self.dan, fran],
        )


class CustomPKTests(TestCase):
    def test_custom_pk_create(self):
        """
        New objects can be created both with pk and the custom name
        """
        Employee.objects.create(employee_code=1234, first_name="Foo", last_name="Bar")
        Employee.objects.create(pk=1235, first_name="Foo", last_name="Baz")
        Business.objects.create(name="Bears")
        Business.objects.create(pk="Tears")

    def test_unicode_pk(self):
        # Primary key may be Unicode string.
        Business.objects.create(name="jaźń")

    def test_unique_pk(self):
        # The primary key must also be unique, so trying to create a new object
        # with the same primary key will fail.
        Employee.objects.create(
            employee_code=123, first_name="Frank", last_name="Jones"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(
                    employee_code=123, first_name="Fred", last_name="Jones"
                )

    def test_zero_non_autoincrement_pk(self):
        Employee.objects.create(employee_code=0, first_name="Frank", last_name="Jones")
        employee = Employee.objects.get(pk=0)
        self.assertEqual(employee.employee_code, 0)

    def test_custom_field_pk(self):
        # Regression for #10785 -- Custom fields can be used for primary keys.
        new_bar = Bar.objects.create()
        new_foo = Foo.objects.create(bar=new_bar)

        f = Foo.objects.get(bar=new_bar.pk)
        self.assertEqual(f, new_foo)
        self.assertEqual(f.bar, new_bar)

        f = Foo.objects.get(bar=new_bar)
        self.assertEqual(f, new_foo)
        self.assertEqual(f.bar, new_bar)

    # SQLite lets objects be saved with an empty primary key, even though an
    # integer is expected. So we can't check for an error being raised in that
    # case for SQLite. Remove it from the suite for this next bit.
    @skipIfDBFeature("supports_unspecified_pk")
    def test_required_pk(self):
        # The primary key must be specified, so an error is raised if you
        # try to create an object without it.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(first_name="Tom", last_name="Smith")

    def test_auto_field_subclass_create(self):
        obj = CustomAutoFieldModel.objects.create()
        self.assertIsInstance(obj.id, MyWrapper)

    @skipUnlessDBFeature("can_return_rows_from_bulk_insert")
    def test_auto_field_subclass_bulk_create(self):
        obj = CustomAutoFieldModel()
        CustomAutoFieldModel.objects.bulk_create([obj])
        self.assertIsInstance(obj.id, MyWrapper)
