# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import IntegrityError, transaction
from django.test import TestCase, skipIfDBFeature
from django.utils import six

from .models import Bar, Business, Employee, Foo


class BasicCustomPKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dan = Employee.objects.create(
            employee_code=123, first_name="Dan", last_name="Jones",
        )
        cls.fran = Employee.objects.create(
            employee_code=456, first_name="Fran", last_name="Bones",
        )
        cls.business = Business.objects.create(name="Sears")
        cls.business.employees.add(cls.dan, cls.fran)

    def test_querysets(self):
        """
        Both pk and custom attribute_name can be used in filter and friends
        """
        self.assertQuerysetEqual(
            Employee.objects.filter(pk=123), [
                "Dan Jones",
            ],
            six.text_type
        )

        self.assertQuerysetEqual(
            Employee.objects.filter(employee_code=123), [
                "Dan Jones",
            ],
            six.text_type
        )

        self.assertQuerysetEqual(
            Employee.objects.filter(pk__in=[123, 456]), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type
        )

        self.assertQuerysetEqual(
            Employee.objects.all(), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type
        )

        self.assertQuerysetEqual(
            Business.objects.filter(name="Sears"), [
                "Sears"
            ],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            Business.objects.filter(pk="Sears"), [
                "Sears",
            ],
            lambda b: b.name
        )

    def test_querysets_related_name(self):
        """
        Custom pk doesn't affect related_name based lookups
        """
        self.assertQuerysetEqual(
            self.business.employees.all(), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type
        )
        self.assertQuerysetEqual(
            self.fran.business_set.all(), [
                "Sears",
            ],
            lambda b: b.name
        )

    def test_querysets_relational(self):
        """
        Queries across tables, involving primary key
        """
        self.assertQuerysetEqual(
            Employee.objects.filter(business__name="Sears"), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type,
        )
        self.assertQuerysetEqual(
            Employee.objects.filter(business__pk="Sears"), [
                "Fran Bones",
                "Dan Jones",
            ],
            six.text_type,
        )

        self.assertQuerysetEqual(
            Business.objects.filter(employees__employee_code=123), [
                "Sears",
            ],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            Business.objects.filter(employees__pk=123), [
                "Sears",
            ],
            lambda b: b.name,
        )

        self.assertQuerysetEqual(
            Business.objects.filter(employees__first_name__startswith="Fran"), [
                "Sears",
            ],
            lambda b: b.name
        )

    def test_get(self):
        """
        Get can accept pk or the real attribute name
        """
        self.assertEqual(Employee.objects.get(pk=123), self.dan)
        self.assertEqual(Employee.objects.get(pk=456), self.fran)

        self.assertRaises(
            Employee.DoesNotExist,
            lambda: Employee.objects.get(pk=42)
        )

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
        # Or we can use the real attribute name for the primary key:
        self.assertEqual(e.employee_code, 123)

        self.assertRaises(AttributeError, lambda: e.id)

    def test_in_bulk(self):
        """
        Custom pks work with in_bulk, both for integer and non-integer types
        """
        emps = Employee.objects.in_bulk([123, 456])
        self.assertEqual(emps[123], self.dan)

        self.assertEqual(Business.objects.in_bulk(["Sears"]), {
            "Sears": self.business,
        })

    def test_save(self):
        """
        custom pks do not affect save
        """
        fran = Employee.objects.get(pk=456)
        fran.last_name = "Jones"
        fran.save()

        self.assertQuerysetEqual(
            Employee.objects.filter(last_name="Jones"), [
                "Dan Jones",
                "Fran Jones",
            ],
            six.text_type
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
        # Primary key may be unicode string
        Business.objects.create(name='jaźń')

    def test_unique_pk(self):
        # The primary key must also obviously be unique, so trying to create a
        # new object with the same primary key will fail.
        Employee.objects.create(
            employee_code=123, first_name="Frank", last_name="Jones"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(employee_code=123, first_name="Fred", last_name="Jones")

    def test_zero_non_autoincrement_pk(self):
        Employee.objects.create(
            employee_code=0, first_name="Frank", last_name="Jones"
        )
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
        self.assertEqual(f, new_foo),
        self.assertEqual(f.bar, new_bar)

    # SQLite lets objects be saved with an empty primary key, even though an
    # integer is expected. So we can't check for an error being raised in that
    # case for SQLite. Remove it from the suite for this next bit.
    @skipIfDBFeature('supports_unspecified_pk')
    def test_required_pk(self):
        # The primary key must be specified, so an error is raised if you
        # try to create an object without it.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(first_name="Tom", last_name="Smith")
